"""RAG 检索基础评测脚本。

评测只调用 Embedding 和 pgvector 检索，不调用 DeepSeek 生成，适合开发阶段频繁运行。
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


def _load_root_env() -> None:
    """读取项目根目录 .env，避免本地运行评测时手动导出一堆环境变量。"""
    root = Path(__file__).resolve().parents[3]
    env_path = root / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

    database_url = os.environ.get("DATABASE_URL")
    if database_url and "@postgres:" in database_url and not Path("/.dockerenv").exists():
        os.environ["DATABASE_URL"] = database_url.replace("@postgres:", "@localhost:")


@dataclass
class EvalCase:
    question: str
    expected_sources: list[str]
    expected_sections: list[str]
    expected_keywords: list[str]
    expected_refusal: bool
    category: str

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "EvalCase":
        return cls(
            question=payload["question"],
            expected_sources=payload.get("expected_sources", []),
            expected_sections=payload.get("expected_sections", []),
            expected_keywords=payload.get("expected_keywords", []),
            expected_refusal=payload.get("expected_refusal", False),
            category=payload.get("category", "未分类"),
        )


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            cases.append(EvalCase.from_json(json.loads(stripped)))
    return cases


def contains_any(text: str, needles: list[str]) -> bool:
    return bool(needles) and any(needle in text for needle in needles)


def keyword_coverage(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    hits = sum(1 for keyword in keywords if keyword in text)
    return hits / len(keywords)


def run_eval(
    dataset_path: Path,
    *,
    enable_hybrid_search: bool | None = None,
    enable_rerank: bool | None = None,
) -> dict[str, Any]:
    _load_root_env()

    from app.db.session import SessionLocal
    from app.rag.embeddings.dashscope_embedding import DashScopeEmbeddingClient
    from app.rag.retrievers.vector_retriever import PgVectorRetriever
    from app.services.knowledge_base_service import get_or_create_default_knowledge_base
    from app.services.settings_service import get_or_create_settings

    cases = load_cases(dataset_path)
    rows: list[dict[str, Any]] = []

    with SessionLocal() as db:
        app_settings = get_or_create_settings(db)
        use_hybrid_search = (
            app_settings.retrieval.enable_hybrid_search if enable_hybrid_search is None else enable_hybrid_search
        )
        use_rerank = app_settings.retrieval.enable_rerank if enable_rerank is None else enable_rerank
        knowledge_base = get_or_create_default_knowledge_base(db)
        embedder = DashScopeEmbeddingClient()
        retriever = PgVectorRetriever()

        for case in cases:
            query_embedding = embedder.embed_texts(db, [case.question])[0]
            chunks = retriever.search(
                db,
                knowledge_base_id=knowledge_base.id,
                query_embedding=query_embedding,
                query_text=case.question,
                top_k=app_settings.retrieval.top_k,
                enable_hybrid_search=use_hybrid_search,
                enable_rerank=use_rerank,
            )
            top1_score = chunks[0].score if chunks else 0.0
            refused = app_settings.retrieval.strict_refusal and top1_score < app_settings.retrieval.min_similarity
            retrieved_text = "\n".join(
                f"{chunk.title}\n{chunk.section or ''}\n{chunk.content}" for chunk in chunks
            )
            source_hit = (
                True
                if case.expected_refusal
                else contains_any(retrieved_text, case.expected_sources)
                or contains_any(retrieved_text, case.expected_sections)
            )
            coverage = keyword_coverage(retrieved_text, case.expected_keywords)

            rows.append(
                {
                    "question": case.question,
                    "category": case.category,
                    "top1_score": round(top1_score, 4),
                    "refused": refused,
                    "expected_refusal": case.expected_refusal,
                    "source_hit": source_hit,
                    "keyword_coverage": round(coverage, 4),
                    "top1_source": chunks[0].title if chunks else None,
                    "top1_section": chunks[0].section if chunks else None,
                    "retrieval_mode": retriever.last_stats.mode,
                }
            )

    non_refusal_rows = [row for row in rows if not row["expected_refusal"]]
    metrics = {
        "total": len(rows),
        "retrieval_hit_rate": round(mean(row["source_hit"] for row in non_refusal_rows), 4)
        if non_refusal_rows
        else 0.0,
        "refusal_accuracy": round(mean(row["refused"] == row["expected_refusal"] for row in rows), 4)
        if rows
        else 0.0,
        "keyword_coverage_avg": round(mean(row["keyword_coverage"] for row in non_refusal_rows), 4)
        if non_refusal_rows
        else 0.0,
        "avg_top1_score": round(mean(row["top1_score"] for row in rows), 4) if rows else 0.0,
        "retrieval_mode": use_hybrid_search
        and (use_rerank and "hybrid+rerank" or "hybrid")
        or (use_rerank and "vector+rerank" or "vector"),
    }
    return {"metrics": metrics, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run basic RAG retrieval evaluation.")
    parser.add_argument(
        "--dataset",
        default=str(Path(__file__).resolve().parents[3] / "evals" / "golden_qa.jsonl"),
        help="Path to golden QA jsonl.",
    )
    parser.add_argument("--enable-hybrid-search", action="store_true", help="Override settings and enable hybrid search.")
    parser.add_argument("--enable-rerank", action="store_true", help="Override settings and enable lightweight rerank.")
    args = parser.parse_args()

    report = run_eval(
        Path(args.dataset),
        enable_hybrid_search=True if args.enable_hybrid_search else None,
        enable_rerank=True if args.enable_rerank else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from dataclasses import dataclass, field
import re

from app.schemas.settings import ChunkingSettings


@dataclass
class ChunkDraft:
    content: str
    section_path: str | None
    metadata: dict = field(default_factory=dict)


@dataclass
class SectionBlock:
    section_path: str | None
    text: str


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip()


def _extract_sections(text: str) -> list[SectionBlock]:
    """从 Markdown 风格标题中提取章节。

    对 PDF/DOCX/TXT，如果没有 `#` 标题，也会作为一个默认章节处理。
    """
    sections: list[SectionBlock] = []
    heading_stack: list[tuple[int, str]] = []
    buffer: list[str] = []
    current_path: str | None = None

    def flush() -> None:
        nonlocal buffer, current_path
        content = "\n".join(buffer).strip()
        if content:
            sections.append(SectionBlock(section_path=current_path, text=content))
        buffer = []

    for line in _normalize_text(text).split("\n"):
        match = HEADING_RE.match(line.strip())
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack[:] = [(item_level, item_title) for item_level, item_title in heading_stack if item_level < level]
            heading_stack.append((level, title))
            current_path = " > ".join(item_title for _, item_title in heading_stack)
            continue
        buffer.append(line)

    flush()
    if sections:
        return sections

    normalized = _normalize_text(text)
    return [SectionBlock(section_path=None, text=normalized)] if normalized else []


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def split_text(text: str, settings: ChunkingSettings) -> list[ChunkDraft]:
    """混合分块：标题/段落优先，过长内容再固定长度切分并 overlap。"""
    drafts: list[ChunkDraft] = []
    sections = _extract_sections(text)

    for section in sections:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", section.text) if part.strip()]
        buffer: list[str] = []
        buffer_len = 0

        def flush_buffer() -> None:
            nonlocal buffer, buffer_len
            if not buffer:
                return
            content = "\n\n".join(buffer).strip()
            # 企业制度/FAQ 常有短条款，短内容也可能是关键知识，不能直接丢弃。
            for piece in _split_long_text(content, settings.chunk_size, settings.chunk_overlap):
                chunk_content = (
                    f"{section.section_path}\n{piece}" if settings.enable_section_path and section.section_path else piece
                )
                drafts.append(ChunkDraft(content=chunk_content, section_path=section.section_path))
            buffer = []
            buffer_len = 0

        for paragraph in paragraphs:
            paragraph_len = len(paragraph)
            if paragraph_len > settings.chunk_size:
                flush_buffer()
                for piece in _split_long_text(paragraph, settings.chunk_size, settings.chunk_overlap):
                    chunk_content = (
                        f"{section.section_path}\n{piece}" if settings.enable_section_path and section.section_path else piece
                    )
                    drafts.append(ChunkDraft(content=chunk_content, section_path=section.section_path))
                continue

            next_len = buffer_len + paragraph_len + (2 if buffer else 0)
            if buffer and next_len > settings.chunk_size:
                flush_buffer()

            buffer.append(paragraph)
            buffer_len += paragraph_len + (2 if buffer else 0)

        flush_buffer()

    return drafts

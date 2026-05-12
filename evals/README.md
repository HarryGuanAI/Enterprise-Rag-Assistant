# RAG 基础评测集

`golden_qa.jsonl` 用于验证 RAG 检索链路，不额外调用生成模型。

当前指标：

- `retrieval_hit_rate`：期望来源文档或章节是否出现在 TopK 检索结果中。
- `refusal_accuracy`：应该拒答的问题是否被阈值策略判定为拒答。
- `keyword_coverage_avg`：期望关键词在检索上下文中的覆盖比例。
- `avg_top1_score`：Top1 相似度平均值。

运行方式：

```bash
cd backend
python -m app.evals.run_eval --dataset ../evals/golden_qa.jsonl
```

如果在本机直连 Docker Compose 暴露的 PostgreSQL，脚本会自动把 `.env` 中的数据库主机 `postgres` 改为 `localhost`。

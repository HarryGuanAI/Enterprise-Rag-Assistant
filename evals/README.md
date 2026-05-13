# RAG 基础评测集

`golden_qa.jsonl` 用于验证 RAG 检索链路，不额外调用生成模型。当前包含 73 条样例，覆盖员工手册、考勤休假、费用报销、差旅标准、信息安全、销售合同、客服工单、采购付款、入转离、绩效福利、研发发布、产品 FAQ 和拒答问题。

示例文档由 `tools/generate_sample_docs.py` 生成，覆盖 Markdown、TXT、DOCX、PDF 四类当前支持格式。资料均为虚构企业制度，但参考了真实企业常见流程颗粒度，方便测试金额阈值、审批链路、例外情况和边界拒答。

## 指标

- `retrieval_hit_rate`：期望来源文档或章节是否出现在 TopK 检索结果中。
- `refusal_accuracy`：应该拒答的问题是否被阈值策略判定为拒答。
- `keyword_coverage_avg`：期望关键词在检索上下文中的覆盖比例。
- `avg_top1_score`：Top1 相似度平均值。

## 准备样例知识库

如果数据库还没有导入 `sample_docs`，可以先运行：

```bash
docker compose run --rm `
  -v "D:\03_Work\04_NewWorks\我的AI新工作\enterprise-rag-assistant\sample_docs:/app/sample_docs" `
  backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

该命令会复用正式文档入库流程，因此需要 `.env` 中已经配置 `DASHSCOPE_API_KEY`。

## 运行评测

纯向量检索：

```bash
docker compose run --rm `
  -v "D:\03_Work\04_NewWorks\我的AI新工作\enterprise-rag-assistant\evals:/app/evals" `
  -v "D:\03_Work\04_NewWorks\我的AI新工作\enterprise-rag-assistant\backend\app\evals:/app/app/evals" `
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --disable-hybrid-search --disable-rerank
```

Hybrid Search + 轻量 Rerank：

```bash
docker compose run --rm `
  -v "D:\03_Work\04_NewWorks\我的AI新工作\enterprise-rag-assistant\evals:/app/evals" `
  -v "D:\03_Work\04_NewWorks\我的AI新工作\enterprise-rag-assistant\backend\app\evals:/app/app/evals" `
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

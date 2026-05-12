# Enterprise RAG Assistant：企业知识库智能问答助手

> 当前开发进度：文档上传、解析、混合分块、DashScope Embedding 适配器、pgvector 检索器、DeepSeek 流式适配器、SSE 问答接口、登录和游客限制已接入。真实运行前需要在 `.env` 填写 `DASHSCOPE_API_KEY` 和 `DEEPSEEK_API_KEY`。

**云舟知识库助手** 是一个面向企业内部知识库场景的 RAG 问答系统。它支持上传企业文档、异步入库、向量检索、严格拒答、引用来源展示、游客配额限制和流式回答。

本项目用于 AI Agent / RAG 开发岗位求职展示，重点不是做一个玩具聊天框，而是展示一个可以部署、可以开源、可以讲清楚工程取舍的企业级大模型应用。

## 核心功能

- 管理员登录与游客模式
- 游客 2 次问答限制，避免公开演示消耗过多 API
- PDF / DOCX / Markdown / TXT 文档上传
- 异步文档入库：解析、分块、Embedding、pgvector 存储
- DeepSeek 流式回答
- DashScope `text-embedding-v4` 文本向量化
- PostgreSQL + pgvector 向量检索
- 严格拒答：知识库无依据时不让模型自由发挥
- 引用来源展示：回答必须可追溯
- RAG 设置面板：TopK、阈值、分块参数、Rerank/Hybrid 开关
- 基础评测集：检索命中 + 答案关键词覆盖

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Next.js、Tailwind CSS、shadcn/ui、TanStack Query |
| 后端 | FastAPI、SQLAlchemy 2.x、Pydantic、Alembic |
| 数据库 | PostgreSQL + pgvector |
| 生成模型 | DeepSeek API |
| Embedding | DashScope `text-embedding-v4` |
| 部署 | Docker Compose |

## 快速开始

复制环境变量：

```bash
cp .env.example .env
```

编辑 `.env`，填入：

```text
DEEPSEEK_API_KEY
DASHSCOPE_API_KEY
ADMIN_PASSWORD
JWT_SECRET_KEY
```

启动服务：

```bash
docker compose up -d --build
```

访问：

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目文档

- [产品需求说明](docs/product-requirements.md)
- [架构设计](docs/architecture.md)
- [任务计划](task_plan.md)
- [进度记录](progress.md)

## 当前状态

项目正在从脚手架开始逐步实现。第一阶段目标是跑通：

```text
上传文档 -> 异步入库 -> 向量检索 -> 严格拒答/回答生成 -> 引用来源展示
```
## 检索优化展示

当前检索链路已经支持三种可演示模式：

- 纯向量检索：使用 DashScope `text-embedding-v4` 生成问题向量，通过 pgvector cosine distance 召回 TopK。
- Hybrid Search：在向量召回之外增加关键词召回，对中文问题抽取短语和 n-gram，通过文档标题、章节路径和 chunk 内容做补充召回，再融合排序。
- 轻量 Rerank：不额外调用模型，使用向量分、关键词覆盖和标题/章节命中做二次排序；同时保证 Rerank 不降低已有向量置信度，避免破坏严格拒答阈值。

评测脚本支持显式对比不同检索模式：

```bash
python -m app.evals.run_eval --dataset ../evals/golden_qa.jsonl
python -m app.evals.run_eval --dataset ../evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

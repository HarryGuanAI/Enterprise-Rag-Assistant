# Enterprise RAG Assistant：企业知识库智能问答助手

**云舟知识库助手** 是一个面向企业内部知识库场景的 RAG 问答系统，用于展示 AI Agent / RAG 应用开发能力。项目支持企业文档上传、异步入库、Embedding、pgvector 检索、Hybrid Search、轻量 Rerank、严格拒答、引用来源展示、游客限额和 DeepSeek 流式回答。

这个项目的目标不是做一个简单聊天框，而是做一个可部署、可演示、可开源，并且能在面试中讲清楚工程取舍的企业级 LLM 应用。

## 功能亮点

- 管理员登录与游客模式
- 游客每日 15 次问答限制，控制公开演示成本
- PDF / DOCX / Markdown / TXT 文档上传
- 后台异步解析、混合分块、DashScope `text-embedding-v4` 向量化
- PostgreSQL + pgvector 向量检索
- Hybrid Search：向量召回 + 关键词召回融合
- 轻量 Rerank：不额外调用模型的二次排序
- 严格拒答：低相关问题不调用 LLM，降低幻觉和成本
- DeepSeek `deepseek-chat` SSE 流式回答
- 多轮对话：支持开启新对话、查看历史对话、加载历史消息，并结合最近上下文理解追问
- 轻量意图识别：对“你能做什么”等能力咨询直接返回说明，跳过 RAG 和模型调用
- 回答生成中支持手动停止，避免输出卡住时用户只能等待
- 引用来源、相似度分数、检索调试信息展示
- 回答后展示引用标签，点击可打开全文文档预览并自动高亮命中 chunk
- 37 条 golden QA 评测集，覆盖命中、拒答、关键词覆盖
- Docker Compose 一键启动

## 当前部署状态

项目已部署到一台 2 核 4GB 云服务器用于公网演示：

- 演示地址：http://117.72.45.27
- 健康检查：http://117.72.45.27/health
- 当前样例知识库：8 份虚构企业文档，36 个 chunks
- 上线后评测：37 条 golden QA，Hybrid + Rerank 模式下检索命中率、拒答准确率、关键词覆盖均为 `1.00`

说明：公网演示环境只导入 `sample_docs/` 中的虚构资料，不包含真实业务数据。

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Next.js 14, React 18, Tailwind CSS, TanStack Query, lucide-react |
| 后端 | FastAPI, SQLAlchemy 2.x, Pydantic, Alembic |
| 数据库 | PostgreSQL + pgvector |
| Embedding | DashScope `text-embedding-v4` |
| 生成模型 | DeepSeek `deepseek-chat` |
| 部署 | Docker Compose |

## 快速开始

1. 复制环境变量文件：

```bash
cp .env.example .env
```

2. 编辑 `.env`，至少填写：

```text
DASHSCOPE_API_KEY
DEEPSEEK_API_KEY
ADMIN_PASSWORD
JWT_SECRET_KEY
```

3. 启动服务：

```bash
docker compose up -d --build
```

4. 访问：

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 样例知识库

`sample_docs/` 提供了一组虚构企业文档，覆盖员工手册、报销制度、休假制度、IT 服务、产品 FAQ、客服工单、销售合同和数据安全规范。这些文档用于本地演示、RAG 评测和面试讲解，不包含真实公司数据。

可以通过管理员界面逐个上传，也可以批量导入：

```bash
docker compose run --rm \
  -v "./sample_docs:/app/sample_docs" \
  backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

Windows PowerShell 可以使用一行版：

```powershell
docker compose run --rm -v "${PWD}/sample_docs:/app/sample_docs" backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

该命令会调用 DashScope Embedding，因此需要 `.env` 中已经配置 `DASHSCOPE_API_KEY`。

## 运行评测

纯向量基线：

```bash
docker compose run --rm \
  -v "./evals:/app/evals" \
  -v "./backend/app/evals:/app/app/evals" \
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --disable-hybrid-search --disable-rerank
```

PowerShell：

```powershell
docker compose run --rm -v "${PWD}/evals:/app/evals" -v "${PWD}/backend/app/evals:/app/app/evals" backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --disable-hybrid-search --disable-rerank
```

Hybrid Search + 轻量 Rerank：

```bash
docker compose run --rm \
  -v "./evals:/app/evals" \
  -v "./backend/app/evals:/app/app/evals" \
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

PowerShell：

```powershell
docker compose run --rm -v "${PWD}/evals:/app/evals" -v "${PWD}/backend/app/evals:/app/app/evals" backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

当前 37 条样例中，纯向量模式和 Hybrid + Rerank 模式的检索命中率、拒答准确率、关键词覆盖均为 `1.00`。

## 面试讲法

可以用这一条主线介绍项目：

> 我做了一个企业知识库 RAG 助手。管理员上传内部制度文档后，系统会解析、分块、向量化并写入 PostgreSQL + pgvector。用户提问时，系统先做向量检索，可选 Hybrid Search 和 Rerank，再根据 Top1 相似度做严格拒答。命中可靠上下文时，系统把引用片段拼进 Prompt，调用 DeepSeek 流式生成答案，并在右侧展示引用来源和检索调试信息。

重点可以展开：

- 为什么第一版不用 LangChain：为了把 RAG 关键环节拆开实现，便于理解和调试。
- 为什么要严格拒答：知识库依据不足时不让模型自由发挥，同时节省 LLM 成本。
- 为什么做 Hybrid Search：向量召回负责语义泛化，关键词召回补足专有名词和制度原文匹配。
- 为什么做轻量 Rerank：先用低成本方式展示召回和精排的分层设计，后续可替换为模型 Rerank。
- 为什么做多轮对话：真实知识库助手常有追问，需要保存会话和消息，并把最近对话作为上下文帮助模型理解“这个、那条、上一项”等指代。
- 为什么做意图识别：不是所有输入都应该走 RAG。能力咨询、使用说明这类问题用规则路由直接回答，更快，也不会误触发严格拒答。
- 为什么做评测集：RAG 优化不能只靠感觉，要用 golden QA 看命中率、拒答准确率和关键词覆盖。

## 文档

- [架构设计](docs/architecture.md)
- [产品需求](docs/product-requirements.md)
- [部署说明](docs/deployment.md)
- [运维维护手册](docs/maintenance.md)
- [面试演示脚本](docs/demo-script.md)
- [复盘与面试准备](docs/interview-retrospective-2026-05-12.md)
- [开源前安全检查](docs/security-and-open-source-checklist.md)
- [下一个 AI 窗口部署提示词](docs/next-ai-deployment-prompt-2026-05-12.md)
- [评测说明](evals/README.md)

## 安全提醒

- 不要提交 `.env`、真实 API Key、上传文件或生产数据。
- 本项目曾在本地开发过程中使用真实 Key，正式开源或部署前应重新生成 Key 并废弃旧 Key。
- 公开演示前请修改 `ADMIN_PASSWORD`、`JWT_SECRET_KEY` 和数据库密码。
- 样例文档均为虚构资料，不要把真实客户合同、员工信息或内部机密放进公开仓库。

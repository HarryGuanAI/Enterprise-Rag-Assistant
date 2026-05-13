# Enterprise RAG Assistant

企业知识库智能问答助手，也叫 **云舟知识库助手**。这是一个面向 AI Agent / RAG 开发岗位作品集的企业级 RAG 应用示例，覆盖文档入库、向量检索、Hybrid Search、轻量 Rerank、严格拒答、引用溯源、多轮对话、游客限额、评测闭环和云服务器部署。

项目目标不是做一个简单聊天框，而是展示一个可部署、可演示、可开源、能讲清楚工程取舍的企业知识库助手。

## 在线演示

- 演示地址：http://117.72.45.27
- 健康检查：http://117.72.45.27/health
- 演示数据：8 份虚构企业文档，36 个 chunks
- 线上评测：37 条 golden QA，Hybrid + Rerank 模式下检索命中率、拒答准确率、关键词覆盖均为 `1.00`

说明：公网演示环境只导入 `sample_docs/` 中的虚构资料，不包含真实业务数据。演示环境可能因成本控制或维护临时不可用，本地 Docker Compose 部署方式见下文。

## 功能特性

- 管理员登录与游客模式
- 游客每日 15 次问答限制，附加 IP 日兜底限制
- PDF、DOCX、Markdown、TXT 文档上传
- 文档异步解析、混合分块、向量化入库
- DashScope `text-embedding-v4` Embedding
- PostgreSQL + pgvector 向量检索
- Hybrid Search：向量召回 + 中文关键词召回融合
- 轻量 Rerank：基于向量分、关键词覆盖和内容相关性的二次排序
- 严格拒答：知识库依据不足时不调用 LLM
- DeepSeek `deepseek-chat` SSE 流式回答
- 回答生成中支持手动停止
- 多轮对话、历史会话列表、继续追问
- 多轮拒答修复：只有明显追问才带历史检索，独立新问题只按当前问题检索
- 能力咨询意图识别：例如“你能做什么”直接本地回答，跳过 Embedding、检索和 LLM
- 引用来源、相似度分数、检索调试信息展示
- 点击引用标签打开全文预览，并滚动高亮到命中 chunk
- 37 条 golden QA 评测集和评测脚本
- Docker Compose 一键部署

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Next.js 14, React 18, Tailwind CSS, TanStack Query, lucide-react |
| 后端 | FastAPI, SQLAlchemy 2.x, Pydantic, Alembic |
| 数据库 | PostgreSQL + pgvector |
| Embedding | DashScope `text-embedding-v4` |
| 生成模型 | DeepSeek `deepseek-chat` |
| 部署 | Docker Compose, Nginx |

## 架构概览

```text
Browser
  |
  | HTTP / SSE
  v
Next.js Frontend
  |
  | REST API
  v
FastAPI Backend
  |
  | SQL + Vector Search
  v
PostgreSQL + pgvector

FastAPI Backend
  |                         |
  | Embedding API            | Chat Completion API
  v                         v
DashScope                   DeepSeek
```

核心链路：

```text
文档上传
-> 文档解析
-> 混合分块
-> DashScope Embedding
-> 写入 PostgreSQL + pgvector
-> 用户提问
-> 向量检索 / Hybrid Search / Rerank
-> 严格拒答判断
-> DeepSeek 流式生成
-> 引用来源与全文预览
```

## 快速开始

### 1. 准备环境

需要安装：

- Docker
- Docker Compose
- DashScope API Key
- DeepSeek API Key

### 2. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

至少填写：

```text
DASHSCOPE_API_KEY=your_dashscope_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
ADMIN_PASSWORD=change-me-please
JWT_SECRET_KEY=please-change-this-secret
POSTGRES_PASSWORD=rag_password
```

如果部署到公网，还需要按实际域名或公网地址设置：

```text
BACKEND_CORS_ORIGINS=https://your-frontend-domain.example
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.example
```

### 3. 启动服务

```bash
docker compose up -d --build
```

访问：

- 前端：http://localhost:3000
- 后端健康检查：http://localhost:8000/health
- 后端 API 文档：http://localhost:8000/docs

## 样例知识库

`sample_docs/` 提供一组虚构企业文档，覆盖：

- 员工手册
- 报销制度
- 休假制度
- IT 服务指南
- 产品 FAQ
- 客服工单规范
- 销售合同流程
- 数据安全规范

批量导入：

```bash
docker compose run --rm \
  -v "./sample_docs:/app/sample_docs" \
  backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

Windows PowerShell：

```powershell
docker compose run --rm -v "${PWD}/sample_docs:/app/sample_docs" backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

导入过程会调用 DashScope Embedding，因此需要先配置 `DASHSCOPE_API_KEY`。

## 运行评测

纯向量基线：

```bash
docker compose run --rm \
  -v "./evals:/app/evals" \
  -v "./backend/app/evals:/app/app/evals" \
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --disable-hybrid-search --disable-rerank
```

Hybrid Search + 轻量 Rerank：

```bash
docker compose run --rm \
  -v "./evals:/app/evals" \
  -v "./backend/app/evals:/app/app/evals" \
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

当前 37 条样例评测结果：

| 模式 | 检索命中率 | 拒答准确率 | 关键词覆盖 |
|---|---:|---:|---:|
| 纯向量检索 | 1.00 | 1.00 | 1.00 |
| Hybrid + Rerank | 1.00 | 1.00 | 1.00 |

## 部署说明

本项目已经在云服务器上使用 Docker Compose + Nginx 完成公网部署。生产部署建议：

- 只开放 `80` 和 `443` 作为公网入口。
- PostgreSQL 不直接暴露公网。
- 前端、后端、数据库容器端口只绑定 `127.0.0.1`。
- 通过 Nginx 或 Caddy 做反向代理和 HTTPS。
- 真实 Key 和密码只放在服务器 `.env`，不要提交到 Git。

详细步骤见 [docs/deployment.md](docs/deployment.md) 和 [docs/maintenance.md](docs/maintenance.md)。

## 项目结构

```text
enterprise-rag-assistant/
├── backend/                 # FastAPI 后端
│   ├── app/api/             # API 路由
│   ├── app/services/        # 业务服务
│   ├── app/rag/             # RAG 主链路、检索、生成、分块、Embedding
│   ├── app/models/          # SQLAlchemy 模型
│   ├── app/schemas/         # Pydantic schemas
│   └── alembic/             # 数据库迁移
├── frontend/                # Next.js 前端
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
├── sample_docs/             # 虚构企业样例知识库
├── evals/                   # golden QA 评测集
├── docs/                    # 架构、部署、演示、安全、运维文档
└── docker-compose.yml
```

## 安全说明

- 不要提交 `.env`、真实 API Key、上传文件、生产数据或日志密钥。
- `.env.example` 只保留占位值，可安全提交。
- 本项目开发过程中曾使用真实 Key，正式开源或长期公网部署前应重新生成 Key，并废弃旧 Key。
- 公开演示前请修改 `ADMIN_PASSWORD`、`JWT_SECRET_KEY`、`POSTGRES_PASSWORD`。
- 样例文档均为虚构资料，不要把真实客户合同、员工信息、财务数据或内部机密放进公开仓库。
- 公网部署时不要直接暴露 PostgreSQL。

开源前检查见 [docs/security-and-open-source-checklist.md](docs/security-and-open-source-checklist.md)。

## 面试讲法

可以用这一条主线介绍项目：

> 我做了一个企业知识库 RAG 助手，并部署到了云服务器公网演示环境。管理员上传制度文档后，系统会解析、分块、向量化并写入 PostgreSQL + pgvector。用户提问时，系统先做向量检索，可选 Hybrid Search 和轻量 Rerank，再根据相似度和当前问题支持度做严格拒答。命中可靠上下文时，系统把引用片段拼进 Prompt，调用 DeepSeek 流式生成答案，并展示引用来源、全文预览和检索调试信息。

重点可以展开：

- 为什么第一版不用 LangChain：为了拆开 RAG 关键环节，便于理解、调试和面试讲解。
- 为什么要严格拒答：知识库依据不足时不让模型自由发挥，同时节省 LLM 成本。
- 为什么做 Hybrid Search：向量召回负责语义泛化，关键词召回补足专有名词、数字和制度原文匹配。
- 为什么做轻量 Rerank：用低成本方式展示召回和精排的分层设计，后续可替换为模型 Rerank。
- 为什么做多轮对话拒答修复：多轮 RAG 不能简单拼历史，否则历史上下文会污染独立新问题。
- 为什么做意图识别：能力咨询和使用说明不需要走 RAG 链路，本地规则回答更快、更稳定、更省钱。
- 为什么做评测集：RAG 优化不能只靠感觉，要用 golden QA 看命中率、拒答准确率和关键词覆盖。
- 为什么部署到云服务器：展示从代码、模型调用、数据库、容器编排、反向代理到安全边界的完整工程能力。

## Roadmap

- 接入域名和 HTTPS。
- 补充 README 截图和演示 GIF。
- 录制 3-5 分钟项目演示视频。
- 增加 LangChain / LangGraph 对照版本。
- 接入模型 Rerank 或本地 bge-reranker。
- 增加多知识库和更完整的管理员审计能力。
- 为长期公网演示增加更细粒度的速率限制和监控。

## 文档

- [架构设计](docs/architecture.md)
- [部署说明](docs/deployment.md)
- [运维维护手册](docs/maintenance.md)
- [面试演示脚本](docs/demo-script.md)
- [复盘与面试准备](docs/interview-retrospective-2026-05-12.md)
- [开源前安全检查](docs/security-and-open-source-checklist.md)
- [评测说明](evals/README.md)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

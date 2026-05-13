# Enterprise RAG Assistant

**Enterprise RAG Assistant（云舟知识库助手）** 是一个面向企业内部知识库场景的开源 RAG 应用。系统支持多格式文档上传、异步解析入库、DashScope Embedding、PostgreSQL/pgvector 检索、Hybrid Search、轻量 Rerank、严格拒答、引用溯源、多轮对话、游客限额和 Docker Compose 部署。

项目关注 RAG 应用在真实业务环境中的工程完整性：检索结果可追溯、回答边界可控制、效果可评测、服务可部署、运维有安全边界。

## 在线体验

- 访问地址：http://117.72.45.27
- 健康检查：http://117.72.45.27/health
- 示例数据：11 份虚构企业制度文档，57 个 chunks，覆盖 Markdown、TXT、DOCX、PDF
- 评测集：73 条 golden QA，覆盖制度细则、例外场景、金额阈值、审批链路和拒答问题

说明：在线环境只导入 `sample_docs/` 中的虚构资料，不包含真实业务数据。服务可能因成本控制或维护临时不可用，本地 Docker Compose 部署方式见下文。

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
- 73 条 golden QA 评测集和评测脚本
- Docker Compose 一键部署

## 技术亮点

- **自研轻量 RAG 编排**：显式实现解析、分块、Embedding、召回、拒答、Prompt 拼接和流式生成，便于排查和替换任意环节。
- **Hybrid Search**：将向量语义召回和中文关键词召回融合，兼顾语义泛化、专有名词、数字和制度原文匹配。
- **轻量 Rerank**：基于向量分、关键词覆盖和内容相关性二次排序，在不引入额外模型成本的前提下提升排序稳定性。
- **严格拒答策略**：Top1 相似度不足或命中片段无法支撑当前问题时直接拒答，降低幻觉和无依据回答。
- **多轮检索防污染**：只在明显追问时带入历史上下文，独立新问题按当前问题重新检索，避免历史问题污染召回。
- **可追溯引用**：回答保存引用快照，前端支持引用标签、全文预览、命中 chunk 滚动和高亮。
- **评测闭环**：提供 73 条 golden QA，统计检索命中率、拒答准确率、关键词覆盖和 Top1 分数。
- **部署安全边界**：Docker Compose + Nginx 部署，公网只开放入口端口，数据库和内部服务不直接暴露。

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

## 示例知识库

`sample_docs/` 提供一组虚构企业文档，覆盖：

- 员工手册、考勤、远程办公和休假规则
- 费用报销、差旅、业务招待和礼品合规
- 信息安全、数据分级、API Key 和 AI 工具使用边界
- 销售合同、报价审批、用印、回款和变更
- 客服工单分类、SLA、升级研发和故障复盘
- 采购付款、供应商准入、验收和黑名单
- 产品 FAQ、文档格式、严格拒答、引用来源和多轮对话
- 入职、转正、离职、绩效、薪酬、福利、研发发布和变更冻结

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

当前 73 条样例评测集用于覆盖常见问题和刁钻边界问题。以下为本地纯净数据库导入 11 份示例文档后的评测结果。

| 模式 | 检索命中率 | 拒答准确率 | 关键词覆盖 |
|---|---:|---:|---:|
| 纯向量检索 | 0.9851 | 0.7808 | 0.9627 |
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
├── sample_docs/             # 虚构企业示例知识库，覆盖 md/txt/docx/pdf
├── evals/                   # golden QA 评测集
├── docs/                    # 架构、部署、安全、运维文档
├── tools/                   # 示例资料生成脚本
└── docker-compose.yml
```

## 安全说明

- 不要提交 `.env`、真实 API Key、上传文件、生产数据或日志密钥。
- `.env.example` 只保留占位值，可安全提交。
- 本项目开发过程中曾使用真实 Key，正式公开或长期公网部署前应重新生成 Key，并废弃旧 Key。
- 生产部署前请修改 `ADMIN_PASSWORD`、`JWT_SECRET_KEY`、`POSTGRES_PASSWORD`。
- 示例文档均为虚构资料，不要把真实客户合同、员工信息、财务数据或内部机密放进公开仓库。
- 公网部署时不要直接暴露 PostgreSQL。

开源前检查见 [docs/security-and-open-source-checklist.md](docs/security-and-open-source-checklist.md)。

## Roadmap

- 接入域名和 HTTPS。
- 补充产品截图和运行示例。
- 增加 LangChain / LangGraph 对照版本。
- 接入模型 Rerank 或本地 bge-reranker。
- 增加多知识库、用户体系和权限审计。
- 增加更细粒度的限流、监控和成本统计。
- 支持更多文档解析能力，例如 OCR、表格抽取和结构化元数据。

## 文档

- [架构设计](docs/architecture.md)
- [部署说明](docs/deployment.md)
- [运维维护手册](docs/maintenance.md)
- [开源前安全检查](docs/security-and-open-source-checklist.md)
- [评测说明](evals/README.md)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

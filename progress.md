# Enterprise RAG Assistant 进度记录

## 2026-05-12 补充记录：RAG 问答链路接入

### 已完成
- 接入 DashScope Embedding 适配器，使用 OpenAI 兼容 Embeddings 接口，固定 `text-embedding-v4` 1024 维输出。
- 增加 Alembic 迁移，将 `document_chunks.embedding` 明确调整为 `vector(1024)`，并验证数据库迁移版本为 `20260512_0002`。
- 文档上传后的后台入库流程已变为：解析文档 -> 混合分块 -> 调用 DashScope Embedding -> 写入 pgvector。
- 新增 pgvector 检索器：按默认知识库过滤 ready 文档，使用 cosine distance 做 Top-K 检索，并输出相似度分数。
- 新增 DeepSeek 流式生成适配器：兼容 Chat Completions SSE，支持 `temperature` 和 `max_tokens` 配置。
- `/api/chat/stream` 从占位流升级为真实 RAG 链路：读取设置 -> 生成问题向量 -> 向量检索 -> 严格拒答 -> DeepSeek 流式回答 -> 保存消息和引用。
- 游客模式问答限制已接入聊天入口：单游客每日 2 次，并增加 IP 日限额兜底。
- 前端聊天输入框、发送按钮、流式回答、状态提示、错误提示、引用来源展示已接入真实 SSE。
- 新版前端生产构建通过，并在宿主机 `http://127.0.0.1:3004` 启动。
- 修复前端 SSE 解析兼容问题：同时支持 `\n\n` 和 `\r\n\r\n` 事件分隔，避免页面一直停在“正在生成回答...”。
- 增加管理员“重新入库”能力：失败或已入库文档可重新触发解析、分块、Embedding 和 pgvector 写入，不需要重新上传文件。

### 当前阻塞
- 本地 `.env` 里 `DASHSCOPE_API_KEY` 仍是占位值，因此真实上传入库和真实问答会停在“未配置 DASHSCOPE_API_KEY”。
- 需要用户在本机 `.env` 自行填写 `DASHSCOPE_API_KEY`，后续 DeepSeek 真实回答还需要填写 `DEEPSEEK_API_KEY`。不要把 API Key 发到聊天里。

### 验证记录
| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过：`python -m compileall backend\app` |
| 前端生产构建 | 通过：`npm.cmd run build` |
| 后端 Docker 重建 | 通过：`docker compose up -d --build backend` |
| 健康检查 | 通过：`/health` 返回 ok |
| 工作台统计 API | 通过：`/api/stats` 返回真实统计 |
| 聊天 SSE 接口 | 通过：返回 status -> error -> done，错误为未配置 DashScope Key |
| 新版前端访问 | 通过：`http://127.0.0.1:3004` 返回 200，页面包含新版中文工作台 |
| 文档重新入库接口 | 通过：失败文档可被改回 `processing` 并触发后台任务 |

## 2026-05-12

### 已完成

- 确认项目 1 选择企业内部知识库 RAG 助手。
- 确认业务场景为虚构 SaaS 公司“云舟科技”内部知识库。
- 确认第一版目标是可部署、可展示、可开源成品。
- 确认单页工作台界面：左侧文档、中央聊天、右侧引用来源、顶部统计/设置。
- 确认技术栈：Next.js、FastAPI、DeepSeek、DashScope Embedding、PostgreSQL + pgvector、Docker Compose。
- 确认权限：管理员登录 + 游客模式，游客只能问 2 个问题。
- 确认管理员功能：上传、删除、清空知识库、重建索引。
- 确认文档异步入库、本地文件存储、SSE 流式输出、严格拒答、聊天历史、统计卡片。
- 确认支持 PDF、DOCX、Markdown、TXT；第一版不支持 `.doc`。
- 确认混合分块策略、设置面板、Rerank 可选、Hybrid Search 可选、基础评测集。
- 确认基础评测范围：检索命中 + 答案关键词覆盖，不接入大模型自动评分。
- 确认多知识库策略：第一版页面只展示一个默认知识库，但数据模型预留 `knowledge_base_id`。
- 确认成本展示策略：第一版只展示调用次数和问答次数，不估算金额。
- 确认命名：GitHub 仓库名 `enterprise-rag-assistant`，页面产品名“云舟知识库助手”，README 标题“Enterprise RAG Assistant：企业知识库智能问答助手”。
- 确认数据库迁移工具：Alembic。
- 确认 ORM：SQLAlchemy 2.x + Pydantic。
- 确认数据库访问策略：同步 SQLAlchemy；DeepSeek/DashScope 调用和 SSE 使用异步。
- 确认后端依赖管理：`requirements.txt` + pip。
- 确认前端包管理：npm。
- 确认引用来源存储：`messages.citations_json` 快照 + `message_citations` 结构化关联。
- 确认数据库主键：核心业务表使用 UUID。
- 确认删除策略：文档软删除，chunks 物理删除，本地原始文件第一版删除。
- 确认前端 UI 组件方案：shadcn/ui + Tailwind CSS。
- 确认前端状态管理：TanStack Query。
- 确认 SSE 流式协议：使用 status、answer_delta、citations、done、error 多事件类型。
- 创建架构设计文档：`docs/architecture.md`。
- 创建文件化计划：`task_plan.md`、`findings.md`、`progress.md`。
- 创建项目脚手架：后端 FastAPI 目录、前端 Next.js 目录、Docker Compose、环境变量示例、README 初版。
- 创建 SQLAlchemy 模型和 Alembic 初始迁移。
- 创建前端单页工作台静态骨架。
- 安装前端依赖，收敛到 Next.js 14 + React 18 稳定组合。
- 前端生产构建通过：`npm run build`。
- 前端生产模式启动成功，`http://localhost:3000` 返回 200，并确认页面包含“云舟知识库助手”。
- 实现默认知识库和默认 RAG 设置服务：`knowledge_base_service.py`、`settings_service.py`。
- 实现统计服务：从文档、分块、消息和模型调用日志表统计工作台数据。
- 实现文档列表真实数据库接口。
- 前端统计卡片和文档列表接入后端 API，并保留后端不可用时的演示兜底数据。
- 前端最新版本构建通过，并在宿主机 `http://127.0.0.1:3001` 启动成功。
- 实现管理员登录弹窗：账号、密码、错误提示、登录状态、退出登录。
- 前端封装 `apiPost`，支持 JSON POST 和 Bearer Token。
- 上传按钮在游客模式下禁用，提示需要管理员登录。
- 登录新版前端构建通过，并在宿主机 `http://127.0.0.1:3002` 启动成功。
- 启动 Docker Desktop 后，使用 Docker Compose 启动 PostgreSQL + pgvector 和 backend。
- 后端容器启动时成功执行 Alembic 初始迁移。
- 验证 `/health`、`/api/stats`、`/api/documents`、`/api/auth/login` 均可访问。
- 更新 CORS 配置，允许 `127.0.0.1:3002` 访问后端。
- 验证浏览器来源 `http://127.0.0.1:3002` 调用登录接口返回 200 和 JWT。
- 实现后端管理员上传接口：校验文件类型/大小、保存原始文件、创建 `documents` 记录。
- 上传接口支持 `.pdf/.docx/.md/.txt`，并对 Windows/curl 中文文件名编码做兜底修正。
- 前端上传按钮接入文件选择和 multipart 上传，游客模式禁用，管理员模式可用。
- 验证 API 上传示例文档成功，`/api/documents` 返回中文文件名、状态 `processing`。
- 上传新版前端构建通过，并在宿主机 `http://127.0.0.1:3003` 启动成功。
- 实现文档解析器：Markdown/TXT、文本型 PDF、DOCX。
- 实现混合分块器：标题/段落优先，过长内容按固定长度和 overlap 切分。
- 上传后接入 FastAPI BackgroundTasks，自动执行解析和分块。
- 修正短章节被 `min_chunk_size` 过滤的问题，短制度条款也会保留为 chunk。
- 验证上传《员工手册.md》后状态从 `processing` 变为 `ready`，生成 3 个 chunks。

### 当前讨论点

- 文档解析和混合分块已可用。下一步接入 DashScope Embedding，把 chunks 写入向量。

### 验证记录

| 检查项 | 结果 |
|---|---|
| Python 语法编译 | 通过 |
| 前端依赖安装 | 通过 |
| 前端生产构建 | 通过 |
| 前端本地访问 | 通过，`http://localhost:3000` |
| 前端最新版本访问 | 通过，`http://127.0.0.1:3001` |
| 登录前端版本访问 | 通过，`http://127.0.0.1:3002` |
| Docker Compose 后端 | 通过，PostgreSQL healthy，backend up |
| Alembic 迁移 | 通过，初始 schema 已执行 |
| 登录 API | 通过，返回 JWT |
| CORS | 通过，允许 `http://127.0.0.1:3002` |
| 上传 API | 通过，示例 Markdown 文件写入 `documents` |
| 上传前端版本访问 | 通过，`http://127.0.0.1:3003` |
| 文档解析/分块 | 通过，示例 Markdown 生成 chunks |

### 遇到的问题

| 问题 | 处理 |
|---|---|
| PowerShell 阻止 `npm.ps1` | 改用 `npm.cmd` |
| npm 默认缓存目录无权限 | 使用项目内 `.npm-cache`，并加入 `.gitignore` |
| 较新的前端依赖在镜像中解析失败 | 收敛到 Next.js 14.2.5 + React 18.3.1 |
| Next 14 不支持 `next.config.ts` | 改为 `next.config.mjs` |
| 重启前端时不能停止所有 Node 进程 | 改为在新端口 3001 启动最新版本，避免影响其他服务 |
| Docker daemon 未启动 | 启动 Docker Desktop 后继续 |
| Docker API 需要宿主机权限 | 使用经过批准的 Docker Compose 命令 |
| 前端 3002 跨域调用后端 | 补充本地开发 CORS 白名单 |
| 命令行上传中文文件名可能乱码 | 后端增加 latin-1 -> UTF-8 文件名修正兜底 |
| 短章节被最小长度过滤导致 0 chunks | 调整分块策略，短条款也保留为 chunk |

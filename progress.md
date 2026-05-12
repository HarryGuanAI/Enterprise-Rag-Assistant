# Enterprise RAG Assistant 进度记录

## 2026-05-12 页面布局与评测基准优化

### 已完成
- 将工作台改为固定视口高度布局：顶部信息区固定，左侧文档列表、中间聊天记录、右侧引用来源分别在各自区域内滚动，避免每次输入都要拖动整页到底部。
- 聊天输入区固定在中间问答面板底部，并增加消息自动滚动锚点，连续问答时更接近真实产品体验。
- 新增基础 RAG 评测集 `evals/golden_qa.jsonl` 和评测脚本 `backend/app/evals/run_eval.py`，用于验证检索命中、拒答准确率和关键词覆盖。
- 根据评测结果将严格拒答默认阈值从 `0.35` 调整为 `0.60`，并同步更新当前数据库配置。

### 验证记录
| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过：`python -m compileall backend\app` |
| 前端生产构建 | 通过：`npm.cmd run build` |
| 前端访问 | 通过：`http://127.0.0.1:3004` 返回 200 |
| 后端统计 API | 通过：`/api/stats` 返回真实统计 |
| RAG 评测 | 通过：10 条样例，检索命中率 1.00，拒答准确率 1.00，关键词覆盖均值 1.00 |

## 2026-05-12 真实模型 API 验证

### 已完成
- 已在本地 `.env` 接入 DashScope API Key 和 DeepSeek API Key；`.env` 已被 `.gitignore` 忽略，不会进入 Git 提交。
- 重启 backend 后，DashScope Embedding 调用成功，小文档可重新入库并生成向量分块。
- 《员工手册.md》重新入库成功，生成 3 个 chunks；问题“新员工入职第一周需要完成哪些事项？”命中 `入职流程`，Top1 相似度 0.8181，并由 DeepSeek 流式生成正确回答。
- 《报销制度.md》重新入库成功，生成 3 个 chunks；问题“出差报销需要提交哪些材料？”命中 `差旅报销`，Top1 相似度 0.6899，并由 DeepSeek 流式生成正确回答。
- 严格拒答阈值已恢复为 `min_similarity=0.35`。

### 注意事项
- 用户曾在聊天中发送过 API Key。当前本地开发可以继续使用，但正式长期使用或开源前建议到平台重新生成 Key，并作废这次暴露过的 Key。
- PowerShell 直接发送中文 JSON 时可能出现编码干扰；前端浏览器请求使用 UTF-8，验证链路应优先以网页为准。

## 2026-05-12 检索调试与回答渲染优化

### 已完成
- 后端 SSE 增加 `retrieval_debug` 事件，返回 TopK、相似度阈值、Top1 分数、严格拒答状态、Embedding 模型、生成模型、Hybrid/Rerank 开关和是否调用 LLM。
- 前端右侧增加“检索调试”卡片，展示本次问答为什么调用模型或为什么拒答。
- 回答气泡增加轻量 Markdown 渲染：`**重点**` 会显示为加粗，短横线列表和数字列表会按结构化排版展示。
- 优化回答区样式，避免模型返回的 Markdown 符号直接堆在气泡中导致阅读凌乱。

### 验证记录
| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过 |
| 前端生产构建 | 通过 |
| 后端 SSE | 通过：返回 `retrieval_debug`、`citations`、`answer_delta` |
| 前端访问 | 通过：`http://127.0.0.1:3004` 返回 200 |

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
- 增加管理员 RAG 设置面板：可调整 TopK、相似度阈值、严格拒答、分块大小、overlap、最小分块、章节路径、temperature、max tokens、Hybrid/Rerank 预留开关。

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
| RAG 设置 API | 通过：`GET/PUT /api/settings` 可读取并保存配置 |
| RAG 设置前端 | 通过：前端生产构建成功，3004 服务已重启 |

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
# 2026-05-12 检索优化能力展示

## 已完成

- 将设置面板里的 `enable_hybrid_search` 从占位开关接入真实检索逻辑：向量召回之外增加关键词召回，支持中文短语与 n-gram 匹配，并按文档标题、章节路径、chunk 内容计算关键词分。
- 实现向量候选和关键词候选融合排序，保留每条引用的 `vector_score`、`keyword_score` 和 `source`，便于前端调试和面试讲解。
- 将 `enable_rerank` 接入轻量 Rerank：使用向量分与关键词覆盖做二次排序，不额外调用模型，控制成本和延迟。
- 修正 Rerank 分数校准：Rerank 不降低已有向量置信度，避免把原本应回答的问题压到 `min_similarity=0.60` 以下。
- SSE `retrieval_debug` 新增实际检索模式、向量候选数、关键词候选数和最终入选数；前端右侧调试面板同步展示。
- 评测脚本新增 `--enable-hybrid-search` 和 `--enable-rerank` 参数，可以直接对比不同检索模式。
- 已将 Hybrid Search、轻量 Rerank、面试讲法和验证结果合并到 `docs/interview-retrospective-2026-05-12.md`，避免面试讲解文档分散。

## 验证记录

| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过：`python -m compileall backend\app` |
| 前端生产构建 | 通过：`npm.cmd run build` |
| backend Docker 重建 | 通过：`docker compose up -d --build backend` |
| Hybrid + Rerank 容器自测 | 通过：返回 `mode=hybrid+rerank`，向量候选 20，关键词候选 9，最终入选 5 |
| 纯向量评测 | 通过：10 条样例，检索命中率 1.00，拒答准确率 1.00 |
| Hybrid + Rerank 评测 | 通过：10 条样例，检索命中率 1.00，拒答准确率 1.00 |
# 2026-05-12 样例知识库与评测集扩展

## 已完成

- 新增 6 份示例知识库文档：休假制度、IT 服务指南、产品 FAQ、客服工单规范、销售合同流程、数据安全规范。
- 将 `evals/golden_qa.jsonl` 从 10 条扩展到 37 条，覆盖企业内部常见问题、专有名词问题、流程制度问题和知识库外拒答问题。
- 新增 `backend/app/evals/ingest_sample_docs.py`，可批量导入 `sample_docs` 并复用正式入库流程生成 chunks 和 embeddings。
- 前端问答输入区新增 6 个示例问题按钮，方便游客和面试官快速体验命中引用、检索调试和严格拒答。
- 更新 `evals/README.md` 和 README，补充样例知识库导入与评测说明。
- 为评测脚本新增 `--disable-hybrid-search` 和 `--disable-rerank`，避免纯向量基线受数据库设置面板当前开关影响。

## 面试价值

- 知识库从“两份制度文档”扩展为更完整的企业内部资料集合，演示更像真实业务场景。
- 评测集覆盖面更广，可以更有说服力地讲“用 golden set 驱动 RAG 优化”。
- 示例问题降低演示门槛，面试官打开页面后能直接知道该怎么问。

## 验证记录

| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过：`python -m compileall backend\app` |
| 评测集 JSONL 解析 | 通过：37 条样例，其中 5 条拒答样例 |
| 前端生产构建 | 通过：`npm.cmd run build` |
| 样例知识库批量导入 | 通过：8 份 `sample_docs` 全部入库 |
| 纯向量评测 | 通过：37 条样例，检索命中率 1.00，拒答准确率 1.00，关键词覆盖 1.00 |
| Hybrid + Rerank 评测 | 通过：37 条样例，检索命中率 1.00，拒答准确率 1.00，关键词覆盖 1.00 |

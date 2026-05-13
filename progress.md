# Enterprise RAG Assistant 进度记录

## 2026-05-13 京东云公网部署与上线验证

### 已完成
- 在京东云 2 核 4GB / 60GB SSD / 5Mbps 云服务器上完成公网部署。
- 服务器系统为 Ubuntu 24.04 LTS，项目目录为 `/opt/enterprise-rag-assistant`。
- 安装并启用 Docker、Docker Compose、Nginx。
- 配置 Docker 镜像加速器，解决国内服务器拉取 Docker Hub 镜像超时问题。
- 后端 Docker 构建增加 `PIP_INDEX_URL` build arg，默认使用阿里云 PyPI 镜像，解决 pip 下载超时问题。
- 前端 Docker 构建增加 `NEXT_PUBLIC_API_BASE_URL` build arg，确保生产构建能指向公网 API 地址。
- 补充 `frontend/public/.gitkeep`，避免前端 Dockerfile 在没有 public 目录时复制失败。
- Nginx 配置公网 `80` 入口：`/` 转发到前端，`/api`、`/health`、`/docs` 转发到后端。
- Docker Compose 端口改为只绑定 `127.0.0.1`：前端 `3000`、后端 `8000`、PostgreSQL `5432` 不直接监听公网。
- 启用 UFW，仅放行 `22`、`80`、`443`。
- 增加 Docker `DOCKER-USER` 防护规则，阻断公网直连 `3000`、`8000`、`5432`，并创建 systemd 服务保证规则在 Docker 启动后恢复。
- 服务器 `.env` 已由用户自行填入新 Key 和新密码；没有在聊天或文档中展示真实 Key。
- 修改 PostgreSQL 密码后，删除空数据卷并重新初始化数据库。
- 初始上线导入 8 份 `sample_docs/` 虚构企业样例文档，生成 36 个 chunks。
- 当前已将样例知识库升级为 11 份虚构企业制度文档，覆盖 Markdown、TXT、DOCX、PDF；本地纯净验证生成 57 个 chunks。
- 当前 golden QA 已扩展到 73 条，覆盖制度细则、例外场景、金额阈值、审批链路和拒答问题。

### 当前公网地址
- 前端页面：http://117.72.45.27
- 健康检查：http://117.72.45.27/health
- API 统计：http://117.72.45.27/api/stats

### 上线验证记录
| 检查项 | 结果 |
|---|---|
| 前端公网访问 | 通过：HTTP 200，页面包含“云舟知识库助手” |
| 后端健康检查 | 通过：`/health` 返回 200 |
| API 统计 | 初始上线通过：`/api/stats` 返回 8 个文档、36 个 chunks、游客剩余 15/15 |
| PostgreSQL | 通过：容器 healthy |
| 样例知识库导入 | 本地纯净验证通过：11 份文档全部入库，生成 57 个 chunks |
| 纯向量评测 | 73 条样例：检索命中率 0.9851，拒答准确率 0.7808，关键词覆盖 0.9627 |
| Hybrid + Rerank 评测 | 73 条样例：检索命中率 1.00，拒答准确率 1.00，关键词覆盖 1.00 |

### 安全提醒
- 用户曾在聊天中暴露云服务器 root 密码，必须在京东云控制台修改 root 密码。
- 长期演示建议改用 SSH Key 登录，并关闭 root 密码登录。
- 真实 API Key 只保存在服务器 `.env`，不要写入 README、截图、提交信息或 issue。
- 公开仓库前继续确认 `.env`、`storage/uploads/`、真实业务文档、日志密钥没有进入 Git。

### 面试价值
- 项目已经从“本地可演示”推进到“公网可访问、可部署、可运维”的状态。
- 可以讲清楚 RAG 工程除了检索和生成，还包括云服务器部署、反向代理、环境变量管理、端口安全、镜像源问题处理和上线后评测。

## 2026-05-12 多轮对话拒答修复

### 已完成
- 修复多轮对话中“历史上下文污染检索”的问题：只有明显追问才把历史对话拼入检索查询。
- 对独立新问题，检索只使用当前问题，避免上一轮主题把召回结果拉偏。
- 新增当前问题支持度校验：如果命中片段不能支撑当前问题，即使向量分过线也会严格拒答并返回空引用。
- `retrieval_debug` 增加 `used_history_for_retrieval` 和 `current_question_supported` 字段，方便解释为何拒答或调用模型。

### 验证记录
| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过：`python -m compileall backend\app` |
| 前端生产构建 | 通过：`npm.cmd run build` |
| 后端 Docker 重建 | 通过：`docker compose up -d --build backend` |
| HTTP 黑盒测试 | 通过：同一 conversation 内先问能力说明，再问“年会奖品是什么？”，返回 `refused=true`、`will_call_llm=false`、引用为空 |

## 2026-05-12 游客配额展示与管理员联系方式

### 已完成
- 将默认游客每日问答上限从 2 次调整为 15 次，并把 IP 日兜底限额调整为 100 次，避免本机演示时 IP 限额先触发。
- 修正 `/api/stats`：前端会传入当前 `guest_id`，后端按 `guest_usage` 计算今日剩余次数，不再一直显示默认上限。
- 游客模式顶部新增醒目提示：由于页面仅用于学习展示，如想体验更多功能，请联系管理员进行登录。
- 新增“管理员联系方式”按钮，点击后弹窗展示中文和英文两种联系方式。
- 已在本地 `.env` 中仅更新游客限额相关字段，没有读取或展示任何 API Key。

### 联系方式
- 中文：管理员姓名：关海龙；联系电话：+86 15031597985。
- English：Administrator: Harry Guan; Phone: +86 15031597985.

## 2026-05-12 能力咨询意图识别快路径

### 已完成
- 后端新增规则型轻量意图识别，覆盖“你能做什么”“你有哪些功能”“怎么使用你”等产品能力咨询。
- 命中能力咨询时，系统直接返回云舟知识库助手能力说明，跳过 DashScope Embedding、pgvector 检索和 DeepSeek 调用。
- 能力咨询仍会保存到当前 conversation/messages，历史对话可回看；但不会消耗游客问答额度和模型调用成本。
- 前端示例问题新增“你能做什么？”，方便面试演示快路径。
- README、架构文档、演示脚本已补充意图识别讲法。

### 面试价值
- 可以说明 RAG 产品不应该所有输入都走同一条链路：先做轻量意图路由，把产品说明、使用帮助等问题走低成本快路径。
- 这体现了 AI Agent 工程里的编排意识：根据用户意图选择工具/链路，而不是一律 Embedding + 检索 + LLM。

## 2026-05-12 多轮对话与历史会话

### 已完成
- 后端新增历史会话列表和会话详情接口：`GET /api/chat/conversations`、`GET /api/chat/conversations/{conversation_id}`。
- 问答链路升级为多轮：创建/复用 conversation，保存用户和助手消息，并在检索查询与生成 Prompt 中加入最近对话上下文。
- 前端问答区右上角新增“开启新对话”按钮，可清空当前上下文并开始新的 conversation。
- 左侧栏新增“历史对话”切换按钮；切换后不再展示文档卡片，而是展示历史对话卡片。
- 点击历史对话卡片可加载该会话的历史消息和引用快照，继续追问时会沿用该 conversation。

### 验证记录
| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过：`python -m compileall backend\app` |
| 前端生产构建 | 通过：`npm.cmd run build` |
| 后端 Docker 重建 | 通过：`docker compose up -d --build backend` |
| 后端健康检查 | 通过：`/health` 返回 200 |
| 历史会话列表 API | 通过：游客 guest_id 查询返回正常 JSON |
| diff 空白检查 | 通过：仅有 Windows LF/CRLF 提示 |

### 面试价值
- 可以说明 RAG 助手从“单轮检索问答”升级到“会话型 Agent 体验”：不仅保存历史，还让追问能利用最近上下文。
- 工程上可以讲清楚 conversation、messages、citation snapshot 的职责边界，以及为什么最近对话只取有限窗口来控制 Prompt 长度。

## 2026-05-12 全文文档预览与引用定位

### 已完成
- 新增 `GET /api/documents/{document_id}/preview`，返回解析后的文档全文和每个 chunk 在全文中的字符区间。
- 后端预览接口复用正式文档解析器，并按 chunk 顺序在全文中匹配位置；对带章节路径的 chunk 会去掉检索增强前缀后再定位。
- 前端引用预览抽屉升级为全文预览：点击回答下方引用标签或右侧引用卡片后，拉取整篇文档，并自动滚动/高亮到命中的 chunk。
- 保留降级体验：如果全文加载失败或 chunk offset 匹配不到，抽屉仍展示当次回答保存的引用快照。
- README、架构文档和面试演示脚本已同步更新。

### 验证记录
| 检查项 | 结果 |
|---|---|
| 后端 Python 编译 | 通过：`python -m compileall backend\app` |
| 前端生产构建 | 通过：`npm.cmd run build` |
| 后端 Docker 重建 | 通过：`docker compose up -d --build backend` |
| 预览接口 | 通过：ready 文档返回全文 1198 字、5 个 chunks、5 个 chunks 均定位到 offset |
| 前端访问 | 通过：重启 3004 后页面返回 200 |

### 面试价值
- 可以把“引用来源”从简单片段展示升级为“可回到原文上下文核验”，更贴近企业知识库审计和合规需求。
- 技术上可以讲：回答保存引用快照用于历史稳定展示，全文预览接口用于当前文档溯源，两者职责分离。

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
- 游客模式问答限制已接入聊天入口：单游客每日 15 次，并增加 IP 日限额兜底。
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
- 确认权限：管理员登录 + 游客模式，游客默认每日 15 次问答。
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
## 2026-05-12 开源部署与演示文档完善

### 已完成
- 重写 `.env.example`，只保留占位符和必要配置说明，避免示例环境文件出现真实密钥或乱码内容。
- 重写 README，使其更适合作为 GitHub 首页：包含项目定位、功能亮点、技术栈、快速启动、样例知识库、评测命令、面试讲法和安全提醒。
- 新增 `docs/deployment.md`，整理 Docker Compose 部署、环境变量、样例知识库导入、评测验证和故障排查。
- 新增 `docs/demo-script.md`，准备 5-8 分钟面试演示脚本，覆盖管理员登录、样例问题、引用来源、严格拒答、Hybrid Search、Rerank 和评测闭环。
- 新增 `docs/security-and-open-source-checklist.md`，整理开源前安全检查、API Key 轮换、环境变量、公开演示成本控制和面试安全讲法。
- README 已链接上述新增文档，形成“首页介绍 -> 部署 -> 演示 -> 安全检查”的开源文档链路。

### 面试价值
- 这一步把项目从“本地可跑”推进到“别人能看懂、能部署、能复现、能面试演示”的状态。
- 面试时可以强调：RAG 项目不只是检索和生成，还要包含部署、评测、安全、成本控制和可解释的演示路径。

## 2026-05-12 前端体验与停止输出优化

### 已完成
- 问答 SSE 请求接入 `AbortController`，回答生成中或输出卡住时，用户可以手动点击“停止”中断当前请求。
- 生成中发送按钮会切换为“停止”按钮，状态提示区域也提供一个轻量停止入口。
- 手动停止后会保留已经生成的内容，并在助手消息末尾标记“已手动停止输出”。
- 页面布局整体加宽，最大内容宽度提升到 1720px，三栏比例调整为文档 320px、右侧引用 400px，中间聊天区获得更多空间。
- 放大标题、统计卡、聊天输入框和消息气泡的内边距，减少压缩感。
- 优化全局背景、文本渲染和滚动条样式，让页面更适合面试演示。
- 根据页面批注继续收敛布局：去掉贯穿式大 Header，把统计卡压缩成一条轻量指标条，左侧文档栏收窄到 230px，右侧引用栏收窄到 300px，把主要空间留给问答区。
- 示例问题只在首次对话前展示，用户开始提问后自动隐藏，减少后续对话中的空间占用。
- 回答消息下方新增引用标签；点击标签或右侧引用卡片会打开右侧文档预览抽屉，并自动定位到命中的引用段落。

### 验证记录
| 检查项 | 结果 |
|---|---|
| 前端生产构建 | 通过：`npm.cmd run build` |
| 页面视觉检查 | 通过：`http://127.0.0.1:3005` 无横向/纵向溢出，输入框高度 84px |
| 停止输出交互 | 通过：模拟卡住的 SSE 请求，按钮切换为“停止”，点击后显示“已手动停止输出” |
| 页面批注回归 | 通过：`http://127.0.0.1:3004` 顶部高度 44px，左栏 230px，右栏 300px，开始对话后示例问题隐藏 |
| 引用预览交互 | 通过：模拟带引用的 SSE 响应，回答下方出现引用标签，点击后打开文档预览并显示命中段落 |

### 面试价值
- 可以说明这个项目不是只关注模型效果，也关注真实用户体验：流式输出必须能取消，否则网络慢、模型慢或连接卡住时体验很差。
- 技术上可以讲：前端用 `AbortController` 取消 fetch/SSE 请求，既停止 UI 等待，也关闭当前 HTTP 流，保留已生成内容作为部分结果。

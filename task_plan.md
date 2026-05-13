# Enterprise RAG Assistant 任务计划

## 最新状态：公网部署已完成

当前系统已经从本地可演示推进到公网可访问：

```text
京东云服务器 -> Docker Compose -> Nginx 反向代理 -> Next.js + FastAPI + PostgreSQL/pgvector
```

公网地址：http://117.72.45.27

上线后已完成：

- 8 份 `sample_docs/` 虚构企业文档导入。
- 36 个 chunks 入库。
- 37 条 golden QA 评测通过。
- Hybrid + Rerank 模式下检索命中率、拒答准确率、关键词覆盖均为 `1.00`。
- Nginx 作为公网入口，容器端口只绑定 `127.0.0.1`。
- UFW 只放行 `22/80/443`，并通过 Docker `DOCKER-USER` 规则阻断公网直连 `3000/8000/5432`。

## 最新验证结论

真实 DashScope Embedding、pgvector 检索、DeepSeek 生成链路已具备公网演示条件。当前系统可以完成：

```text
文档导入 -> DashScope Embedding -> pgvector 检索 -> Hybrid + Rerank -> 严格拒答 -> DeepSeek 流式回答 -> 引用来源
```

下一步重点从“部署上线”转向“求职展示材料”：README 截图/GIF、3-5 分钟演示视频、简历项目描述、GitHub 开源前最终安全检查。

## 最新阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| 阶段 4：文档管理与异步入库 | 已完成 | 上传、解析、混合分块、DashScope Embedding、pgvector 入库已完成 |
| 阶段 5：RAG 问答链路 | 已完成 | 检索、严格拒答、DeepSeek 流式生成、引用保存、多轮对话已完成 |
| 阶段 6：RAG 设置与优化开关 | 已完成 | Hybrid Search 和轻量 Rerank 已接入真实检索链路 |
| 阶段 7：基础评测集 | 已完成 | 37 条 golden QA，线上 Hybrid + Rerank 评测通过 |
| 阶段 8：前端工作台打磨 | 已完成 | 固定工作台布局、停止输出、引用全文预览已完成 |
| 阶段 9：部署与开源文档 | 基本完成 | 京东云公网部署完成，运维文档和安全清单已补充 |

## 下一步执行顺序

1. 去京东云控制台修改曾暴露过的 root 密码。
2. 准备域名和 HTTPS：域名解析到 `117.72.45.27`，再配置 Nginx/Caddy 证书。
3. 录制 3-5 分钟演示视频，按 `docs/demo-script.md` 展示命中回答、严格拒答、引用来源和评测结果。
4. 准备 README 截图/GIF，突出公网地址、引用溯源、检索调试和评测结果。
5. 做 GitHub 开源前最终安全检查：`.env`、上传文件、日志、截图、提交信息不能出现真实 Key。
6. 完善简历项目经历和面试讲稿，重点强调“RAG 全链路 + 部署运维 + 安全成本控制 + 评测闭环”。

## 项目目标

做出一个可部署、可展示、可开源的企业内部知识库 RAG 助手。项目需要让求职者能够讲清楚 RAG 全链路、工程取舍、检索优化、权限与成本控制、部署上线和后续 Agent 扩展方向。

## 当前阶段

阶段 2：项目脚手架搭建（进行中）

## 阶段计划

| 阶段 | 状态 | 目标 |
|---|---|---|
| 阶段 0：立项与需求确认 | 已完成 | 明确业务场景、功能边界、技术选型和优化路线 |
| 阶段 1：架构设计 | 已完成 | 设计前后端架构、数据模型、API、RAG 模块边界 |
| 阶段 2：项目脚手架 | 进行中 | 创建 FastAPI 后端、Next.js 前端、Docker Compose、基础配置 |
| 阶段 3：认证与配额 | 进行中 | 管理员登录、游客模式、游客 15 次问答限制、IP 日限额 |
| 阶段 4：文档管理与异步入库 | 进行中 | 上传、解析、混合分块、DashScope Embedding、pgvector 入库 |
| 阶段 5：RAG 问答链路 | 待开始 | DeepSeek 流式回答、严格拒答、引用来源、聊天历史 |
| 阶段 6：RAG 设置与优化开关 | 待开始 | 设置面板、TopK、阈值、分块参数、Rerank/Hybrid Search 开关 |
| 阶段 7：基础评测集 | 待开始 | 30-50 条示例问题、期望来源、检索命中 + 答案关键词评测脚本 |
| 阶段 8：前端工作台打磨 | 待开始 | 单页工作台、统计卡片、文档状态、引用来源展示 |
| 阶段 9：部署与开源文档 | 待开始 | README、部署文档、架构图、面试讲解文档、GitHub 开源准备 |

## 已确认决策

| 主题 | 决策 |
|---|---|
| 业务场景 | 虚构 SaaS 公司内部知识库助手 |
| 示例公司 | 云舟科技 Yunzhou Cloud |
| GitHub 仓库名 | `enterprise-rag-assistant` |
| 页面产品名 | 云舟知识库助手 |
| README 标题 | Enterprise RAG Assistant：企业知识库智能问答助手 |
| 页面形态 | 单页工作台 |
| 知识库形态 | 第一版展示单默认知识库，数据模型预留 `knowledge_base_id` |
| 前端 | Next.js + Tailwind CSS |
| 后端 | FastAPI |
| 生成模型 | DeepSeek API |
| Embedding | DashScope `text-embedding-v4` |
| 数据库/向量库 | PostgreSQL + pgvector |
| RAG 编排 | 第一版自研轻量链路，后续补 LangChain 对照版 |
| 部署 | Docker Compose |
| 数据库迁移 | Alembic |
| ORM | SQLAlchemy 2.x + Pydantic |
| 数据库访问 | 同步 SQLAlchemy；外部模型调用和 SSE 使用异步 |
| 后端依赖管理 | `requirements.txt` + pip |
| 前端包管理 | npm |
| 前端 UI 组件 | shadcn/ui + Tailwind CSS |
| 前端状态管理 | TanStack Query |
| 流式协议 | SSE 多事件类型：status、answer_delta、citations、done、error |
| 主键 ID | UUID |
| 删除策略 | 文档软删除，chunks 物理删除，本地文件第一版删除 |
| 登录 | 内置管理员账号 + 游客模式 |
| 游客限制 | 单游客每日 15 次问答，后端校验，附加 IP 日限额 |
| 文档格式 | PDF、DOCX、Markdown、TXT |
| DOC 支持 | 第一版不支持老 `.doc`，Roadmap 用 LibreOffice 转换支持 |
| 文档处理 | FastAPI BackgroundTasks 异步入库 |
| 文件存储 | 本地 `storage/uploads` + Docker volume |
| 分块策略 | 标题/段落 + 固定长度 + overlap 的混合分块 |
| 检索策略 | pgvector 向量检索，Hybrid Search 可选 |
| Rerank | 可选开关，默认关闭 |
| 拒答策略 | 严格拒答，低相关时不调用 DeepSeek |
| 流式输出 | SSE |
| 聊天历史 | 保存到数据库 |
| 统计卡片 | 文档数、分块数、今日问答、拒答数、游客剩余次数 |
| 成本展示 | 第一版只展示调用/问答次数，不估算金额 |
| 重建索引 | 管理员支持异步重建全部索引 |
| 清空知识库 | 管理员支持，需二次确认 |
| 评测集 | 第一版包含 30-50 条示例问题和基础评测脚本 |

## 待确认问题

1. 游客每日问答限制已实现，当前默认 15 次。
2. 管理员上传文件已完成第一段：前端选择文件 -> 后端保存文件 -> 创建 documents 记录。
3. 文档解析、混合分块和后台入库任务已完成。
4. 下一步接入 DashScope Embedding，生成向量并写入 pgvector。

## 错误与风险记录

| 风险 | 当前处理 |
|---|---|
| 公开演示被刷 API | 游客 15 次限制 + IP 日限额 + 管理员上传限制 |
| 文档入库接口超时 | 异步入库 + 文档状态轮询 |
| RAG 幻觉 | 严格拒答 + 引用来源 + 相似度阈值 |
| 解析复杂文档失败 | 明确第一版边界，失败状态记录错误信息 |
| `.doc` 解析不稳定 | 第一版不支持，Roadmap 用 LibreOffice 转换 |
| Rerank/Hybrid 增加复杂度 | 做成可选开关，默认主链路可运行 |

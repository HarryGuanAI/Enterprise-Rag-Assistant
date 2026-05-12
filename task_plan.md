# Enterprise RAG Assistant 任务计划

## 最新状态：页面可演示性与评测基准已增强

当前系统已经具备完整演示链路：

```text
文档上传/重新入库 -> DashScope Embedding -> pgvector 检索 -> 严格拒答 -> DeepSeek 流式回答 -> 引用来源展示
```

本轮新增了基础评测集和评测脚本，并根据评测结果把默认拒答阈值调整为 `0.60`。当前 10 条基准样例中，知识库内问题可以正确命中来源，知识库外问题可以正确拒答。

页面也已从“整页长滚动”调整为“固定工作台”：左侧文档、中间聊天、右侧引用分别滚动，聊天输入区固定在问答面板底部。

## 最新验证结论

真实 DashScope Embedding 和 DeepSeek 流式问答已经接通。当前系统可以完成：

```text
文档重新入库 -> 生成向量 -> pgvector 检索 -> 引用来源 -> DeepSeek 流式回答
```

下一步重点从“链路能跑”转向“效果可解释、可调优、可评测”。

当前已完成第一步可解释化：SSE 返回 `retrieval_debug`，前端展示检索调试卡片，并优化回答 Markdown 渲染。

## 最新阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| 阶段 4：文档管理与异步入库 | 基本完成，待真实 Key 验证 | 上传、解析、混合分块、DashScope Embedding 适配器、pgvector `vector(1024)` 已完成 |
| 阶段 5：RAG 问答链路 | 进行中 | `/api/chat/stream` 已接入检索、拒答、DeepSeek 流式生成、引用保存；真实生成依赖 API Key |
| 阶段 6：RAG 设置与优化开关 | 进行中 | 管理员设置面板已接入，可保存检索、分块、生成参数 |
| 阶段 8：前端工作台打磨 | 进行中 | 上传、登录、真实 SSE 问答、引用来源展示已接入 |

## 下一步执行顺序

1. 用户在本机 `.env` 中填写 `DASHSCOPE_API_KEY`，不要在聊天中发送密钥。
2. 重启 backend，上传示例 Markdown 文档，验证 `documents.status=ready` 且 `document_chunks.embedding is not null`。
3. 用户在本机 `.env` 中填写 `DEEPSEEK_API_KEY`，重启 backend。
4. 在前端 `http://127.0.0.1:3004` 发送真实问题，验证流式回答、引用来源和聊天历史。
5. 对失败文档点击“重新入库”，验证补齐 Key 后无需重复上传即可完成向量化。
6. 补充检索调试信息：展示 Top-K 分数、命中文档、拒答原因，方便面试讲解 RAG 优化。
7. 将 Hybrid Search 和 Rerank 从“配置开关”升级为真实检索逻辑。

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
| 阶段 3：认证与配额 | 进行中 | 管理员登录、游客模式、游客 2 次问答限制、IP 日限额 |
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
| 游客限制 | 单游客 2 次问答，后端校验，附加 IP 日限额 |
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

1. 游客 2 次问答限制尚未实现。
2. 管理员上传文件已完成第一段：前端选择文件 -> 后端保存文件 -> 创建 documents 记录。
3. 文档解析、混合分块和后台入库任务已完成。
4. 下一步接入 DashScope Embedding，生成向量并写入 pgvector。

## 错误与风险记录

| 风险 | 当前处理 |
|---|---|
| 公开演示被刷 API | 游客 2 次限制 + IP 日限额 + 管理员上传限制 |
| 文档入库接口超时 | 异步入库 + 文档状态轮询 |
| RAG 幻觉 | 严格拒答 + 引用来源 + 相似度阈值 |
| 解析复杂文档失败 | 明确第一版边界，失败状态记录错误信息 |
| `.doc` 解析不稳定 | 第一版不支持，Roadmap 用 LibreOffice 转换 |
| Rerank/Hybrid 增加复杂度 | 做成可选开关，默认主链路可运行 |

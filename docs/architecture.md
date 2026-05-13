# Enterprise RAG Assistant 架构设计

## 1. 总体架构

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
DashScope text-embedding    DeepSeek
```

## 2. 后端模块结构

```text
backend/app/
├── api/              # API 路由层：接收前端请求
├── core/             # 配置、日志、安全、异常处理
├── db/               # 数据库连接、Alembic 迁移配置
├── models/           # SQLAlchemy 数据库模型
├── schemas/          # Pydantic 请求/响应模型
├── services/         # 业务服务：文档、聊天、设置、统计
├── rag/              # RAG 核心模块
│   ├── loaders/      # 文档解析
│   ├── splitters/    # 文档分块
│   ├── embeddings/   # DashScope Embedding 适配器
│   ├── retrievers/   # 向量检索、Hybrid、Rerank
│   ├── generators/   # DeepSeek 生成适配器
│   ├── prompts/      # Prompt 模板
│   └── pipeline.py   # RAG 主流程编排
└── main.py
```

## 3. 前端模块结构

```text
frontend/
├── app/              # Next.js App Router
├── components/       # 页面组件
├── lib/              # API 客户端、工具函数
├── types/            # TypeScript 类型
└── styles/           # 全局样式
```

前端使用 shadcn/ui + Tailwind CSS 构建企业 SaaS 工作台界面。

选择原因：

- shadcn/ui 组件源码可控，适合开源项目阅读和二次修改。
- Tailwind CSS 便于快速实现一致的间距、颜色和响应式布局。
- 相比重型后台框架，界面更现代、轻量，适合“云舟知识库助手”的产品展示。

前端服务端状态使用 TanStack Query 管理。

适用数据：

- 文档列表
- 统计卡片
- 应用设置
- 聊天历史
- 文档处理状态轮询

选择原因：

- 统一管理 loading、error、refetch 和缓存。
- 文档异步入库需要轮询状态，TanStack Query 支持良好。
- 第一版不引入复杂全局状态库，登录 token 和局部 UI 状态用轻量方式处理。

## 4. 依赖管理

### 4.1 后端

后端使用 `requirements.txt` + pip。

选择原因：

- 开源用户最容易理解。
- Docker 构建简单。
- README 中安装命令直观。
- 第一版不需要复杂包发布和 monorepo 管理。

### 4.2 前端

前端使用 npm。

选择原因：

- Next.js 默认支持好。
- 开源用户熟悉度最高。
- 与 Docker 构建流程简单匹配。

## 5. 数据库与 ORM

后端使用 SQLAlchemy 2.x + Pydantic。

分层方式：

- SQLAlchemy models：负责数据库表映射。
- Pydantic schemas：负责 API 请求和响应结构。
- Alembic：负责数据库迁移。

选择原因：

- SQLAlchemy 是 Python 后端最成熟的 ORM 之一。
- 与 Alembic 配合稳定。
- 模型层和接口层分离，适合复杂项目长期维护。
- 便于接入 pgvector 类型和自定义向量检索 SQL。

数据库访问第一版采用同步 SQLAlchemy。外部模型调用、SSE 流式输出等 I/O 等待明显的部分使用异步实现。

选择原因：

- 项目主要耗时来自 DeepSeek、DashScope 和文档处理，不是数据库查询。
- 同步 SQLAlchemy 更简单稳定，适合第一版和开源用户理解。
- SSE 流式输出仍然可以通过异步生成器实现良好体验。
- 后续如需高并发，可评估迁移到异步 SQLAlchemy 或拆分 worker。

## 6. 数据库迁移

使用 Alembic 管理数据库结构版本。

原因：

- 数据库表较多，后续会持续调整字段。
- 开源用户可以通过迁移脚本初始化数据库。
- 更符合正式后端工程实践。

## 7. 数据模型设计

第一版核心表：

| 表名 | 作用 |
|---|---|
| `knowledge_bases` | 知识库表，第一版只有默认知识库 |
| `documents` | 文档表，保存上传文件和入库状态 |
| `document_chunks` | 文档分块表，保存文本、元数据和 embedding 向量 |
| `conversations` | 会话表 |
| `messages` | 消息表，保存用户问题和助手回答 |
| `message_citations` | 引用来源结构化关联表 |
| `guest_usage` | 游客配额表 |
| `app_settings` | RAG 参数设置表 |
| `model_call_logs` | 模型调用记录表 |

所有核心业务表主键使用 UUID。

选择原因：

- 前后端分离场景下 ID 会暴露在 API 中，UUID 不容易泄露数据量。
- 后续扩展多知识库、多用户或异步 worker 时更安全。
- 数据迁移和合并时冲突概率低。

### 7.1 引用来源存储

引用来源采用“双存储”：

1. `messages.citations_json` 保存当次回答展示给用户的引用快照。
2. `message_citations` 保存 message 与 chunk 的结构化关联。

选择原因：

- JSON 快照保证历史消息稳定，即使后续文档被删除或索引重建，用户仍能看到当时的引用内容。
- 结构化关联便于后续统计 chunk 被引用次数、分析知识库热点和失败样本。

### 7.2 删除策略

文档删除采用“文档软删除 + chunks 物理删除”。

具体规则：

- `documents.deleted_at` 标记文档已删除，保留文档管理记录。
- 删除文档时物理删除对应 `document_chunks`，确保旧内容不会继续被检索。
- 第一版同时删除本地原始文件，避免演示环境磁盘持续膨胀。
- 历史消息中的 `citations_json` 保留当时引用快照，保证历史回答仍可追溯。

选择原因：

- 避免被删除文档继续进入 RAG 检索。
- 保留文档操作记录，方便审计和问题排查。
- 和引用来源快照设计配合，历史回答不会因文档删除而完全失去依据。

## 8. RAG 主链路

### 8.1 文档入库

```text
上传文档
-> 保存原始文件
-> 创建 documents 记录，状态 processing
-> BackgroundTasks 异步处理
-> 文档解析
-> 混合分块
-> DashScope Embedding
-> 写入 document_chunks + pgvector
-> 更新 documents 状态 ready
```

### 8.2 问答生成

```text
用户提问
-> 身份与配额校验
-> 读取或创建 conversation
-> 保存用户消息
-> 轻量意图识别：能力咨询直接回答
-> 最近对话 + 当前问题向量化
-> pgvector 检索
-> 可选 Hybrid Search
-> 可选 Rerank
-> 相似度阈值过滤
-> 低相关严格拒答
-> 拼接 Prompt
-> DeepSeek SSE 流式生成
-> 保存 messages 与引用来源
```

多轮对话处理：

- `conversations` 保存一次连续对话的元数据。
- `messages` 保存用户和助手消息。
- 用户明确追问时，后端才会把最近几轮消息拼入检索查询，帮助模型理解上下文指代。
- 如果当前问题是新话题，检索只使用当前问题，避免历史上下文把召回结果拉偏。
- 命中候选还要通过当前问题支持度校验；不支持当前问题时会严格拒答并返回空引用。
- 前端提供“开启新对话”和“历史对话”入口，可切换和加载历史消息。

### 8.3 意图识别快路径

对“你能做什么”“你有哪些功能”“怎么使用你”这类能力咨询，后端使用规则型轻量识别直接返回产品能力说明。

选择原因：

- 这类问题不需要查企业知识库，也不需要调用 DeepSeek。
- 跳过 Embedding、pgvector 检索和 LLM 生成，响应更快，公开演示成本更低。
- 避免把产品说明类问题误判为“知识库依据不足”而显得笨拙。

### 8.4 SSE 流式事件协议

`POST /api/chat/stream` 使用 SSE 多事件类型返回。

事件类型：

```text
event: status
data: {"message":"正在检索知识库..."}

event: answer_delta
data: {"content":"根据"}

event: citations
data: {"citations":[...]}

event: done
data: {"message_id":"..."}

event: error
data: {"message":"模型调用失败"}
```

前端处理方式：

- `status`：展示当前执行状态。
- `answer_delta`：追加 AI 回答内容。
- `citations`：更新右侧引用来源。
- `done`：结束 loading，并刷新聊天历史。
- `error`：展示错误提示。

选择原因：

- 比纯文本流更容易处理引用来源和错误状态。
- 便于后续加入检索阶段耗时、模型信息、Token 用量等事件。

### 8.5 引用全文预览

`GET /api/documents/{document_id}/preview` 返回解析后的文档全文，以及每个 chunk 在全文中的字符区间。前端点击引用标签时，根据引用中的 `document_id` 拉取全文，再用 `chunk_id` 找到命中区间，自动滚动并高亮。

选择原因：

- 用户不仅能看到本次检索片段，还能回到整篇文档中核对上下文。
- 引用快照和全文预览分离：历史回答稳定展示，当前文档仍可用于更完整的溯源阅读。
- 便于展示 RAG 的可追溯性和企业知识库审计价值。

## 9. 扩展点

- `rag/generators/`：替换 DeepSeek 为 Qwen/OpenAI/Claude。
- `rag/embeddings/`：替换 DashScope Embedding 为本地 bge-m3 或 OpenAI 兼容接口。
- `rag/retrievers/`：扩展 Elasticsearch/OpenSearch Hybrid Search。
- `rag/pipeline.py`：后续增加 LangChain 对照版。
- `services/document_service.py`：后续替换 BackgroundTasks 为 Celery + Redis worker。

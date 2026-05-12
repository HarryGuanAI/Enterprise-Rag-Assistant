# Enterprise RAG Assistant 调研与发现

## 立项发现

- 求职目标是 AI Agent 开发岗位，但第一个项目先聚焦企业知识库 RAG 助手。
- 项目必须是可部署、可展示、可开源的成品，而不是只在本地跑通的 Demo。
- 用户希望全程参与，重点理解技术选择、优化点和面试表达，不需要亲自写代码，但会看代码。
- 文档、代码结构、中文注释、README 和部署说明都需要足够完整，服务 GitHub 开源和面试展示。

## 技术取舍记录

### 为什么第一版先不用 LangChain

第一版自研轻量 RAG 链路，有助于讲清楚文档解析、分块、Embedding、向量入库、检索、Prompt 拼装和模型生成的底层过程。后续增加 LangChain 对照版，展示框架化能力。

### 为什么用 PostgreSQL + pgvector

比 FAISS/Chroma 更贴近企业真实项目。PostgreSQL 同时保存业务数据、聊天历史、文档状态和向量，Docker Compose 部署也可控。

### 为什么用 DeepSeek + DashScope

DeepSeek 负责答案生成，DashScope `text-embedding-v4` 负责文本向量化。生成模型和 Embedding 模型分离，符合真实项目中“按能力选型”的思路。

### 为什么不支持 `.doc`

`.docx` 是结构化 Office Open XML，可用 `python-docx` 稳定解析。`.doc` 是老式二进制格式，通常需要 LibreOffice 转换，会增加镜像体积和部署复杂度。第一版支持 `.docx`，`.doc` 放入 Roadmap。

### 为什么做异步入库

文档解析、分块和 Embedding 调用可能耗时。异步入库可以避免上传接口阻塞，并让前端展示 `processing/ready/failed` 状态，更接近真实企业项目。

### 为什么做严格拒答

企业知识库场景强调可信与可追溯。检索低相关时不让模型凭常识回答，而是直接拒答，减少幻觉并节省模型调用成本。

## 后续需补充调研

- DashScope Embedding 与 Rerank 最新 API 参数。
- DeepSeek 流式 API 返回格式、Token 用量字段和错误码。
- pgvector 在 PostgreSQL 中的向量距离计算与索引配置。
- FastAPI SSE 最佳实践。
- Docker Compose 中 pgvector 镜像选择。


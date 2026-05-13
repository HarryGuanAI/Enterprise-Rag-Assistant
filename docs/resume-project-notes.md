# 求职项目讲法：Enterprise RAG Assistant

> 这份文档用于个人求职准备，不作为开源 README 的公开主叙事。公开仓库首页重点展示项目能力、工程质量和可复现部署；面试时再结合本文讲自己的设计取舍。

## 1. 一句话介绍

我做了一个可部署的企业知识库 RAG 助手，支持多格式文档入库、pgvector 语义检索、Hybrid Search、轻量 Rerank、严格拒答、引用溯源、多轮对话和云服务器部署，重点解决企业制度问答中的可追溯、可评测和可上线问题。

## 2. 1 分钟讲法

这个项目是一个企业知识库 RAG 系统。前端用 Next.js，后端用 FastAPI，数据库用 PostgreSQL + pgvector。管理员可以上传 PDF、DOCX、Markdown、TXT，系统异步解析、分块、调用 DashScope `text-embedding-v4` 生成 1024 维稠密向量并入库。用户提问时，系统先做检索和严格拒答判断，依据不足就不调用 LLM；依据充分时调用 DeepSeek 流式回答，并返回引用来源。

我重点做了三类工程优化：第一是 Hybrid Search，把向量召回和中文关键词召回融合，解决制度名、金额、流程节点等纯向量不稳定的问题；第二是多轮 RAG 防污染，只有明显追问才带历史检索；第三是评测闭环，用 73 条 golden QA 验证检索命中、拒答准确和关键词覆盖。项目已经用 Docker Compose + Nginx 部署到云服务器。

## 3. 3 分钟讲法

项目的核心目标不是只做一个能聊天的页面，而是把 RAG 应用从文档入库到公网部署完整打通。

文档侧，系统支持 PDF、DOCX、Markdown、TXT。上传后进入异步处理流程：先解析文本，再按标题、段落和长度做混合分块，最后调用 DashScope Embedding 生成 1024 维稠密向量，写入 PostgreSQL 的 pgvector 字段。

检索侧，我没有只做单路向量召回。向量检索适合语义泛化，但企业制度里经常有专有名词、金额阈值、审批节点、制度编号，这些对关键词更敏感。所以我做了 Hybrid Search：一路是 pgvector cosine similarity，一路是中文关键词和 n-gram 召回，然后按 chunk 去重融合，再做轻量 Rerank。Rerank 不额外调用模型，主要基于向量分、关键词覆盖、标题章节命中和领域词覆盖。后来我还专门修复了“薪酬绩效/绩效薪酬”这种词序变化导致的误拒答问题。

生成侧，系统会先判断 Top1 相似度和命中片段是否足以支撑当前问题。如果不足，直接严格拒答，不调用 DeepSeek。这样既降低幻觉，也节省成本。能回答的问题会把检索片段拼入 Prompt，用 DeepSeek SSE 流式输出，并保存引用快照，前端能点击引用打开全文并高亮命中 chunk。

多轮对话侧，我做了追问识别。只有“这个呢”“继续说”“上一条呢”这类明显追问才把历史拼进检索 query；如果用户换了一个独立问题，就只按当前问题检索，避免上一轮内容污染召回。

工程侧，项目有游客限额、管理员登录、RAG 参数设置、检索调试面板、Docker Compose 部署、Nginx 反向代理和安全检查文档。评测侧有 73 条 golden QA，用检索命中率、拒答准确率、关键词覆盖和 Top1 分数来驱动优化。

## 4. 高频追问

### Embedding 是什么模型？维度是多少？

当前使用 DashScope `text-embedding-v4`，是稠密向量模型，固定输出 1024 维。数据库字段是 pgvector 的 `vector(1024)`，检索时使用 cosine distance，并换算为相似度分数。

### Hybrid Search 怎么做的？

不是直接接 Elasticsearch，而是在 PostgreSQL 内实现轻量混合检索。一路用 pgvector 做向量召回，另一路从中文问题中抽取关键词、短语和 n-gram，在文档标题、章节路径和 chunk 内容里匹配。两路候选按 chunk 去重后融合分数，再用轻量 Rerank 二次排序。

### 为什么不直接上模型 Rerank？

第一版优先保证低成本、可解释和容易部署。轻量 Rerank 已经能解决一批排序问题，而且右侧调试面板能解释每个 chunk 的向量分和关键词分。后续可以接 bge-reranker 或云厂商 rerank 模型作为升级版。

### 做 Query Rewrite 吗？

当前不做 LLM Query Rewrite，不额外调用大模型改写用户问题。系统做的是轻量规则处理：能力咨询识别、多轮追问判断、文本归一化、关键词抽取和当前问题支持度校验。这样成本低、链路更可控。

### “薪酬绩效”和“绩效薪酬”为什么曾经表现不同？

这是中文短 query 的词序鲁棒性问题。短问题信息量少，Embedding 分数和关键词短语匹配都会受词序影响。修复方式不是简单调低阈值，而是在 Hybrid Search 和支持度校验里加入领域词覆盖，让“薪酬”“绩效”“福利”等领域词组合能容忍顺序变化，同时仍保持严格拒答。

### 怎么控制幻觉？

三层控制：Prompt 要求只基于上下文回答；Top1 相似度不足或片段不支持当前问题时直接拒答；回答必须带引用来源，用户可以查看全文和命中 chunk。

### 怎么控制成本？

游客每日限额，IP 日兜底限额；低相关问题拒答时不调用 DeepSeek；能力咨询问题走本地快路径；上传和入库只允许管理员操作；API Key 只在后端环境变量中保存。

### 怎么证明优化有效？

项目有 73 条 golden QA，覆盖 HR、报销、信息安全、销售合同、客服 SLA、采购付款、产品 FAQ、入转离、绩效薪酬、商务接待、研发发布以及知识库外拒答问题。评测指标包括 retrieval hit rate、refusal accuracy、keyword coverage 和 avg top1 score。

## 5. 简历项目描述

```text
Enterprise RAG Assistant：企业知识库智能问答系统
- 基于 Next.js + FastAPI + PostgreSQL/pgvector 构建企业知识库 RAG 系统，支持多格式文档上传、异步解析、混合分块、向量入库、全文引用预览和 SSE 流式问答。
- 接入 DashScope text-embedding-v4 1024 维稠密向量与 DeepSeek Chat，实现 pgvector 语义检索、严格拒答、引用溯源、检索调试、多轮对话和手动停止输出。
- 实现 Hybrid Search 与轻量 Rerank，融合向量召回、中文关键词召回、召回排名、关键词覆盖和领域词顺序容错，提升制度类短问题与专有词问题的召回稳定性。
- 构建 73 条 golden QA 评测集，覆盖制度细则、金额阈值、审批链路、异常场景和知识库外拒答问题，用检索命中率、拒答准确率、关键词覆盖和 Top1 分数驱动 RAG 调优。
- 使用 Docker Compose + Nginx 部署到云服务器，设计游客限额、管理员登录、环境变量密钥管理、容器端口收敛和公开演示成本控制。
```

## 6. 近期重点提醒

- 开源 README 不写“求职”“面试”“演示项目”等字样，只展示技术能力和工程质量。
- GitHub 开源前继续检查 `.env`、上传文件、日志、截图和提交历史，避免泄露真实密钥。
- 开发过程中暴露过的 DashScope、DeepSeek Key 和服务器 root 密码，长期公开访问前应重新生成或修改并废弃旧凭据。
- 域名 `airagcloud.online` 已申请，DNS 计划指向 `117.72.45.27`，当前处于备案流程中；备案通过后再切换 HTTPS 域名访问。
- 下一步优先准备 README 截图/GIF、3-5 分钟讲解视频、域名 HTTPS 完成后的公开访问链接。

## 7. 给简历优化 AI 的提示词

```text
你现在扮演一名资深 AI Agent / RAG 开发岗位简历顾问，请帮我优化个人简历中的项目经历。

我的目标岗位：AI Agent 开发工程师 / RAG 应用开发工程师 / 大模型应用开发工程师。

项目名称：Enterprise RAG Assistant / 云舟知识库助手

项目定位：
这是一个可部署、可演示、可开源的企业知识库 RAG 助手。它不是简单调用聊天 API，而是完整覆盖文档上传、异步解析、分块、Embedding、向量入库、混合检索、严格拒答、引用溯源、多轮对话、评测和云服务器部署。

技术栈：
- Frontend：Next.js 14、React 18、Tailwind CSS、TanStack Query、lucide-react
- Backend：FastAPI、SQLAlchemy 2.x、Pydantic、Alembic
- Database：PostgreSQL + pgvector
- Embedding：DashScope text-embedding-v4，1024 维稠密向量
- LLM：DeepSeek deepseek-chat，SSE 流式回答
- Deployment：Docker Compose、Nginx、云服务器

核心能力：
- 支持 PDF、DOCX、Markdown、TXT 上传与异步入库
- 文档解析后进行混合分块，并写入 pgvector
- 使用 pgvector cosine similarity 做向量召回
- 实现 Hybrid Search：向量召回 + 中文关键词/短语/n-gram 召回 + 融合排序
- 实现轻量 Rerank：基于向量分、关键词覆盖、标题/章节命中和领域词覆盖二次排序
- 严格拒答：Top1 相似度不足或命中片段无法支撑当前问题时，不调用 LLM，返回无依据提示
- 引用溯源：回答带引用来源，可点击打开全文并高亮命中 chunk
- 多轮对话：保存会话和历史消息，支持继续追问
- 多轮防污染：只有明显追问才带历史进入检索；独立新问题只按当前问题检索
- 能力咨询意图识别：“你能做什么”等问题走本地快路径，跳过 Embedding、检索和 LLM
- 查询处理：当前不做 LLM Query Rewrite，但会做文本归一化、关键词抽取、追问识别和当前问题支持度校验
- 词序鲁棒性：修复“薪酬绩效/绩效薪酬”这类中文短问题词序变化导致的误拒答
- 游客限额、管理员登录、RAG 参数设置、检索调试面板、手动停止输出
- 使用 11 份虚构企业制度样例文档覆盖 HR、报销、信息安全、销售合同、客服 SLA、采购付款、产品 FAQ、入转离、绩效薪酬、商务接待、研发发布
- 建立 73 条 golden QA 评测集，覆盖制度细则、金额阈值、审批链路、异常场景和知识库外拒答
- 最新 Hybrid + Rerank 评测结果：retrieval_hit_rate=1.00，refusal_accuracy=1.00，keyword_coverage_avg=1.00，avg_top1_score=0.7584
- 已部署到云服务器，使用 Docker Compose 编排 PostgreSQL、FastAPI、Next.js，Nginx 反向代理；域名 airagcloud.online 已申请，备案中

请基于以上信息帮我完成：
1. 生成一版适合放在中文技术简历里的项目经历，要求 4-6 条 bullet，每条体现技术动作 + 结果/价值，避免空泛。
2. 生成一版更适合 Boss 直聘/拉勾/猎聘项目描述的短版，控制在 150-250 字。
3. 生成一版面试时 60 秒项目介绍，语言自然，不要像背稿。
4. 生成一版“技术亮点”模块，突出 RAG 检索、Hybrid Search、严格拒答、评测闭环、部署安全。
5. 帮我把措辞优化得像真实工程项目，不要夸大，不要写“精通”，不要写无法证明的数据。
6. 注意：开源 README 里不要出现“求职”“面试”“演示项目”这些词；简历里可以突出“已开源/可在线访问/可部署”。
```

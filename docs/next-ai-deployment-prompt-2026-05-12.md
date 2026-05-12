# 下一个 AI 窗口系统提示词：部署上线阶段

请把下面整段发给下一个 AI 窗口，用于继续 Enterprise RAG Assistant / 云舟知识库助手的部署上线工作。

```text
你现在接手我的 AI Agent / RAG 开发求职项目：Enterprise RAG Assistant / 云舟知识库助手。

项目目录：
D:\03_Work\04_NewWorks\我的AI新工作\enterprise-rag-assistant

我的目标：
我要用这个项目应聘 AI Agent / RAG 开发岗位。项目必须是一个可部署、可演示、可开源的企业知识库 RAG 助手。代码要优雅、易读，必要位置有中文注释，文档要完整。接下来重点不是继续堆功能，而是准备部署上线、开源检查、演示材料和求职讲法。

接手后请优先阅读：
1. README.md
2. docs/deployment.md
3. docs/security-and-open-source-checklist.md
4. docs/demo-script.md
5. docs/architecture.md
6. docs/interview-retrospective-2026-05-12.md
7. progress.md
8. task_plan.md

当前已完成能力：
- Next.js + FastAPI + PostgreSQL + pgvector + Docker Compose 基础项目
- 管理员登录：admin / 本地 .env 中的 ADMIN_PASSWORD
- 游客模式，默认每日 15 次问答限制，IP 日兜底默认 100 次
- 游客顶部提示：页面仅用于学习展示，如想体验更多功能，请联系管理员登录
- 管理员联系方式弹窗：
  - 中文：关海龙，+86 15031597985
  - English：Harry Guan, +86 15031597985
- PDF、DOCX、Markdown、TXT 上传与异步入库
- DashScope text-embedding-v4 Embedding
- DeepSeek deepseek-chat 流式回答
- pgvector 检索、严格拒答、引用来源、检索调试信息
- Hybrid Search：向量召回 + 中文关键词召回融合
- 轻量 Rerank：基于向量分、关键词覆盖和内容相关性二次排序
- 回答生成中支持手动停止，前端用 AbortController 中断 SSE/fetch 流
- 多轮对话：开启新对话、历史对话列表、加载历史消息、继续追问
- 多轮拒答修复：只有明显追问才把历史带入检索；独立新问题只按当前问题检索；命中片段不能支撑当前问题时严格拒答并返回空引用
- 能力咨询意图识别：例如“你能做什么”直接返回产品能力说明，跳过 Embedding、检索和 DeepSeek
- 引用全文预览：点击引用标签打开整篇文档，并滚动/高亮到命中 chunk
- sample_docs 虚构企业样例知识库，覆盖 HR、报销、休假、IT、产品 FAQ、客服工单、销售合同、数据安全
- 37 条 RAG 评测集和评测脚本
- 当前默认 min_similarity=0.60
- 纯向量模式和 Hybrid + Rerank 模式评测中，检索命中率、拒答准确率、关键词覆盖均为 1.00
- README、部署说明、面试演示脚本、开源前安全检查、求职复盘文档已补齐

当前本地服务：
- 前端：http://127.0.0.1:3004
- 后端：http://127.0.0.1:8000
- 后端健康检查：http://127.0.0.1:8000/health

重要安全提醒：
- .env 里有真实 API Key，已被 .gitignore 忽略，不要读取后在回答里展示完整 Key，不要提交。
- 用户曾在对话中暴露过真实 API Key。正式开源或公网部署前，必须提醒用户重新生成 DashScope 和 DeepSeek Key，并废弃旧 Key。
- 不要提交 .env、storage/uploads、真实业务文档、截图里的密钥、日志里的密钥。

最近验证：
- python -m compileall backend\app 通过
- npm.cmd run build 通过
- docker compose up -d --build backend 通过
- git diff --check 通过，仅有 Windows LF/CRLF 提示
- /health 返回 200
- 3004 页面返回 200，CSS 返回 200
- “你能做什么”走意图识别快路径，不触发 retrieval_debug，不生成问题向量
- 同一 conversation 内问无关问题“年会奖品是什么？”会严格拒答，will_call_llm=false，citations=[]
- stats 按 guest_id 计算游客剩余次数；新游客 15/15，用满时 0/15

下一步工作重点：准备部署上线
1. 检查 Git 状态，确认没有 .env、真实上传文件、缓存、日志进入 Git。
2. 根据 docs/security-and-open-source-checklist.md 做开源前安全检查。
3. 提醒用户轮换并废弃开发阶段暴露过的 DashScope / DeepSeek Key。
4. 准备云服务器部署方案：
   - Docker Compose
   - 域名与 HTTPS
   - BACKEND_CORS_ORIGINS
   - NEXT_PUBLIC_API_BASE_URL
   - 数据库密码、JWT_SECRET_KEY、ADMIN_PASSWORD
5. 上线后导入 sample_docs，并运行 37 条 golden QA 评测。
6. 准备 README 截图/GIF、演示视频脚本和简历项目描述。

操作习惯：
- 不要读出或展示 .env 中的 Key。
- 改代码前先检查现有实现和 Git 状态。
- 每次改完要运行必要验证。
- 如果跑 npm build 后 3004 页面变成裸 HTML，通常是 Next.js .next 缓存问题：停止 3004、清理 frontend/.next、重新 npm.cmd run dev -- -p 3004。
- 回答要用中文，既讲清楚做了什么，也讲清楚面试怎么讲。
```

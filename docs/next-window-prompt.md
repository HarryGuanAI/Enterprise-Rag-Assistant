# 给下一个窗口的提示词

请从下面这段开始，把它完整发给新的 Codex 窗口：

```text
你现在接手我的 AI Agent 开发求职项目：Enterprise RAG Assistant / 云舟知识库助手。

项目目录：
D:\03_Work\04_NewWorks\我的AI新工作\enterprise-rag-assistant

我的目标：
我要用这个项目应聘 AI Agent / RAG 开发岗位。项目必须是一个可部署、可演示、可开源的企业知识库 RAG 助手。代码要优雅、易读，必要位置有中文注释，文档要完整。请继续像上一轮一样带着我做，我不会亲自写代码，但我要理解每一步为什么这样做、用了什么技术、怎么优化、面试怎么讲。

你接手后请先阅读：
1. docs/handoff-2026-05-12.md
2. task_plan.md
3. progress.md
4. README.md
5. docs/architecture.md

当前已完成：
- Next.js + FastAPI + PostgreSQL + pgvector + Docker Compose 基础项目
- 管理员登录：admin / 本地 .env 中的 ADMIN_PASSWORD
- 游客模式，每日 2 次问答限制
- PDF、DOCX、Markdown、TXT 上传与异步入库
- DashScope text-embedding-v4 Embedding
- DeepSeek deepseek-chat 流式回答
- pgvector 检索、严格拒答、引用来源、检索调试信息
- 前端固定工作台布局，输入框固定在聊天面板底部
- 基础 RAG 评测集和评测脚本
- 当前默认 min_similarity=0.60，10 条评测样例检索命中率和拒答准确率都是 1.00

当前本地服务：
- 前端：http://127.0.0.1:3004
- 后端：http://127.0.0.1:8000

重要安全提醒：
- .env 里有真实 API Key，已被 .gitignore 忽略，不要读取后在回答里展示完整 Key，不要提交。
- 后续开源或部署前提醒我重新生成并废弃曾经暴露过的 Key。

我希望下一步继续开发：
优先做“检索优化能力展示”，也就是把设置面板里的 Hybrid Search 和 Rerank 从占位开关变成真实能力。请先检查代码状态，再给我简短说明下一步会做什么，然后直接实现。每次实现后请运行必要验证，并用中文解释这个优化在 RAG 面试里怎么讲。
```

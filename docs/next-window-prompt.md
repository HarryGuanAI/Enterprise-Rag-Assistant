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
6. docs/demo-script.md
7. docs/security-and-open-source-checklist.md

当前已完成：
- Next.js + FastAPI + PostgreSQL + pgvector + Docker Compose 基础项目
- 管理员登录：admin / 本地 .env 中的 ADMIN_PASSWORD
- 游客模式，每日 2 次问答限制
- PDF、DOCX、Markdown、TXT 上传与异步入库
- DashScope text-embedding-v4 Embedding
- DeepSeek deepseek-chat 流式回答
- pgvector 检索、严格拒答、引用来源、检索调试信息
- Hybrid Search：向量召回 + 中文关键词召回融合
- 轻量 Rerank：基于向量分、关键词覆盖和内容相关性二次排序
- 回答生成中支持手动停止，前端用 AbortController 中断 SSE/fetch 流
- 前端页面结构已基本确定：左上角 logo + 名称、顶部轻量统计条、左侧窄文档栏、中间主问答区、右侧窄引用栏
- 示例问题只在首次对话前展示，开始对话后自动隐藏
- 回答后显示引用标签，点击后从右侧打开文档预览抽屉，并定位到引用段落
- sample_docs 虚构企业样例知识库，覆盖 HR、报销、休假、IT、产品 FAQ、客服工单、销售合同、数据安全
- 37 条 RAG 评测集和评测脚本
- 当前默认 min_similarity=0.60
- 纯向量模式和 Hybrid + Rerank 模式评测中，检索命中率、拒答准确率、关键词覆盖均为 1.00
- README、部署说明、面试演示脚本、开源前安全检查文档已补齐

当前本地服务：
- 前端：http://127.0.0.1:3004
- 后端：http://127.0.0.1:8000

重要安全提醒：
- .env 里有真实 API Key，已被 .gitignore 忽略，不要读取后在回答里展示完整 Key，不要提交。
- 后续开源或部署前提醒我重新生成并废弃曾经暴露过的 Key。

最近验证：
- npm.cmd run build 通过
- git diff --check 通过，仅有 Windows LF/CRLF 提示
- 3004 页面返回 200
- 浏览器验证 1296x576 视口无横向/纵向溢出
- 停止输出交互通过
- 引用标签和文档预览抽屉交互通过

我希望下一步继续开发：
优先做“真正的全文文档预览”。当前引用预览抽屉展示的是本次检索命中的 chunk，已经能演示引用可追溯；下一步希望新增后端接口返回文档全文和 chunk 位置信息，让右侧预览窗口能展示整篇文档，并自动滚动/高亮到命中的引用段落。请先检查代码状态，再给我简短说明下一步会做什么，然后直接实现。每次实现后请运行必要验证，并用中文解释这个优化在 RAG 面试里怎么讲。
```

# 面试演示脚本

这份脚本用于 5-8 分钟项目演示。目标是让面试官快速看到：文档入库、RAG 检索、严格拒答、引用来源、Hybrid/Rerank、评测闭环。

## 1. 开场介绍

一句话：

> 这是一个企业知识库 RAG 助手。管理员上传内部文档后，系统自动解析、分块、向量化入库；员工提问时，系统先检索相关片段，再基于引用来源调用 DeepSeek 流式回答；如果知识库依据不足，会严格拒答。

## 2. 打开页面

访问：

```text
http://127.0.0.1:3004
```

公网演示环境也可以访问：

```text
http://117.72.45.27
```

讲解页面结构：

- 左侧：知识库文档和入库状态
- 中间：企业知识库问答
- 右侧：引用来源和检索调试
- 顶部：文档数、分块数、今日问答、拒答次数、模型调用

## 3. 管理员登录

点击“管理员登录”：

- 用户名：`admin`
- 密码：对应环境 `.env` 中的 `ADMIN_PASSWORD`

讲解点：

> 前端不保存任何 API Key。上传、入库、问答、模型调用都经过后端，管理员密码和模型 Key 都在环境变量里。

## 4. 导入或上传样例文档

如果数据库为空，可以批量导入：

```bash
docker compose run --rm \
  -v "./sample_docs:/app/sample_docs" \
  backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

Windows PowerShell：

```powershell
docker compose run --rm -v "${PWD}/sample_docs:/app/sample_docs" backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

讲解点：

> 样例知识库覆盖 HR、IT、产品 FAQ、客服工单、销售合同、数据安全等企业常见场景，比只放一两段玩具文本更接近真实业务。

## 5. 演示一次命中回答

可以先点击：

```text
你能做什么？
```

讲解点：

> 这是能力咨询意图，系统不会走 RAG 检索，也不会调用大模型，而是用轻量规则直接返回产品能力说明。这样能避免“你能做什么”被严格拒答，看起来更像真实助手。

点击示例问题：

```text
出差报销需要提交哪些材料？
```

观察：

- 中间出现流式回答
- 右侧出现引用来源
- 点击引用标签后，右侧抽屉展示整篇文档，并自动滚动/高亮到命中的 chunk
- 检索调试显示 TopK、阈值、Top1、检索模式

讲解点：

> 回答不是模型凭空生成，而是先检索报销制度中的差旅报销片段，再把片段作为上下文传给 DeepSeek。引用标签可以回到整篇文档里的命中位置，方便用户确认答案依据。

## 6. 演示安全类问题

点击示例问题：

```text
API Key 可以写进 README 或工单评论吗？
```

讲解点：

> 这个问题会命中数据安全规范，能展示项目对真实工程安全问题的覆盖，也能顺便强调开源前必须轮换 Key。

## 7. 演示严格拒答

点击示例问题：

```text
公司年会抽奖一等奖是什么？
```

讲解点：

> 这是知识库外问题。Top1 相似度低于阈值时系统直接拒答，不调用 DeepSeek。这样既减少幻觉，也节省 API 成本。

## 8. 演示多轮对话

继续追问：

```text
那 P1 呢？
```

观察：

- 问答区右上角有“开启新对话”
- 左侧“知识库文档”旁可以切换到“历史对话”
- 历史对话卡片可重新加载之前的消息

讲解点：

> 真实知识库助手不是一次性问答。后端会保存 conversation 和 messages，并把最近几轮对话放入检索查询和 Prompt，让模型能理解“那、这个、上一条”这类指代。

## 9. 演示 Hybrid Search 和 Rerank

管理员打开“RAG 设置”：

- 开启 Hybrid
- 开启 Rerank
- 保存设置

再次提问：

```text
折扣超过 35% 的报价需要谁审批？
```

观察右侧调试信息：

- 检索模式变为 `hybrid+rerank`
- 能看到向量候选、关键词候选、最终入选数量
- 引用卡片显示向量分和关键词分

讲解点：

> 向量召回负责语义泛化，关键词召回补足专有名词、数字、制度条款，Rerank 负责把更相关片段排到前面。

## 10. 演示评测闭环

运行：

```bash
docker compose run --rm \
  -v "./evals:/app/evals" \
  -v "./backend/app/evals:/app/app/evals" \
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

Windows PowerShell：

```powershell
docker compose run --rm -v "${PWD}/evals:/app/evals" -v "${PWD}/backend/app/evals:/app/app/evals" backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

讲解点：

> 我用 37 条 golden QA 验证检索命中率、拒答准确率和关键词覆盖。RAG 优化不是靠主观感觉，而是用评测集驱动阈值和检索策略调整。

## 11. 收尾总结

可以这样收尾：

> 这个项目展示了一个 RAG 应用从文档处理、向量入库、检索优化、严格拒答、引用溯源到评测闭环的完整工程链路。后续可以把当前 RAG 能力封装成企业 Agent 的工具，比如报销助手、入职助手或 IT 工单助手。

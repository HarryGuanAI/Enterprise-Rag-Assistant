# 运维维护手册

本文档记录云舟知识库助手上线后的日常维护命令和安全注意事项。不要在本文档中写入真实 API Key、服务器密码或 `.env` 内容。

## 1. 当前部署状态

当前公网演示环境：

- 访问地址：http://117.72.45.27
- 健康检查：http://117.72.45.27/health
- API 统计：http://117.72.45.27/api/stats
- 服务器部署目录：`/opt/enterprise-rag-assistant`
- 部署方式：Docker Compose + Nginx 反向代理
- 系统：Ubuntu 24.04 LTS
- 规格：2 核 CPU、4GB 内存、60GB SSD、5Mbps 带宽

当前上线验证结果：

| 检查项 | 结果 |
|---|---|
| 前端首页 | 200，页面包含“云舟知识库助手” |
| 后端 `/health` | 200 |
| `/api/stats` | 200 |
| 样例文档 | 11 份，覆盖 Markdown、TXT、DOCX、PDF |
| Ready 文档 | 本地纯净验证 11 份；线上以 `/api/stats` 为准 |
| 分块数 | 本地纯净验证 57；线上以 `/api/stats` 为准 |
| 评测集 | 73 条 |
| Hybrid + Rerank 评测 | 本地纯净验证：检索命中率 1.00，拒答准确率 1.00，关键词覆盖 1.00 |

## 2. 常用维护命令

进入部署目录：

```bash
cd /opt/enterprise-rag-assistant
```

查看容器状态：

```bash
docker compose ps
```

查看后端日志：

```bash
docker compose logs --tail=120 backend
```

查看前端日志：

```bash
docker compose logs --tail=120 frontend
```

重启服务：

```bash
docker compose restart
```

重新构建并启动：

```bash
docker compose up -d --build
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1/api/stats
```

## 3. 样例数据和评测

导入样例知识库：

```bash
docker compose run --rm \
  -v "$(pwd)/sample_docs:/app/sample_docs" \
  backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

运行 Hybrid + Rerank 评测：

```bash
docker compose run --rm \
  -v "$(pwd)/evals:/app/evals" \
  -v "$(pwd)/backend/app/evals:/app/app/evals" \
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --enable-hybrid-search --enable-rerank
```

当前上线评测结果：

```text
total: 73
retrieval_mode: hybrid+rerank
retrieval_hit_rate: 1.00
refusal_accuracy: 1.00
keyword_coverage_avg: 1.00
avg_top1_score: 0.7615
```

最新本地回归记录（2026-05-13）：

```text
total: 73
retrieval_mode: hybrid+rerank
retrieval_hit_rate: 1.00
refusal_accuracy: 1.00
keyword_coverage_avg: 1.00
avg_top1_score: 0.7584
```

## 3.1 检索链路维护说明

当前 Embedding 使用 DashScope `text-embedding-v4`，属于稠密向量模型，后端固定请求 `1024` 维输出，数据库字段为 `vector(1024)`。向量检索使用 pgvector cosine distance，业务分数按 `1 - distance` 计算。

Hybrid Search 的实现方式：

- 向量召回：使用用户问题向量在 pgvector 中检索语义相近 chunks。
- 关键词召回：从问题中提取英文/数字 token、中文连续短语和 2/3/4-gram，在文件名、章节路径和 chunk 内容中匹配。
- 融合排序：按 chunk id 去重，保留向量分与关键词分，并结合两路召回排名做融合排序。
- 分数控制：向量和关键词都命中的片段会加权提升；仅关键词命中的片段设置保守上限，避免弱匹配绕过严格拒答。
- 轻量 Rerank：基于向量分、关键词覆盖、标题/章节命中、内容相关性和领域词覆盖做二次排序，不额外调用 rerank 模型。

Query 处理策略：

- 当前系统不做 LLM Query Rewrite，不会为了改写 query 额外调用大模型。
- 能力咨询类问题直接走本地回答，跳过 Embedding、检索和 DeepSeek。
- 只有明显追问才带入最近历史作为检索上下文；独立新问题只按当前问题检索。
- 输入会做空白、大小写和常见标点归一化，并抽取关键词供 Hybrid Search 使用。
- 检索后会做当前问题支持度校验；命中片段无法支撑当前问题时严格拒答。
- 针对“薪酬绩效/绩效薪酬”一类中文领域词顺序变化，系统增加了领域词覆盖容错，避免短问题因词序变化被误拒答。

排查检索异常时优先看右侧 retrieval_debug：

- `Top1` 是否低于阈值 `min_similarity`。
- `候选：向量 / 关键词 / 入选` 是否说明关键词召回没有命中。
- 命中来源是否来自目标制度文档。
- `will_call_llm` 是否为 `false`，如果为 false 说明严格拒答拦截生效。
- 对同义问法或词序变化问题，优先用 golden QA 增补一条用例，再调整召回或 rerank 规则。

## 4. 环境变量维护

真实配置文件位于服务器：

```text
/opt/enterprise-rag-assistant/.env
```

必须保密的字段：

- `DASHSCOPE_API_KEY`
- `DEEPSEEK_API_KEY`
- `ADMIN_PASSWORD`
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`

修改 `.env` 后重启：

```bash
docker compose down
docker compose up -d --no-build
```

如果修改了 `POSTGRES_PASSWORD`，而数据库已经初始化过，不能只改 `.env`。如果数据库里没有需要保留的数据，可以重新初始化：

```bash
docker compose down -v
docker compose up -d --no-build
```

如果已有生产数据，不要直接 `down -v`，应先做数据库备份并在 PostgreSQL 内修改用户密码。

## 5. 端口和安全

公网入口只应开放：

- `22`：SSH
- `80`：HTTP
- `443`：HTTPS，配置域名证书后使用

容器端口只绑定本机：

- `127.0.0.1:3000`
- `127.0.0.1:8000`
- `127.0.0.1:5432`

服务器额外启用了 Docker `DOCKER-USER` 规则，阻断公网直连：

- `3000`
- `8000`
- `5432`

检查命令：

```bash
ufw status verbose
iptables -S DOCKER-USER
```

重要安全提醒：

- 当前开发过程中服务器 root 密码曾经在聊天里暴露过，应在云控制台修改 root 密码。
- 后续建议改用 SSH Key 登录，并关闭 root 密码登录。
- API Key 曾经在开发过程中暴露过，公网长期演示前应重新生成并废弃旧 Key。
- 不要把 `.env`、`storage/uploads/`、真实业务文档或日志密钥提交到 Git。

## 5.1 域名与 HTTPS 状态

当前计划使用域名：

```text
airagcloud.online
www.airagcloud.online
```

域名解析目标：

```text
117.72.45.27
```

当前状态：

- 域名已在阿里云申请。
- DNS A 记录计划指向京东云服务器公网 IP `117.72.45.27`。
- 京东云备案仍在处理中；备案完成前，域名访问可能被云厂商拦截或解析表现不稳定。
- 服务器 Nginx 已提前加入：
  ```text
  server_name airagcloud.online www.airagcloud.online 117.72.45.27;
  ```
- 当前可稳定访问地址仍以 `http://117.72.45.27` 为准。

备案通过后的待办：

1. 确认 DNS 公共解析结果：
   ```bash
   nslookup airagcloud.online 223.5.5.5
   nslookup www.airagcloud.online 223.5.5.5
   ```
   两个结果都应返回 `117.72.45.27`。
2. 确认 HTTP 域名访问：
   ```bash
   curl -I http://airagcloud.online
   curl -I http://www.airagcloud.online
   ```
3. 配置 HTTPS 证书，建议使用 Let's Encrypt + Certbot。
4. 将服务器 `.env` 中公网访问相关配置切换为域名，例如：
   ```text
   BACKEND_CORS_ORIGINS=https://airagcloud.online,https://www.airagcloud.online
   NEXT_PUBLIC_API_BASE_URL=https://airagcloud.online
   ```
5. 重新构建前端并重启服务：
   ```bash
   cd /opt/enterprise-rag-assistant
   docker compose up -d --build
   ```
6. 验证：
   ```bash
   curl -I https://airagcloud.online
   curl -s https://airagcloud.online/api/stats
   ```

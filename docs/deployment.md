# 部署说明

本文档说明如何在本地或一台普通云服务器上运行 Enterprise RAG Assistant。

## 1. 准备环境

需要安装：

- Docker
- Docker Compose
- 可用的 DashScope API Key
- 可用的 DeepSeek API Key

项目默认使用 Docker Compose 启动 PostgreSQL、后端和前端。

## 2. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

至少修改以下字段：

```text
DASHSCOPE_API_KEY=你的 DashScope Key
DEEPSEEK_API_KEY=你的 DeepSeek Key
ADMIN_PASSWORD=一个强密码
JWT_SECRET_KEY=一串随机长密钥
POSTGRES_PASSWORD=一个数据库密码
```

公开部署时还应修改：

```text
BACKEND_CORS_ORIGINS=https://你的前端域名
NEXT_PUBLIC_API_BASE_URL=https://你的后端域名
```

## 3. 启动服务

```bash
docker compose up -d --build
```

启动后访问：

- 前端：http://localhost:3000
- 后端健康检查：http://localhost:8000/health
- 后端 API 文档：http://localhost:8000/docs

## 4. 导入样例知识库

项目提供 `sample_docs/` 作为演示资料。可以在管理员界面逐个上传，也可以批量导入：

```bash
docker compose run --rm \
  -v "./sample_docs:/app/sample_docs" \
  backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

Windows PowerShell：

```powershell
docker compose run --rm -v "${PWD}/sample_docs:/app/sample_docs" backend python -m app.evals.ingest_sample_docs --sample-dir /app/sample_docs
```

导入过程会调用 DashScope Embedding。导入完成后，前端文档列表会显示样例文档和分块数量。

## 5. 运行评测

纯向量基线：

```bash
docker compose run --rm \
  -v "./evals:/app/evals" \
  -v "./backend/app/evals:/app/app/evals" \
  backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --disable-hybrid-search --disable-rerank
```

Windows PowerShell：

```powershell
docker compose run --rm -v "${PWD}/evals:/app/evals" -v "${PWD}/backend/app/evals:/app/app/evals" backend python -m app.evals.run_eval --dataset /app/evals/golden_qa.jsonl --disable-hybrid-search --disable-rerank
```

Hybrid Search + Rerank：

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

## 6. 常见问题

### 文档入库失败，提示未配置 DASHSCOPE_API_KEY

确认 `.env` 中已经填写 `DASHSCOPE_API_KEY`，然后重启后端：

```bash
docker compose up -d --build backend
```

如果文档已经上传但失败，可以在前端文档列表点击“重新入库”。

### 问答失败，提示未配置 DEEPSEEK_API_KEY

确认 `.env` 中已经填写 `DEEPSEEK_API_KEY`，并重启后端。

### 前端无法访问后端

检查：

- 后端是否在 `http://localhost:8000/health` 返回 ok
- `NEXT_PUBLIC_API_BASE_URL` 是否指向正确后端地址
- `BACKEND_CORS_ORIGINS` 是否包含前端地址

### 公开部署前要做什么

- 更换 `ADMIN_PASSWORD`
- 更换 `JWT_SECRET_KEY`
- 更换数据库密码
- 重新生成 API Key，废弃曾经暴露过的旧 Key
- 确认 `.env`、`storage/uploads/`、真实业务文档没有进入 Git

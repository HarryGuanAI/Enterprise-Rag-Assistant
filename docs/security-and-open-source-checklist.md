# 开源前安全检查清单

正式公开 GitHub 仓库或部署公网演示前，请逐项检查。

## 1. API Key

- 不要提交 `.env`。
- 不要在 README、文档、截图、issue、commit message 中出现真实 API Key。
- 如果真实 Key 曾经在对话、截图或日志中暴露过，应在平台重新生成 Key，并废弃旧 Key。
- 检查代码中是否只有 `your_deepseek_api_key`、`your_dashscope_api_key` 这类占位值。

## 2. 环境变量

必须修改：

- `ADMIN_PASSWORD`
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DASHSCOPE_API_KEY`
- `DEEPSEEK_API_KEY`

公开部署时还要检查：

- `BACKEND_CORS_ORIGINS`
- `NEXT_PUBLIC_API_BASE_URL`

## 3. Git 忽略

确认以下内容没有进入 Git：

- `.env`
- `.env.local`
- `storage/uploads/`
- `node_modules/`
- `.next/`
- Python cache
- 数据库 volume
- 真实业务文档

可以运行：

```bash
git status --short
git ls-files | grep -E "(\.env|storage/uploads|node_modules|\.next)"
```

Windows PowerShell 可用：

```powershell
git status --short
git ls-files | Select-String -Pattern "\.env|storage/uploads|node_modules|\.next"
```

## 4. 样例数据

- `sample_docs/` 只能放虚构资料。
- 不要上传真实员工信息、客户合同、客户名称、财务数据、AccessKey、日志截图。
- 评测集 `evals/golden_qa.jsonl` 中的问题也应使用虚构场景。

## 5. 公开演示成本控制

- 游客问答次数限制应开启。
- 管理员上传权限应受登录保护。
- 低相关问题应严格拒答，避免无依据调用 LLM。
- 可以定期查看 `model_call_logs` 统计模型调用次数。

## 6. 面试说明

如果面试官问到安全问题，可以这样说：

> 这个项目把 API Key、管理员密码、JWT 密钥都放在环境变量里，前端不会接触真实 Key。公开演示时我用游客限额控制调用成本，用严格拒答避免无依据调用 LLM。开源前会重新生成并废弃开发阶段暴露过的 Key，确保仓库历史里没有真实密钥。

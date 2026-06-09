# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| v0.1.x  | :white_check_mark: |
| < 0.1   | :x:                |

我们目前处于早期阶段,仅最新 minor 版本接收安全更新。

## Reporting a Vulnerability

**请不要在 GitHub Issue 公开报告安全漏洞**。

请通过以下任一渠道私下报告:

1. **GitHub Security Advisories** (推荐):
   访问 [https://github.com/<your-org>/opendocx/security/advisories/new](https://github.com/<your-org>/opendocx/security/advisories/new)
   提交 Private Security Advisory。

2. **Email**:
   发邮件到 `security [at] example [dot] com` （发布前替换为真实安全邮箱）,
   标题包含 `[OpenDocX Security]` 前缀。

3. **Encrypted 通信**:
   我们支持 PGP 加密邮件,公钥将在收到初次联系后回复。

## 报告内容请包含

- **漏洞类型** (XSS / SQL 注入 / 认证绕过 / LLM 注入 / ...)
- **影响范围** (哪些 endpoint / 哪些组件 / 哪些数据)
- **复现步骤** (尽量详细, 包含 curl/代码片段)
- **影响评估** (严重性,潜在后果)
- **可能的修复方向** (如果你有)
- **是否已公开** (是否在 issue/discuss/CVE 公开讨论过)

## Response Timeline

我们承诺:

- **48 小时内**确认收到报告
- **7 天内**评估严重性并给出初步判断
- **30 天内**发布修复(高/严重级别优先)
- 修复发布前**不公开**漏洞细节(给用户升级窗口期)
- 修复发布后,在 [CHANGELOG](CHANGELOG.md) 致谢(除非你要求匿名)

## Security Best Practices for Self-Hosting

如果你在自己的服务器部署 OpenDocX, 强烈建议:

1. **LLM_API_KEY 保护**:
   - 永远不要 commit `.env` 到 git(.gitignore 已配)
   - 部署时用 secrets manager (Vault / AWS Secrets Manager / 1Password)
   - rotate key 周期 90 天

2. **数据库**:
   - PostgreSQL 不暴露公网,只内网/127.0.0.1
   - 启用 SSL 连接
   - 定期备份(`pg_dump`)

3. **JWT 密钥**:
   - `.env` 中 `SECRET_KEY` 用 `openssl rand -base64 64` 生成
   - 不要用默认的 `dev-secret-key-change-me`

4. **CORS**:
   - 生产环境设具体域名,**不要**用 `allow_origins=["*"]`
   - 后端 `app/main.py` 中检查 CORS 配置

5. **Rate Limit**:
   - 默认 300 req/min/IP(R11 修复后),生产可调更低
   - LLM 端点单独限流,防滥用烧 token

6. **静态站发布**:
   - `data/builds/` 是生成产物,可对外公开
   - 但**别把 SQLite/PostgreSQL data 目录公开**

7. **依赖更新**:
   - 定期 `pip list --outdated` / `npm outdated`
   - 订阅 GitHub Security Alerts

## Known Security Considerations (2026-06)

- **LLM Prompt Injection**: 用户文本可注入 prompt 攻击 (R11 后端 _build_qa 已做选区约束)
- **Markdown XSS**: `mistune.escape=True` + bleach 已转义内联 HTML (R10)
- **JWT 过期**: 默认 7 天,可在 `.env` 调 `JWT_EXPIRE_MINUTES`
- **审计日志**: 所有 admin mutation 已写 `audit_logs` 表 (P1-W3-A1)

---

## Local Data Safety

OpenDocX public releases contain source code and demo seed data only. They do not include local runtime data.

Never commit these files or directories:

- `.env` or `.env.local`
- PostgreSQL or SQLite database files
- `data/builds/`, `data/uploads/`, `data/docs/`, `data/projects/`
- local LLM keys, JWT secrets, logs, or generated static sites

For a clean first run:

```bash
git clone https://github.com/your-org/opendocx.git
cd opendocx
cp .env.example .env
# edit .env for your database, Redis, and optional LLM provider
bash scripts/seed_demo.sh
```

`bash scripts/seed_demo.sh` creates a demo admin account (`admin@opendocx.local` / `admin123`), one demo project, and sample documents.

## API Key Rotation

If an LLM API key may have leaked, rotate it at the provider, update `.env`, restart the backend, and verify an AI editor action.

## Acknowledgements

暂无(项目初期)。

---

## License

本文档采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),可自由分享和修改。

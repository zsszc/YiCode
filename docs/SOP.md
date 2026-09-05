# YiCode 运维 SOP

> 适用范围：忆码 YiCode（FastAPI + React + SQLite，部署于阿里云 ECS）。
> 原则：**密钥永远不进 git**；**轮换优先于清理**；**先备份再操作**。

---

## 1. Secrets 管理规范

### 1.1 敏感信息清单及存放位置

| 敏感项 | 唯一合法存放位置 | 禁止出现的位置 |
|---|---|---|
| Kimi API Key | 本地 `backend/.env`；服务器 systemd 服务配置 | git 仓库、前端代码、聊天截图 |
| JWT `SECRET_KEY` | 本地 `backend/.env`；服务器 systemd 配置 | 同上 |
| 阿里云 SSH 私钥 | 本地项目根 `aliyun_key.pem`（已被 .gitignore 覆盖） | git 仓库（含历史！） |
| 服务器 IP / 域名 | 本地部署脚本、GitHub Secrets | 公开文档、README |
| 数据库 | 服务器 `/opt/yicode/data/yicode.db` | git 仓库 |

### 1.2 红线

- `.env`、`*.pem`、`*.pem.pub`、`*.db` 一律在 `.gitignore` 中；新增敏感文件类型时先加 `.gitignore` 再创建文件。
- 提交前自查：`git status` 中不得出现上述文件；`git diff --cached` 中不得出现 `sk-` 开头的 key、IP、`PRIVATE KEY` 字样。
- 从 git 删除 ≠ 清除泄露。历史中出现过的凭据**一律视为已泄露，立即轮换**，然后用 `git filter-repo` 清洗历史并强推。

### 1.3 凭据轮换步骤（以 API Key 为例）

1. 在对应平台作废旧 key、签发新 key；
2. 更新本地 `backend/.env`；
3. 更新服务器：`ssh` 登录后修改 systemd 服务的 `Environment=`（或环境文件），`systemctl daemon-reload && systemctl restart yicode-backend`；
4. 验证：调一次真实接口确认可用；
5. 确认新 key 生效后再宣布完成。

---

## 2. 部署 Checklist（手动部署）

> 已配置 GitHub Actions CD 后，优先用 CD；以下为兜底手动流程。

- [ ] 本地后端测试通过：`cd backend && python -m pytest tests -q`
- [ ] 本地前端构建通过：`cd frontend && npm run build`
- [ ] 确认无敏感文件混入：`git status` 干净，无 `.env` / `*.pem`
- [ ] 打包上传后端 `app/` 与前端 `dist/` 到服务器 `/opt/yicode/`
- [ ] `systemctl restart yicode-backend` 并 `systemctl status` 确认 active
- [ ] nginx 无需重启（仅静态文件变更时 `nginx -s reload` 都不用）
- [ ] 外网验证：打开站点，注册/登录、题目列表、判题、AI Tutor 各点一遍

---

## 3. 备份与恢复

### 3.1 自动备份（已启用）

- 频率：每日 03:17（cron）
- 内容：SQLite 数据库 `/opt/yicode/data/yicode.db`
- 位置：`/opt/yicode/backups/daily/`，保留最近 14 份，自动清理更旧的

### 3.2 手动备份

```bash
ssh -i aliyun_key.pem root@<服务器IP> \
  "sqlite3 /opt/yicode/data/yicode.db '.backup /opt/yicode/backups/manual-$(date +%F-%H%M).db'"
```

### 3.3 恢复步骤

1. 停服务：`systemctl stop yicode-backend`
2. 备份当前（可能损坏的）库：`cp data/yicode.db data/yicode.db.broken`
3. 用备份覆盖：`cp /opt/yicode/backups/daily/<选定日期>.db /opt/yicode/data/yicode.db`
4. 起服务并验证：`systemctl start yicode-backend`，登录站点抽查题目与提交记录
5. 记录事件到 `docs/`（时间、原因、恢复到哪个备份点）

---

## 4. 安全例行检查（建议每月一次）

- [ ] 服务器：`journalctl -u yicode-backend --since "-7d"` 看有无异常报错
- [ ] 服务器：`last` / `/var/log/secure`（或 `auth.log`）看有无异常登录
- [ ] 仓库：GitHub → Settings → Security → secret scanning 无告警
- [ ] 依赖：`pip list --outdated`、`npm outdated` 评估是否需要升级
- [ ] 备份抽查：随机挑一份备份文件，确认可解出数据

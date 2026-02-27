# Eliza-Py 部署指南（免费服务器版）

本文档介绍如何在免费云服务器上部署 Eliza-Py 项目，并在实验结束后获取数据库文件。

## 适用场景

- ✅ 免费云服务器（如 ClawCloudRun 等）
- ✅ 只能通过 Docker 镜像部署
- ✅ 无 SSH/文件管理器访问权限
- ✅ 服务器提供域名映射（如 `https://xxx.clawcloudrun.com`）
- ✅ 容器可能随时被重启/删除

## 数据持久化方案

### ⚠️ 重要：先确认你的云服务商存储类型

| 存储类型 | 特点 | 数据安全性 |
|---------|------|-----------|
| **临时存储** | 容器删除后数据丢失 | ⚠️ 需要额外备份 |
| **持久化卷** | 容器删除后数据保留 | ✅ 安全 |

**如何确认**：查看云服务商文档中关于"存储卷"、"持久化"的说明。

### 方案 A：使用持久化卷（推荐）

如果你的云服务商支持持久化卷：

1. 在控制台设置挂载点：`/app/data`
2. 容器重启/删除重建后，数据自动保留

**本项目的 Dockerfile 已配置好自动备份机制**：
- 每次启动时自动创建数据库备份到 `/app/data/backups/`
- 保留最近 3 个备份，避免占用过多空间

### 方案 B：临时存储 + 定期下载（保底方案）

如果存储是临时的，建议：

1. **实验期间定期下载数据库**（每天或每次重要操作后）
   ```bash
   curl -H "X-API-Key: 你的密钥" \
        https://your-server.com/admin/export-data \
        -o turing-$(date +%Y%m%d).db
   ```

2. **使用外部备份**（需要配置环境变量）：
   ```bash
   # S3 兼容存储（如 Cloudflare R2）
   BACKUP_S3_BUCKET=my-bucket
   BACKUP_S3_KEY=backups/turing.db
   S3_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com
   AWS_ACCESS_KEY_ID=xxx
   AWS_SECRET_ACCESS_KEY=xxx
   ```

## 部署步骤

### 1. 构建 Docker 镜像

在本地项目根目录执行：

```bash
docker build -t eliza-py .
```

### 2. 推送镜像到仓库

根据你的云服务商要求推送镜像，例如：

```bash
# 标记镜像
docker tag eliza-py registry.example.com/your-namespace/eliza-py:latest

# 登录仓库
docker login registry.example.com

# 推送
docker push registry.example.com/your-namespace/eliza-py:latest
```

### 3. 配置环境变量（可选但推荐）

为了保护数据导出端点，建议设置管理密钥：

```bash
# 生成一个随机密钥（示例）
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 输出示例：xK9mN2pL5qR8sT1vW3xY6zA4bC7dE0fG
```

在云服务商控制台设置环境变量：
- `TURING_ADMIN_API_KEY` = `你的随机密钥`

### 4. 部署到云服务商

在云服务商控制台：
1. 选择 Docker 镜像部署
2. 填写镜像地址
3. 设置环境变量（如果有）
4. 设置挂载点：`/app/data`（确保数据持久化）
5. 设置端口映射：`8000` → 分配的域名

## 获取数据库（实验结束后）

### 方式一：使用 curl 下载（推荐）

```bash
# 如果设置了 TURING_ADMIN_API_KEY
curl -H "X-API-Key: 你的密钥" \
     https://hosktqwopusa.ap-northeast-1.clawcloudrun.com/admin/export-data \
     -o turing.db

# 如果没有设置密钥（不推荐，有安全风险）
curl https://hosktqwopusa.ap-northeast-1.clawcloudrun.com/admin/export-data \
     -o turing.db
```

### 方式二：使用浏览器下载

直接访问：
```
https://hosktqwopusa.ap-northeast-1.clawcloudrun.com/admin/export-data
```

如果设置了密钥，需要在浏览器开发者工具中添加请求头：
1. 按 F12 打开开发者工具
2. 切换到 Network 标签
3. 访问上述 URL
4. 右键请求 → Edit and Resend
5. 添加请求头：`X-API-Key: 你的密钥`
6. 发送请求

### 方式三：使用 PowerShell（Windows）

```powershell
# 设置密钥
$apiKey = "你的密钥"
$url = "https://hosktqwopusa.ap-northeast-1.clawcloudrun.com/admin/export-data"

# 下载
Invoke-RestMethod -Uri $url -Headers @{"X-API-Key" = $apiKey} -OutFile "turing.db"
```

## API 端点说明

| 端点 | 说明 | 认证 |
|------|------|------|
| `/health` | 健康检查 | 无需 |
| `/admin/export-data` | 下载数据库文件 | 可选（通过 `TURING_ADMIN_API_KEY` 保护） |
| `/admin/list-backups` | 列出所有备份文件 | 可选（通过 `TURING_ADMIN_API_KEY` 保护） |

### 下载数据库

```bash
# 下载主数据库
curl -H "X-API-Key: 你的密钥" \
     https://your-server.com/admin/export-data \
     -o turing.db

# 下载特定备份
curl -H "X-API-Key: 你的密钥" \
     "https://your-server.com/admin/export-data?file=turing_backup_20260227_120000.db" \
     -o backup.db

# 列出所有备份
curl -H "X-API-Key: 你的密钥" \
     https://your-server.com/admin/list-backups
```

## 安全建议

1. **生产环境必须设置 `TURING_ADMIN_API_KEY`**
   - 避免数据库被公开下载
   - 密钥长度至少 32 字符

2. **实验结束后及时关闭服务器**
   - 避免资源浪费
   - 避免数据泄露

3. **备份数据库**
   - 下载后立即本地备份
   - 可导入 SQLite 浏览器查看：`sqlite3 turing.db`

## 故障排查

### 401 Unauthorized
- 原因：设置了密钥但未提供或密钥错误
- 解决：检查 `X-API-Key` 请求头是否正确

### 404 Not Found
- 原因：数据库文件不存在
- 解决：检查 `/app/data` 挂载是否正确

### 下载的文件为空
- 原因：数据库尚未创建或挂载失败
- 解决：检查服务器日志，确认 `/app/data/turing.db` 存在

### 容器重启后数据丢失
- 原因：存储是临时的，未配置持久化卷
- 解决：
  1. 确认云服务商是否支持持久化存储
  2. 如果不支持，定期下载数据库备份（见方案 B）

### 备份目录在哪里？
- 备份位置：`/app/data/backups/`
- 可通过导出端点下载任意备份：
  ```bash
  # 下载特定备份（需要知道文件名）
  curl -H "X-API-Key: 你的密钥" \
       https://your-server.com/admin/export-data?file=turing_backup_20260227_120000.db \
       -o turing.db
  ```

## 本地查看数据库

下载后可使用以下工具查看：

```bash
# 命令行
sqlite3 turing.db ".tables"
sqlite3 turing.db "SELECT * FROM users LIMIT 10;"

# GUI 工具
# - DB Browser for SQLite (跨平台)
# - SQLiteStudio (跨平台)
# - DBeaver (跨平台)
```

## 示例完整流程

```bash
# 1. 本地构建镜像
docker build -t eliza-py .

# 2. 推送到云服务商仓库
docker tag eliza-py registry.clawcloudrun.com/myuser/eliza-py:latest
docker push registry.clawcloudrun.com/myuser/eliza-py:latest

# 3. 在云控制台部署，设置：
#    - 镜像：registry.clawcloudrun.com/myuser/eliza-py:latest
#    - 环境变量：TURING_ADMIN_API_KEY=my-secret-key-12345
#    - 挂载点：/app/data  ← 重要！
#    - 端口：8000

# 4. 实验期间定期备份（推荐每天执行）
curl -H "X-API-Key: my-secret-key-12345" \
     https://hosktqwopusa.ap-northeast-1.clawcloudrun.com/admin/export-data \
     -o turing-$(date +%Y%m%d).db

# 5. 实验结束后下载最终数据库
curl -H "X-API-Key: my-secret-key-12345" \
     https://hosktqwopusa.ap-northeast-1.clawcloudrun.com/admin/export-data \
     -o turing-final.db

# 6. 查看有哪些备份可用
curl -H "X-API-Key: my-secret-key-12345" \
     https://hosktqwopusa.ap-northeast-1.clawcloudrun.com/admin/list-backups

# 7. 验证下载
sqlite3 turing-final.db ".tables"
```

---

祝你部署顺利！如有问题，请查看项目 README 或提交 Issue。

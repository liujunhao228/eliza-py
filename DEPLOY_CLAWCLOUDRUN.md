# ClawCloudRun 部署指南

## 快速步骤

### 1. 构建并推送镜像

```bash
# 构建
docker build -t eliza-py .

# 标记（替换为你的镜像仓库）
docker tag eliza-py ccr.ccl.net/eliza-py:latest

# 推送
docker push ccr.ccl.net/eliza-py:latest
```

### 2. ClawCloudRun 控制台配置

| 配置项 | 值 |
|--------|-----|
| **镜像地址** | `ccr.ccl.net/eliza-py:latest` |
| **容器端口** | `3001` ⚠️ 必须是 3001 |
| **环境变量** | `PORT=3001` |
| **存储卷** | `/app/data` (推荐) |

### 3. 环境变量（推荐设置）

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `PORT` | `3001` | **必填**，容器监听端口 |
| `TURING_ADMIN_API_KEY` | 随机字符串 | 数据导出密钥 |
| `CONFIG_TURING_AUTH_SECRET_KEY` | 随机字符串 | JWT 密钥 |
| `DEBUG` | `false` | 生产环境关闭调试 |
| `CONFIG_TURING_FRONTEND_URL` | (可选) | 前端 URL，不设置则自动使用请求域名 ✅ |

生成密钥：
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. 部署后访问

```
https://你的域名.ap-northeast-1.clawcloudrun.com
```

---

## 为什么是 3001 端口？

ClawCloudRun 的端口映射：

```
用户访问 (443/HTTPS)
    │
    ▼
ClawCloudRun 负载均衡
    │
    ▼
转发到容器端口 3001
    │
    ▼
FastAPI 应用 (通过 PORT 环境变量监听 3001)
```

**本项目已支持 `PORT` 环境变量**，自动适配云平台要求。

---

## 🎉 分享链接自动适配动态域名

**问题**：ClawCloud Run 部署后分配随机域名，分享链接如何生成？

**解决方案**：项目已支持自动从 HTTP 请求中获取域名，无需手动配置！

```
用户访问：https://abc123.ap-northeast-1.clawcloudrun.com
                │
                ▼
创建分享时自动使用：https://abc123.ap-northeast-1.clawcloudrun.com/share/xxx
```

### 工作原理

```python
# 优先级：
# 1. 环境变量 CONFIG_TURING_FRONTEND_URL（如果设置）
# 2. 从请求中动态获取（自动适配 ClawCloud Run）
# 3. 配置文件默认值 (http://localhost:5173)
```

### 可选：固定域名

如果你后续绑定了自定义域名，可以设置环境变量：

```bash
CONFIG_TURING_FRONTEND_URL=https://your-custom-domain.com
```

---

## 获取数据库

### 方法一：curl 下载
```bash
curl -H "X-API-Key: 你的密钥" \
     https://你的域名/admin/export-data \
     -o turing.db
```

### 方法二：浏览器下载
访问 `https://你的域名/admin/export-data`

---

## 故障排查

### 容器启动失败
```bash
# 查看日志
kubectl logs <pod-name>
```

### 常见错误

**错误：容器启动后立刻退出**
- 检查 `PORT` 环境变量是否正确设置
- 检查数据库目录权限：`/app/data`

**错误：502 Bad Gateway**
- 容器未正确监听 3001 端口
- 检查日志中的应用启动信息

**错误：数据库丢失**
- 确认已配置持久化存储卷
- 检查挂载点：`/app/data`

---

## 完整示例

### docker-compose.yml（本地测试）
```yaml
version: '3'
services:
  eliza-py:
    image: eliza-py:latest
    ports:
      - "3001:3001"
    environment:
      - PORT=3001
      - TURING_ADMIN_API_KEY=my-secret-key
    volumes:
      - ./data:/app/data
```

运行：
```bash
docker-compose up -d
```

访问：http://localhost:3001

# GitHub Actions Docker 发布指南

本文档说明如何使用 GitHub Actions 自动构建和发布 Docker 镜像到 GitHub Container Registry (GHCR)。

## 功能特性

- ✅ 推送到 GitHub Container Registry (GHCR)
- ✅ 支持多平台构建（linux/amd64, linux/arm64）
- ✅ 智能标签管理（版本、分支、SHA）
- ✅ 构建缓存加速
- ✅ 构建 provenance 证明

## 配置步骤

### 1. 启用 GitHub Packages（仅需一次）

如果是私有仓库，需要启用 GitHub Packages：

1. 进入仓库 **Settings → General**
2. 确保 **Features** 中 **Packages** 已启用

### 2. 配置权限

工作流已使用 `GITHUB_TOKEN` 自动认证，无需额外配置 Secrets。

确保仓库权限设置：
- 进入 **Settings → Actions → General**
- 确认 **Workflow permissions** 设置为 **Read and write permissions**

### 3. 触发构建

工作流会在以下情况自动触发：

| 事件 | 标签示例 | 说明 |
|------|---------|------|
| Push 到 main/master | `latest`, `sha-abc123` | 自动构建 latest 版本 |
| 创建 Pull Request | `pr-123` | 构建 PR 测试镜像（不推送） |
| 创建版本标签 | `v1.0.0`, `1.0`, `1` | 构建发布版本 |
| Push 到其他分支 | `feature-xyz` | 构建分支测试镜像 |

## 镜像标签说明

| 标签 | 说明 |
|------|------|
| `latest` | 最新稳定版（main/master 分支） |
| `v1.0.0` | 完整版本号 |
| `1.0` | 主版本。次版本 |
| `1` | 主版本号 |
| `sha-abc123f` | Git commit SHA |
| `feature-branch` | 分支名称 |
| `pr-123` | Pull Request 编号 |

## 使用镜像

### 拉取镜像

```bash
# 拉取最新版
docker pull ghcr.io/your-username/eliza-py:latest

# 拉取特定版本
docker pull ghcr.io/your-username/eliza-py:v1.0.0
```

### 运行容器

```bash
# 基本运行
docker run -p 8000:8000 -v ./data:/app/data ghcr.io/your-username/eliza-py:latest

# 使用环境变量
docker run -p 8000:8000 \
  -v ./data:/app/data \
  -e CONFIG_TURING_SERVER_PORT=8000 \
  -e CONFIG_TURING_AUTH_SECRET_KEY=your-secret-key \
  ghcr.io/your-username/eliza-py:latest
```

### 认证拉取（私有仓库）

如果镜像是私有的，需要先认证：

```bash
# GitHub Personal Access Token（需要 read:packages 权限）
echo $GHCR_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

## 查看已发布的镜像

1. 进入 GitHub 仓库
2. 点击 **Packages** 标签
3. 选择 `eliza-py` 镜像
4. 查看所有版本

## 自定义构建

编辑 `.github/workflows/docker-publish.yml`：

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    file: ./Dockerfile
    platforms: linux/amd64,linux/arm64  # 修改平台
    push: ${{ github.event_name != 'pull_request' }}
    tags: ${{ steps.meta.outputs.tags }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## 故障排查

### 构建失败

1. 检查 Actions 日志查看详细错误
2. 本地测试构建：`docker build -t eliza-py .`

### 推送失败 - 权限不足

1. 检查 **Settings → Actions → General → Workflow permissions**
2. 确保设置为 **Read and write permissions**
3. 确认 **Allow GitHub Actions to create and approve pull requests** 已启用

### 拉取镜像认证失败

```bash
# 创建 Personal Access Token
# GitHub → Settings → Developer settings → Personal access tokens
# 权限：read:packages

# 认证
echo $GHCR_TOKEN | docker login ghcr.io -u your-username --password-stdin
```

## 安全建议

1. **私有镜像**：生产环境建议使用私有仓库
2. **Token 管理**：定期轮换 Personal Access Token
3. **漏洞扫描**：集成容器安全扫描工具
4. **最小权限**：Token 只授予必要权限

## 相关文档

- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Buildx 文档](https://docs.docker.com/buildx/working-with-buildx/)

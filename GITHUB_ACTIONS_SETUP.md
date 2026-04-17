# GitHub Actions 部署指南 - 123Bot

本文档提供了完整的GitHub Actions配置方案，用于将Docker镜像构建并发布到GitHub Container Registry（GHCR）。

## 📋 项目信息

- **项目名称**: 123盘秒传Telegram机器人
- **构建环境**: Ubuntu Latest
- **Python版本**: 3.12
- **镜像仓库**: GitHub Container Registry (GHCR)

---

## 🚀 行动路线

### 第一步：准备GitHub仓库

1. 确保项目已推送到GitHub
2. 验证仓库为`组织/仓库`格式（e.g., `myorg/123bot`）
3. 在GitHub上进入仓库Settings → Actions → General
   - 确保"Actions permissions"设置为"Allow all actions"

### 第二步：设置仓库权限

1. 进入仓库Settings → Actions → General
2. 向下滚动到"Workflow permissions"部分
3. 选择 **"Read and write permissions"**
4. 勾选 **"Allow GitHub Actions to create and approve pull requests"** (可选)
5. 点击保存

### 第三步：部署工作流文件

1. 在本地项目根目录创建目录结构：
   ```bash
   mkdir -p .github/workflows
   ```

2. 将 `build-and-push.yml` 文件放入 `.github/workflows/` 目录

3. 提交并推送到GitHub：
   ```bash
   git add .github/workflows/build-and-push.yml
   git commit -m "ci: Add GitHub Actions workflow for Docker image build and push"
   git push
   ```

### 第四步：测试工作流

1. 进入GitHub仓库 → **Actions** 选项卡
2. 在左侧选择 **"Build and Push Docker Image"** workflow
3. 点击 **"Run workflow"** 按钮
4. 输入版本号（例如：`1.0.0`）
5. 点击 **"Run workflow"** 执行

### 第五步：验证镜像推送

工作流完成后验证：

1. 进入仓库 → **Packages** 部分
2. 应该能看到新推送的Docker镜像
3. 或在命令行验证：
   ```bash
   docker pull ghcr.io/your-org/123bot:latest
   ```

---

## 🔧 工作流功能说明

### 触发条件

| 触发方式 | 说明 |
|--------|------|
| **workflow_dispatch** | 手动触发，可输入自定义版本号 |
| **Push to main/master** | 主分支推送时自动构建 |
| **Tag推送** (v*) | 创建版本标签时自动构建并标记 |

### 构建标签策略

自动生成以下标签：

```
ghcr.io/your-org/123bot:latest           # 主分支最新版本
ghcr.io/your-org/123bot:1.0.0            # 手动指定的版本
ghcr.io/your-org/123bot:main-<sha>       # Git短SHA标记
```

### 权限配置

```yaml
permissions:
  contents: read      # 读取仓库内容
  packages: write     # 写入GHCR包权限
```

---

## 💾 Dockerfile检查清单

- [x] 基础镜像：Python 3.12-slim
- [x] 系统依赖已安装
- [x] Python依赖安装完成
- [x] 应用代码已复制
- [x] 环境变量配置完成
- [x] 健康检查已配置
- [x] 入口点已设置

---

## 🐳 在本地测试构建

在推送前可在本地测试：

```bash
# 构建镜像
docker build -t 123bot:test .

# 运行测试
docker run -d --name 123bot-test \
  -e P123_ACCOUNT_ID="test_id" \
  -e P123_PASSWORD="test_pwd" \
  -e P123_PARENT_ID="0" \
  123bot:test

# 查看日志
docker logs 123bot-test

# 清理
docker stop 123bot-test
docker rm 123bot-test
```

---

## 📦 使用推送的镜像

### 从GHCR拉取镜像

```bash
# 需要GitHub Token进行身份验证
docker login ghcr.io -u your-username -p your-github-token

# 拉取镜像
docker pull ghcr.io/your-org/123bot:latest
```

### 更新Docker Compose配置

编辑 `docker-compose.yml`：

```yaml
services:
  p123-bot:
    image: ghcr.io/your-org/123bot:latest
    # ... 其他配置
```

然后运行：

```bash
docker-compose pull
docker-compose up -d
```

---

## 🔐 安全建议

1. **GitHub Token**: 工作流自动使用 `secrets.GITHUB_TOKEN`，无需手动配置
2. **镜像隐私**: GHCR镜像继承仓库的可见性设置
   - 私有仓库 → 私有镜像
   - 公开仓库 → 公开镜像
3. **版本管理**: 推荐使用语义化版本 (e.g., `1.0.0`, `1.0.1`)

---

## 🐛 常见问题

### Q: 权限不足错误
**A**: 确保在仓库Settings中启用了"Read and write permissions"

### Q: 镜像无法推送
**A**: 检查GitHub Actions日志，通常是权限问题或Token过期

### Q: 本地构建成功但在CI中失败
**A**: 通常是环境或依赖版本差异，检查：
- Python版本
- 系统依赖安装
- requirements.txt内容

### Q: 如何设置为组织级别秘密？
**A**: 
1. 进入组织Settings → Secrets and variables → Actions
2. 添加组织级别秘密
3. 工作流可直接使用

---

## 📚 扩展建议

### 相关工作流配置

可根据需要添加：

1. **自动化测试** (.github/workflows/test.yml)
2. **代码质量检查** (SonarQube, CodeFactor)
3. **安全扫描** (Trivy, Dependabot)
4. **发布Release** (自动创建GitHub Release)

示例：
```yaml
# 添加测试
- name: Run tests
  run: python -m pytest tests/

# 添加代码扫描
- name: Scan image with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.event.inputs.version }}
```

---

## 📞 支持

遇到问题？检查：
- GitHub Actions日志（Actions标签底部）
- 官方文档：https://docs.github.com/en/actions
- Docker文档：https://docs.docker.com/


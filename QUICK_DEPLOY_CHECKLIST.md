# GitHub Actions 快速部署清单

## ✅ 组织成员部署步骤

### 1️⃣ 前置检查
- [ ] 仓库已推送到GitHub组织账户
- [ ] 有仓库的管理员权限
- [ ] 已安装最新版本的git

### 2️⃣ 激活Actions权限
```
仓库 → Settings → Actions → General
  ☐ Actions permissions: Allow all actions
  ☐ Workflow permissions: Read and write permissions
  ☐ 允许创建Pull requests (可选)
  → 点击Save
```

### 3️⃣ 部署工作流
```bash
mkdir -p .github/workflows
# .github/workflows/build-and-push.yml 已创建
git add .github/workflows/
git commit -m "ci: Add Docker build and push workflow"
git push origin main
```

### 4️⃣ 验证部署
- [ ] 进入GitHub仓库 → Actions标签
- [ ] 应看到"Build and Push Docker Image"工作流
- [ ] 工作流状态为"Ready"

### 5️⃣ 首次测试运行
```
Actions → Build and Push Docker Image
  → Run workflow ▼
    Input: version = 1.0.0
    → Run workflow [绿色按钮]
```

### 6️⃣ 验证结果
- [ ] 工作流完成（绿色✓）
- [ ] 仓库 → Packages 能看到镜像
- [ ] 镜像标签：
  - `latest`
  - `1.0.0`

---

## 📦 镜像使用方式

### 拉取镜像
```bash
docker login ghcr.io -u <username> -p <github-token>
docker pull ghcr.io/<org>/123bot:1.0.0
```

### 使用在docker-compose中
```yaml
services:
  p123-bot:
    image: ghcr.io/<org>/123bot:latest
    # ...
```

### 部署到服务器
```bash
# 在服务器上
docker login ghcr.io
docker pull ghcr.io/<org>/123bot:latest
docker-compose up -d
```

---

## 🔑 文件位置

| 文件 | 位置 | 用途 |
|------|------|------|
| 工作流 | `.github/workflows/build-and-push.yml` | CI/CD配置 |
| Dockerfile | `./Dockerfile` | Docker镜像定义 |
| 本指南 | `GITHUB_ACTIONS_SETUP.md` | 详细文档 |

---

## 🎯 自动触发条件

| 条件 | 动作 |
|------|------|
| 推送到main/master | 自动构建 |
| 创建tag (v*) | 自动构建+标记版本 |
| 手动workflow_dispatch | 构建+自定义版本 |

---

## 🚨 常见错误

| 错误 | 解决方案 |
|------|--------|
| Permission denied | 检查Actions权限设置 |
| Push failed | 确保有写入packages权限 |
| 镜像不可见 | 检查仓库可见性 |

---

## 📞 获取GitHub Token

仅在本地使用时需要：
1. GitHub.com → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. 权限勾选：`write:packages`, `read:packages`, `delete:packages`
4. 保存Token

---

## ⏭️ 后续扩展

- [ ] 添加单元测试workflow
- [ ] 添加代码扫描
- [ ] 添加自动发布Release
- [ ] 配置组织级别秘密


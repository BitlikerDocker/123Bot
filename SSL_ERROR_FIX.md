# Docker容器SSL错误排查指南

## 🔴 错误原因

```
[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
httpx.ConnectError
```

**根本原因**：Docker容器内缺少CA证书，无法验证HTTPS连接

---

## ✅ 解决步骤

### 第1步：更新Dockerfile

已添加 `ca-certificates` 包到系统依赖安装中：

```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

### 第2步：重新构建镜像

```bash
# 方式1：本地构建
docker build -t 123bot:latest .
docker-compose down
docker-compose up -d

# 方式2：使用GitHub Actions
git add Dockerfile
git commit -m "fix: add ca-certificates to resolve SSL error"
git push origin main  # 或手动trigger workflow
```

### 第3步：验证容器运行

```bash
# 查看日志
docker logs -f p123-bot

# 进入容器检查CA证书
docker exec p123-bot ls -la /etc/ssl/certs/ca-certificates.crt
```

---

## 📋 补充检查清单

如果仍然出现SSL错误，尝试以下步骤：

### ✓ 检查网络连接
```bash
# 进入容器
docker exec -it p123-bot bash

# 测试DNS解析
nslookup api.123pan.com

# 测试HTTPS连接
python -c "import urllib.request; urllib.request.urlopen('https://www.google.com')"
```

### ✓ 更新CA证书
```bash
# 在Dockerfile中添加
RUN apt-get update && \
    apt-get install -y ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

### ✓ 配置代理（如需要）
在docker-compose中添加：
```yaml
environment:
  - HTTP_PROXY=${HTTP_PROXY}
  - HTTPS_PROXY=${HTTPS_PROXY}
  - NO_PROXY=${NO_PROXY}
```

---

## 🛠️ P123Client相关配置

如果问题仍未解决，可在 `p123_client.py` 中禁用SSL验证：

```python
# p123_client.py - 不推荐，仅作为最后手段

import httpx

# 创建客户端时禁用SSL验证
client = httpx.Client(verify=False)  # ⚠️ 不安全，仅用于测试
```

或使用环境变量：
```bash
# docker-compose.yaml
environment:
  - PYTHONHTTPSVERIFY=0  # ⚠️ 不推荐生产使用
```

---

## 🔍 验证修复

修改后执行以下步骤验证：

1. **重新构建镜像**
   ```bash
   docker build -t 123bot:latest .
   ```

2. **运行容器**
   ```bash
   docker-compose up -d
   ```

3. **检查日志**（应该能看到成功登录的日志）
   ```bash
   docker logs -f p123-bot | head -50
   ```

4. **验证容器状态**
   ```bash
   docker ps  # 容器应该保持运行状态
   ```

---

## 📊 常见SSL错误及解决方案

| 错误类型 | 原因 | 解决方案 |
|--------|------|--------|
| UNEXPECTED_EOF | 缺少CA证书 | 安装 ca-certificates ✅ |
| CERTIFICATE_VERIFY_FAILED | 证书不信任 | 更新 ca-certificates |
| CONNECTION_REFUSED | 网络不通 | 检查网络/防火墙 |
| TIMEOUT | 连接超时 | 增加超时配置/检查DNS |

---

## 🚀 最佳实践

1. **生产环境**：始终使用CA证书验证，不要禁用SSL
2. **更新镜像**：定期更新基础镜像和CA证书
3. **监控日志**：保留详细的连接日志便于排查
4. **DNS配置**：确保容器内DNS配置正确

---

## 📞 如仍有问题

1. 检查容器内 `/etc/ssl/certs/ca-certificates.crt` 文件是否存在
2. 运行 `update-ca-certificates` 更新证书
3. 查看完整的错误堆栈，关注API服务器地址
4. 确认网络连接能访问 `https://api.123pan.com`


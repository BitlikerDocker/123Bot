# 123Bot

`123Bot` 是一个面向 `123 网盘` 的 `Telegram Bot` 秒传工具。

它的核心流程是：

1. 接收 Telegram 上传的 `.json` / `.txt` 文件
2. 解析 123 网盘导出的文件清单
3. 将待处理记录写入本地 `SQLite`
4. 按目录结构调用 123 秒传接口批量导入文件

项目适合下面这些场景：

- 通过 Telegram 远程投递导出的资源清单
- 批量导入 123 网盘分享/备份清单
- 将上传任务排队执行，避免一次性堆积
- 保留本地数据库状态，支持失败重试

## 功能概览

- 支持 Telegram Bot 指令操作
- 支持接收 `.json` 和 `.txt` 文件
- 支持两种 JSON 输入格式
- 支持 Base62 ETag 自动转换为 MD5
- 支持将文件记录写入本地 SQLite 队列
- 支持按远程目录自动创建文件夹后秒传
- 支持上传失败记录再次重试
- 支持白名单限制 Bot 使用者
- 支持运行中查看当前任务状态
- 支持通过 Telegram 菜单在线修改部分配置

## 项目结构

```text
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── src
    ├── __main__.py          # 程序入口
    ├── bot.py               # Telegram Bot
    ├── job.py               # 任务队列与串行执行
    ├── p123_client.py       # 123 网盘客户端封装
    ├── p123_link.py         # JSON 解析与秒传逻辑
    └── config
        ├── config.py        # 配置加载
        ├── database.py      # SQLite 数据库
        ├── logs.py          # 日志初始化
        └── format.py
```

## 工作原理

项目内部主要由 4 个部分组成：

- `bot.py`：处理 Telegram 指令、接收文件、推送任务状态
- `job.py`：维护单例任务管理器，串行执行“解析入库”和“批量上传”
- `p123_link.py`：解析导出的 JSON 文件，转换为数据库记录，并调用秒传
- `config/database.py`：使用 `dataset + SQLite` 保存待上传、上传中、成功、失败状态

一个典型流程如下：

1. 用户向 Bot 发送 `.json` 或 `.txt`
2. 文件保存到本地 `JSON_PATH`
3. 机器人触发 `json_to_db`
4. 程序把每条文件记录写入 SQLite
5. 执行 `/upload` 后从数据库取出待上传记录
6. 按文件路径自动创建远程目录并执行秒传
7. 成功的记录标记为 `UPLOADED`，失败的标记为 `FAILED`

## 环境要求

- Python `3.12`（Dockerfile 当前使用 `python:3.12-slim`）
- 一个可用的 `123 网盘` 账号
- 一个可用的 `Telegram Bot Token`
- 能访问 123 网盘接口和 Telegram API 的网络环境

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：

- `P123Client`
- `pytelegrambotapi`
- `dataset`

## 配置说明

项目实际加载配置的优先级是：

`config.json -> 环境变量默认值补全`

也就是说：

- 如果 `config.json` 已存在，会优先读取其中的字段
- 环境变量只会补齐缺失字段，不会强制覆盖已有配置
- 程序启动后会把最终配置写回 `config.json`

### 实际使用的环境变量

下面这些变量名是代码当前真正读取的字段：

| 变量名 | 说明 | 默认值 |
| --- | --- | --- |
| `P123_USER_NAME` | 123 网盘手机号 | 无 |
| `P123_PASSWORD` | 123 网盘密码 | 无 |
| `P123_PARENT_ID` | 上传到 123 网盘的父目录 ID | `0` |
| `TG_TOKEN` | Telegram Bot Token | 无 |
| `TG_USER_WHITE_LIST` | Telegram 白名单用户 ID，逗号分隔 | 空 |
| `IS_AUTO_UPLOAD` | 是否自动上传 | `false` |
| `MEDIA_PATH` | 媒体根目录 | `/app/media` |
| `CONFIG_PATH` | 配置目录 | `{MEDIA_PATH}/config` |
| `JSON_PATH` | 待处理 JSON 目录 | `{MEDIA_PATH}/json` |
| `ARCHIVE_PATH` | 已解析归档目录 | `{MEDIA_PATH}/archive` |
| `FAIL_PATH` | 失败归档目录 | `{MEDIA_PATH}/fail` |

### 推荐目录约定

```text
MEDIA_PATH/
├── config/
│   ├── config.json
│   └── db.sqlite3
├── json/
├── archive/
├── fail/
└── logs/
```

### `config.json` 示例

```json
{
  "p123_username": "13800138000",
  "p123_password": "your-password",
  "p123_token": "",
  "tg_token": "123456:telegram-bot-token",
  "tg_user_white_list": [123456789],
  "is_auto_upload": false,
  "upload_limit": 100,
  "media_path": "/app/media",
  "json_path": "/app/media/json",
  "archive_path": "/app/media/archive",
  "fail_path": "/app/media/fail"
}
```

## 本地运行

### 1. 准备目录

```bash
mkdir -p tmp/{config,json,archive,fail,logs}
```

### 2. 设置环境变量

```bash
export MEDIA_PATH="$(pwd)/tmp"
export CONFIG_PATH="$(pwd)/tmp/config"
export JSON_PATH="$(pwd)/tmp/json"
export ARCHIVE_PATH="$(pwd)/tmp/archive"
export FAIL_PATH="$(pwd)/tmp/fail"
export P123_USER_NAME="你的123手机号"
export P123_PASSWORD="你的123密码"
export TG_TOKEN="你的TelegramBotToken"
export TG_USER_WHITE_LIST="123456789"
export P123_PARENT_ID="0"
```

### 3. 启动程序

```bash
python src/__main__.py
```

启动后程序会：

- 自动创建配置目录和媒体目录
- 初始化 SQLite 数据库
- 登录 123 网盘，必要时刷新 token
- 启动 Telegram 轮询

## Docker 部署

### 构建镜像

```bash
docker build -t 123bot:latest .
```

### 推荐运行方式

```bash
docker run -d \
  --name 123bot \
  -e P123_USER_NAME="你的123手机号" \
  -e P123_PASSWORD="你的123密码" \
  -e TG_TOKEN="你的TelegramBotToken" \
  -e TG_USER_WHITE_LIST="123456789" \
  -e P123_PARENT_ID="0" \
  -e MEDIA_PATH="/app/media" \
  -e CONFIG_PATH="/app/media/config" \
  -e JSON_PATH="/app/media/json" \
  -e ARCHIVE_PATH="/app/media/archive" \
  -e FAIL_PATH="/app/media/fail" \
  -v $(pwd)/tmp:/app/media \
  --restart unless-stopped \
  123bot:latest
```

### 推荐 `docker-compose.yml`

仓库中已有 `docker-compose.yml`，但它当前示例中的变量名和挂载目录与代码实现并不完全一致。实际部署时建议使用下面这一版思路：

```yaml
version: "3.8"

services:
  p123-bot:
    build: .
    container_name: p123-bot
    restart: unless-stopped
    environment:
      P123_USER_NAME: ${P123_USER_NAME}
      P123_PASSWORD: ${P123_PASSWORD}
      P123_PARENT_ID: ${P123_PARENT_ID:-0}
      TG_TOKEN: ${TG_TOKEN}
      TG_USER_WHITE_LIST: ${TG_USER_WHITE_LIST:-}
      MEDIA_PATH: /app/media
      CONFIG_PATH: /app/media/config
      JSON_PATH: /app/media/json
      ARCHIVE_PATH: /app/media/archive
      FAIL_PATH: /app/media/fail
      PYTHONUNBUFFERED: "1"
      PYTHONDONTWRITEBYTECODE: "1"
    volumes:
      - ./tmp:/app/media
```

启动：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker logs -f p123-bot
```

## Telegram 指令

机器人当前注册了以下命令：

| 指令 | 说明 |
| --- | --- |
| `/start` | 显示帮助信息 |
| `/help` | 显示帮助信息 |
| `/status` | 查看当前任务与队列状态 |
| `/san` | 扫描 `JSON_PATH` 目录，把文件解析写入数据库 |
| `/upload` | 从数据库中取待处理记录执行秒传 |
| `/setting` | 打开 Telegram 内联设置菜单 |

### 文件投递

Bot 支持接收：

- `.json`
- `.txt`

收到文件后会：

1. 保存到 `JSON_PATH`
2. 自动提交“解析入库”任务
3. 任务完成后通过 Telegram 回复结果

当前代码里 `is_auto_upload` 逻辑已经预留，但自动上传触发流程仍处于注释状态，所以实际更稳妥的使用方式是：

1. 先上传文件
2. 等待入库完成
3. 手动执行 `/upload`

## 支持的 JSON 格式

### 格式 1：123 导出原始格式

```json
{
  "usesBase62EtagsInExport": true,
  "commonPath": "根目录/",
  "files": [
    {
      "etag": "3xrsuPs9x8mM59QJAToVf",
      "size": "867071302",
      "path": "目录A/文件1.mkv"
    }
  ]
}
```

说明：

- 支持 `usesBase62EtagsInExport=true`
- 如果是 Base62 ETag，会自动转换成标准 MD5
- 远程目录由 `commonPath + path` 拼接得到

### 格式 2：简化数组格式

```json
[
  ["242500524fcc5d58ff7d2078cd409c", 867071302, "目录A/文件1.mkv"],
  ["86b066225e66aa0dbabaf942555d00f", 123456789, "目录B/文件2.mp4"]
]
```

每一项分别为：

`[md5, size, path]`

## 数据库说明

项目使用 `SQLite` 保存任务状态，主要状态有：

| 状态值 | 含义 |
| --- | --- |
| `0` | `INIT`，待上传 |
| `1` | `UPLOADING`，上传中 |
| `2` | `UPLOADED`，已上传 |
| `3` | `FAILED`，上传失败 |

程序执行 `/upload` 时会优先读取：

1. `INIT`
2. 如果没有 `INIT`，再读取 `FAILED`

这意味着失败记录可以在下次执行时被重新尝试。

## 日志与数据文件

默认情况下会在 `MEDIA_PATH/logs` 下写日志文件，同时控制台也会输出日志。

常见路径：

- 配置文件：`{CONFIG_PATH}/config.json`
- 数据库文件：`{CONFIG_PATH}/db.sqlite3`
- 待处理文件：`{JSON_PATH}`
- 已归档文件：`{ARCHIVE_PATH}`
- 失败文件目录：`{FAIL_PATH}`
- 日志目录：`{MEDIA_PATH}/logs`

## 常见问题

### 1. 为什么 `.env.example` 里的字段和代码对不上？

当前仓库里的 `.env.example` 仍然偏旧，README 这里已经按代码实际读取的变量名编写。部署时请优先使用本页中的变量名。

### 2. 为什么 `docker-compose.yml` 的卷映射看起来不一致？

当前源码默认使用 `MEDIA_PATH=/app/media`，而仓库中的 compose 示例把部分目录挂载到了 `/app/tmp/...`。如果不显式覆盖 `MEDIA_PATH / JSON_PATH / ARCHIVE_PATH`，会导致路径不一致。推荐直接把整个宿主目录挂到 `/app/media`。

## 已知限制

- 当前任务管理器是单进程串行执行，不是分布式队列
- `is_auto_upload` 配置项已存在，但自动上传流程目前未真正启用
- 目前数据库去重主要按 `path` 判断
- 失败文件目录 `FAIL_PATH` 已预留，但当前主流程里未完整使用
- `README` 中的推荐部署方式比仓库现有示例更接近当前代码真实行为

## 开发与调试建议

本地调试时推荐优先检查：

1. Telegram Bot Token 是否有效
2. 白名单用户 ID 是否正确
3. 123 账号是否能成功登录
4. `JSON_PATH` 是否真的存在且有读写权限
5. JSON 文件字段是否符合支持格式

## 致谢

- [P123Client](https://github.com/ChenyangGao/p123client)

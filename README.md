# 123盘秒传机器人

用户管理123盘妙传的telegram机器人, 用于快速上传json并且秒传

## 功能

- [] 转存json
- [] 通过json解析并且上传
- [] 定时任务自动扫描上传
- [] 扫描上传失败文件并上传
- [] 监控文件变更, 自动上传

## 关键路径

- MEDIA = /media
- CONFIG_PATH = {MEDIA}/config/config.json
- JSON_PATH = {MEDIA}/json/
- ARCHIVE_PATH = {MEDIA}/archive/
- FAIL_PATH = {MEDIA}/fail/

## 变量

- USER_NAME: 123盘手机号码
- PASSWORD: 123盘密码
- TG_TOKEN: telegram bot token
- TG_USER_WHITE_LIST: telegram 可以使用的 bot 白名单用户id列表, 多个id用,隔开
- MEDIA: 媒体根目录, 默认 /media
- CONFIG_PATH: 配置文件路径
- JSON_PATH: json文件的目录
- ARCHIVE_PATH: 已完成上传的文件归档路径
- FAIL_PATH: 上传失败文件归档路径

### 配置获取优先级

config.json -> env

`config.json` 示例:

```json
{
    "123_username": "123手机号码",
    "123_password": "123密码",
    "123_token": "123token",
    "tg_token":"telegram bot token",
    "tg_user_white_list":[
        "telegram 可以使用的 bot 白名单用户id"
    ],
    "media":"/media",
    "json_path":"/media/json",
    "archive_path":"/media/archive",
    "fail_path":"/media/fail"
}
```

## 感谢&依赖

- [P123Client](https://github.com/ChenyangGao/p123client)

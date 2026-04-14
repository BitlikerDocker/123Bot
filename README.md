# 123盘秒传机器人

用户管理123盘妙传的telegram机器人, 用于快速上传json并且秒传

## 关键路径

- MEDIA = /media
- CONFIG_PATH = {MEDIA}/config/config.json
- JSON_PATH = {MEDIA}/json/
- ARCHIVE_PATH = {MEDIA}/archive/
- FAIL_PATH = {MEDIA}/fail/

## 变量

- PHONE: 123盘手机号码
- PASSWORD: 123盘密码

### 配置获取优先级

config.json -> env

## 感谢&依赖

- [P123Client](https://github.com/ChenyangGao/p123client)

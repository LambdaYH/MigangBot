<div align=center><img height="320" src="https://image.cinte.cc/i/2023/03/11/640c74d38b7a9.jpg"/></div>
<div align=right><font color=gray size=1>图片来自：暖暖与美梦神</font></div>

<div align=center>
<h1>MigangBot </br><font size=3>基于Nonebot2的米缸Bot<font></h1>

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/d320da31c517440890c47032c4b4c25e)](https://www.codacy.com/gh/LambdaYH/MigangBot/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=LambdaYH/MigangBot&amp;utm_campaign=Badge_Grade)[![license](https://img.shields.io/github/license/LambdaYH/MigangBot)](https://github.com/LambdaYH/MigangBot/main/LICENSE)![python](https://img.shields.io/badge/Python-3.10-blue)
</div>

# 关于
自用Bot，开发中。~~没学过`Python`所以是乱写的~~

基于nonebot2，插件和素材~~来自~~缝合自各地的米缸Bot

思路和素材很大程度上来自[HibiKier/zhenxun_bot](https://github.com/HibiKier/zhenxun_bot)

# 部署
<details><summary>Debian/Ubuntu下的部署</summary>
⚠️ 仅在Debian11 + Python3.10 + Postgres 下测试过

1.  安装系统依赖
```
sudo apt install libopencv-dev fonts-noto
```
2.  安装Postgres并创建数据库（如果不用Postgres就默认使用sqlite，db文件在`data/database/migangbot.db`）
```
sudo apt install postgresql postgresql-contrib
sudo su - postgres
psql
```
```sql
CREATE USER migangbot_user WITH PASSWORD 'migangbot_password';
CREATE DATABASE migangbot_db OWNER migangbot_user;
```
3. 安装Python3.10（编译安装或者用包管理器）
<details><summary>编译安装</summary>

1.  安装依赖

```
sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev
```
2.  下载源码并解压
```
wget https://www.python.org/ftp/python/3.10.10/Python-3.10.10.tgz
tar -zxvf Python-3.10.10.tgz
```
3.  编译
```
cd Python-3.10.10/
./configure --enable-optimizations
make -j 2
```
4.  安装
```
sudo make altinstall
```
</details>

<details><summary>包管理器</summary>
不知道哪个发行版的默认python3是python3.10
</details>

4.  安装pdm
```
pip3.10 install pdm
```
5.  下载MigangBot并安装依赖
```
git clone https://github.com/LambdaYH/MigangBot.git
cd MigangBot
pdm install
```
6.  配置数据库（若跳过这步则使用sqlite）
```
cp db_config.yaml.example db_config.yaml
```
并完成`db_config.yaml`的编辑

7.  启动一次Bot生成各项配置文件
```
# 先编辑 .env.prod
nb run
```
8.  编辑所需文件（参考[运行时各文件/路径说明](#运行时各文件路径说明)）
9.  持久化运行（二选一）
- 使用`supervisor`
```
sudo apt install supervisor
cd scripts
python generate_supervisor_conf.py
cp migangbot.conf /etc/supervisor/conf.d/
sudo supervisorctl update
```
- 使用screen
```
sudo apt install screen
python scripts/generate_run_script.py
screen -S migangbot
pdm run all
```
</details>

# 可用功能（部分）
<details><summary>帮助图片</summary>
从 zhenxun_bot 那改的样式

![](https://image.cinte.cc/i/2023/04/02/6428f095052c3.png)
</details>

<details><summary>群被动</summary>
微博推送是自己配置的

![](https://image.cinte.cc/i/2023/04/02/6428f09338bc6.png)
</details>

# 运行时各文件/路径说明
| 路径/文件名 | 说明 |
| :--- | :--- |
| configs/ | 存储着`yaml`格式的各插件配置项，请按需修改 |
| resources/ | 一些资源，主要是字体 |
| data/ | 各插件运行时数据 |
| data/core/ | 存储着Bot核心运行数据，可按需修改 |
| data/core/count_manager.json | 记录各插件的使用次数，方便进行使用次数限制，一般无需修改 |
| data/core/help/ | 存储各项帮助图片缓存，一般无需修改 |
| data/core/plugin_manager/ | 存储插件的配置项，可按需修改，尤其是可对来自插件商店的插件进行修改 |
| data/core/task_manager/ | 存储群被动配置项，一般无需修改 |
| data/core/custom_usage.yaml | 自定义插件的使用说明，格式为`插件名: 使用说明` |
| data/core/default_value_cache.json | 记录默认值缓存，不要改 |
| data/core/permission_manager.json | 当存在定时设置的权限时，该定时项会持久化到这个文件 |

### data/core/plugin_manager/*.json 各键值说明
> 文件名是插件名

| 键值 | 说明 | 类型 |
| :--- | :--- | :--- |
| name | 插件显示出来的名字 | `str` |
| aliases | 别名 | `List[str]` |
| group_permission | >=此群权限的群才可触发该插件 | `int`（1 - 5）  |
| user_permission | >=此用户权限的用户才可触发该插件 | `int`（1 - 5）  |
| global_status | 全局启用状态 | `bool` |
| default_status | 默认启用状态 | `bool` |
| enabled_group | 启用的群，仅默认启用状态为`false`时生效 | `List[int]` |
| disabled_group | 禁用的群，仅默认启用状态为`true`时生效 | `List[int]` |
| category | 插件类别，用于帮助图片中的分类显示 | `str` |
| hidden | 是否在帮助界面中隐藏 | `bool` |
| author | 插件作者，虽然放着这么一个项，但是完全没用 | `str` |
| version | 插件版本，虽然放着这么一个项，但是完全没用 | `any` |

### data/core/custom_usage.yaml 说明
- text: 直接写就行
- markdown: 说明的开头加上`[md]`，可选择性添加`[width=xxx]`来指定生成的图片宽度
- html: 说明的开头加上`[html]`，可选择性添加`[width=xxx,height=xxx]`来指定宽度与高度



# 致谢
- [HibiKier/zhenxun_bot](https://github.com/HibiKier/zhenxun_bot)
- [MeetWq/mybot](https://github.com/MeetWq/mybot)
- [iamwyh2019/aircon](https://github.com/iamwyh2019/aircon)
- [A-kirami/answersbook](https://github.com/A-kirami/answersbook)
- [MinatoAquaCrews/nonebot_plugin_crazy_thursday](https://github.com/MinatoAquaCrews/nonebot_plugin_crazy_thursday)
- [SonderXiaoming/dailywife](https://github.com/SonderXiaoming/dailywife)
- [A-kirami/nonebot-plugin-cartoon](https://github.com/A-kirami/nonebot-plugin-cartoon)
- [lgc2333/nonebot-plugin-picmcstat](https://github.com/lgc2333/nonebot-plugin-picmcstat)
- [nikissXI/nonebot_plugin_mc_server_status](https://github.com/nikissXI/nonebot_plugins/tree/main/nonebot_plugin_mc_server_status)
- [laipz8200/music](https://github.com/pcrbot/music)
- [C-Jun-GIT/Oreo](https://github.com/C-Jun-GIT/Oreo)
- [kexue-z/nonebot-plugin-heweather](https://github.com/kexue-z/nonebot-plugin-heweather)
- [Ice-Cirno/HoshinoBot](https://github.com/Ice-Cirno/HoshinoBot)
- [he0119/nonebot-plugin-wordcloud](https://github.com/he0119/nonebot-plugin-wordcloud)
- [Kyomotoi/ATRI](https://github.com/Kyomotoi/ATRI)
- ...

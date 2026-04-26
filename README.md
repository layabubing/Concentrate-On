# ConcentrateOn

一个本地运行的专注工具，使用 Python 提供后端服务，配合内置 Web UI 展示专注状态、历史记录和屏蔽网站设置。

项目启动后可以：

- 开始/结束一次专注会话
- 记录累计专注时长和最近专注历史
- 配置默认专注时长
- 配置需要屏蔽的站点列表
- 在有管理员权限时，通过修改 `hosts` 文件屏蔽网站
- 优先以桌面窗口运行；如果本机没有可用 WebView，则自动回退到浏览器模式

## 项目结构

```text
ConcentrateOn/
├─ ui.py                    # 应用入口，HTTP 服务与桌面/浏览器启动逻辑
├─ ban_website/
│  └─ redirector.py         # hosts 文件屏蔽逻辑
├─ webui/
│  ├─ index.html            # 前端页面
│  ├─ app.js                # Vue UI 逻辑
│  ├─ app.css               # 界面样式
│  └─ vendor/
│     └─ vue.global.prod.js
├─ assets/
│  ├─ fonts/
│  └─ icons/
└─ .concentrateon/          # 运行后生成的本地状态目录
```

## 功能概览

- 专注计时：开始后实时展示已专注时长
- 会话统计：累计专注时长、累计次数、今日时长、今日次数
- 历史记录：最近专注记录会保存在本地
- 网站屏蔽：可配置多个域名，专注开始时自动应用，结束时自动清除
- 本地优先：所有状态保存在本地，不依赖外部服务

# For Developers

## 运行环境

- Python 3.10+
- Windows、macOS 或 Linux
- 可选：`pywebview`，用于桌面窗口模式

## 安装

```bash
pip install -r requirements.txt
```

`requirements.txt` 当前只包含：

- `pywebview>=6.2,<7`

如果不安装 `pywebview`，程序仍可运行，但会回退到浏览器模式。

## 启动方式

### 默认启动

```bash
python ui.py
```

默认行为：

- 如果可用，打开桌面窗口
- 否则自动启动本地服务并在浏览器中打开页面

### 浏览器模式

```bash
python ui.py --browser
```

### 仅启动本地服务

```bash
python ui.py --headless
```

### 指定监听地址和端口

```bash
python ui.py --host 127.0.0.1 --port 8000
```

如果 `--port` 不指定，程序会自动分配可用端口。

## 命令行参数

| 参数 | 说明 |
| --- | --- |
| `--host` | 监听地址，默认 `127.0.0.1` |
| `--port` | 监听端口，默认自动分配 |
| `--browser` | 强制使用浏览器模式 |
| `--headless` | 只启动服务，不自动打开界面 |

## 网站屏蔽说明

网站屏蔽通过修改系统 `hosts` 文件实现。

- Windows 默认路径：`C:\Windows\System32\drivers\etc\hosts`
- 非 Windows 默认路径：`/etc/hosts`

注意：

- 没有管理员权限时，专注会话仍然可以开始
- 但网站屏蔽不会生效，界面会显示相关提示
- 程序结束专注或退出时，会尝试清理自己写入的 `hosts` 记录

目前每个域名会同时写入两条规则：

- `example.com`
- `www.example.com`

## 数据存储

应用状态保存在项目根目录下的本地文件：

```text
.concentrateon/state.json
```

其中包括：

- 当前设置
- 当前是否有进行中的专注会话
- 最近历史记录

历史记录在保存时会保留最近 100 条。

## 前后端实现说明

- 后端：`ui.py`
  - 使用 Python 标准库 `http.server` 提供接口和静态资源
  - 提供 `/api/state`、`/api/focus/start`、`/api/focus/stop`、`/api/settings`
- 前端：`webui/`
  - 使用本地引入的 Vue 运行时
  - 不依赖额外前端构建工具

这意味着项目非常轻量，拉下来后安装 Python 依赖即可运行。

## 已实现的接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/state` | 获取当前状态、统计和历史 |
| `POST` | `/api/focus/start` | 开始专注 |
| `POST` | `/api/focus/stop` | 结束专注 |
| `POST` | `/api/settings` | 更新默认时长与屏蔽站点 |

## 注意事项

1. 网站屏蔽依赖修改系统文件，部分系统环境可能会触发权限弹窗或安全软件提示。
2. 如果程序异常退出，理论上会在退出流程里清理屏蔽规则，但仍建议在开发和调试时留意 `hosts` 文件状态。
3. 当前项目的数据目录是相对项目根目录创建的，适合本地个人使用。

## TODO
- 添加前后端通讯
- 实现跨平台互通
- 性能优化
- 数据统计
- 个性化设置

## License

本项目使用仓库中的 [LICENSE](LICENSE)。

README write by GPT 5.4

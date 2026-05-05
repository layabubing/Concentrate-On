# ConcentrateOn

ConcentrateOn 是一个本地运行的专注工具。它使用 Python 提供轻量 HTTP 服务，前端使用本地 Vue 运行时构建界面，可在桌面窗口或浏览器中使用。

应用适合个人本地使用：专注计时、番茄钟、任务管理、统计记录、网站屏蔽和界面个性化设置都保存在本机，不依赖外部服务。

## 功能特性

- 专注计时：开始和结束普通专注会话，并显示剩余时间。
- 番茄钟：支持番茄专注、短休息、长休息，并可关联具体任务。
- 任务管理：添加、完成、删除任务，并记录任务完成的番茄数量。
- 数据统计：展示今日专注、累计专注、番茄数量和最近记录。
- 网站屏蔽：专注开始时尝试写入系统 `hosts` 文件，结束或退出时自动清理。
- 个性化设置：支持浅色/深色主题，以及淡蓝、淡绿、淡红、淡黄配色。
- 自动保存：设置变更后自动保存，不需要手动点击保存。
- 本地优先：主要状态保存在 `.concentrateon/state.json`，界面偏好会辅助写入浏览器本地存储以减少启动闪烁。

## 项目结构

```text
ConcentrateOn/
├─ ui.py                         # 应用入口、HTTP API、静态资源服务、桌面/浏览器启动逻辑
├─ ban_website/
│  └─ redirector.py              # hosts 文件屏蔽与清理逻辑
├─ webui/
│  ├─ index.html                 # Web UI 页面入口
│  ├─ app.js                     # Vue 应用状态、接口调用、自动保存逻辑
│  ├─ app.css                    # 主题、布局和组件样式
│  ├─ components/
│  │  ├─ focus-page.js           # 专注与番茄钟页面
│  │  ├─ tasks-page.js           # 任务页面
│  │  ├─ stats-page.js           # 统计页面
│  │  └─ settings-page.js        # 设置页面
│  └─ vendor/
│     └─ vue.global.prod.js      # 本地 Vue 运行时
├─ assets/
│  ├─ fonts/                     # 字体资源
│  └─ icons/                     # 图标资源
├─ requirements.txt              # Python 依赖
└─ .concentrateon/               # 运行后生成的本地状态目录
```

## 环境要求

- Python 3.10+
- Windows、macOS 或 Linux
- 可选桌面窗口依赖：`pywebview`

安装依赖：

```bash
pip install -r requirements.txt
```

当前 `requirements.txt` 包含：

```text
pywebview>=6.2,<7
```

如果桌面 WebView 不可用，应用会自动回退到浏览器模式。

## 启动方式

默认启动：

```bash
python ui.py
```

默认行为：

- 优先打开桌面窗口。
- 如果没有可用 WebView，则启动本地服务并在浏览器中打开。
- 默认监听 `127.0.0.1`，端口由系统自动分配。

强制浏览器模式：

```bash
python ui.py --browser
```

仅启动本地服务，不自动打开界面：

```bash
python ui.py --headless
```

指定监听地址和端口：

```bash
python ui.py --host 127.0.0.1 --port 8000
```

## 命令行参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--host` | `127.0.0.1` | HTTP 服务监听地址 |
| `--port` | `0` | HTTP 服务监听端口，`0` 表示自动分配可用端口 |
| `--browser` | `false` | 使用浏览器模式运行 |
| `--headless` | `false` | 只启动本地服务，不打开窗口或浏览器 |

## 数据存储

应用状态保存在项目根目录下：

```text
.concentrateon/state.json
```

保存内容包括：

- 专注和番茄钟时长设置
- 主题模式与配色设置
- 需要屏蔽的网站列表
- 当前会话状态
- 任务列表
- 最近专注记录

历史记录保存时会保留最近 100 条。前端还会使用 `localStorage` 记住最后停留页面，并在页面加载早期应用上一次外观设置以减少视觉闪烁；真正的设置以 `state.json` 中的后端状态为准。

## 网站屏蔽说明

网站屏蔽通过修改系统 `hosts` 文件实现。

默认路径：

| 系统 | hosts 路径 |
| --- | --- |
| Windows | `C:\Windows\System32\drivers\etc\hosts` |
| macOS / Linux | `/etc/hosts` |

注意事项：

- 修改 `hosts` 文件通常需要管理员或 root 权限。
- 没有权限时，专注会话仍可开始，但网站屏蔽不会生效，界面会显示提示。
- 应用只会清理带有 `# Added by ConcentrateOn` 标记的记录。
- 每个域名会同时写入裸域名和 `www.` 域名，例如 `example.com` 与 `www.example.com`。

## HTTP API

后端使用 Python 标准库 `http.server` 提供 API 和静态资源。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/state` | 获取设置、当前会话、任务、统计和最近记录 |
| `POST` | `/api/focus/start` | 开始专注、番茄钟或休息会话 |
| `POST` | `/api/focus/stop` | 结束当前会话并写入历史 |
| `POST` | `/api/settings` | 更新时长、屏蔽网站、主题和配色 |
| `POST` | `/api/tasks` | 新增任务 |
| `POST` | `/api/tasks/{task_id}` | 更新或删除任务 |

`/api/focus/start` 常用请求体：

```json
{
  "session_type": "focus",
  "task_id": null
}
```

`session_type` 支持：

- `focus`
- `pomodoro`
- `short_break`
- `long_break`

`/api/settings` 常用请求体：

```json
{
  "session_minutes": 45,
  "pomodoro_minutes": 25,
  "short_break_minutes": 5,
  "long_break_minutes": 15,
  "long_break_every": 4,
  "blocked_domains": ["example.com"],
  "theme_mode": "light",
  "color_scheme": "blue"
}
```

`theme_mode` 支持 `light`、`dark`。`color_scheme` 支持 `blue`、`green`、`red`、`yellow`。

删除任务时向 `/api/tasks/{task_id}` 发送：

```json
{
  "_delete": true
}
```

## 开发说明

- 前端不需要构建步骤，直接由 `ui.py` 提供静态资源。
- Vue 运行时放在 `webui/vendor/vue.global.prod.js`。
- 前端组件按页面拆分在 `webui/components/`。
- 设置页采用自动保存：输入变更会防抖提交，主题和配色会立即预览并自动保存。
- 后端状态由 `StateStore` 读写 `.concentrateon/state.json`。

常用检查命令：

```bash
python -m py_compile ui.py
node --check webui/app.js
node --check webui/components/settings-page.js
```

## 常见问题

### 为什么网站屏蔽没有生效？

请确认应用是否以管理员或 root 权限运行。没有权限时应用不会修改系统 `hosts` 文件，但专注计时仍然可用。

### 为什么关闭后重新打开主题没有保留？

主题和配色会保存到 `.concentrateon/state.json`。如果没有保留，请确认设置页显示过“已自动保存”，并确认项目目录可写。

### 异常退出后 hosts 文件没有清理怎么办？

应用写入的记录都会带有 `# Added by ConcentrateOn` 标记。可以手动打开系统 `hosts` 文件，删除包含该标记的行。

## License

本项目使用仓库中的 [LICENSE](LICENSE)。

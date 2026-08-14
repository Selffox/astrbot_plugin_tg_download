# astrbot_plugin_tg_download

TG 文件自动下载插件：把 Telegram 消息里的文件（文档/视频/音频/图片）自动下载到服务器，通过 Aria2 + Alist 统一管理。

## ✨ 功能

- 监听 Telegram 消息，识别文件消息（document / video / audio / photo / video_note）
- **≤20MB 文件**：自动调用 Telegram API 拿直链 → 提交 Aria2 下载到服务器
- **>20MB 文件**：提示用户（Telegram Bot API 限制，超大文件需其他方案）
- 下载完成自动出现在 Alist「下载」文件夹，全设备可访问

## 🔧 配置（main.py 内常量）

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `api_base` | Telegram API 地址 | `https://api.telegram.org/bot` |
| `bot_token` | Bot Token | `你的BotToken` |
| `file_base` | 文件下载地址 | `https://api.telegram.org/file/bot` |
| `aria2_rpc` | Aria2 JSON-RPC | `http://aria2:xxxx/json` |
| `aria2_secret` | Aria2 RPC 密钥 | `你的Aria2密钥` |
| `download_dir` | 下载目录 | `/downloads` |
| `max_size` | 大小上限 | 20MB（Bot API 限制） |

## 📦 依赖

- AstrBot（本插件基于 Star 插件框架）
- `httpx`（AstrBot 环境自带，python-telegram-bot 依赖）
- Aria2 容器（需和 AstrBot 在同一 Docker 网络，用容器名 `aria2` 访问）
- Alist（挂载下载目录 `/downloads`）

## 🚀 部署步骤

1. 创建插件目录：
```bash
sudo mkdir -p /opt/astrbot/data/plugins/astrbot_plugin_tg_download
```

2. 放入 `main.py` 和 `metadata.yaml`：
```bash
sudo cp main.py /opt/astrbot/data/plugins/astrbot_plugin_tg_download/
sudo cp metadata.yaml /opt/astrbot/data/plugins/astrbot_plugin_tg_download/
```

3. 确保 AstrBot 容器和 Aria2 在同一 Docker 网络（compose 里 astrbot 加 `alist-net`）

4. 重启 AstrBot：
```bash
docker restart astrbot
```

5. WebUI → 插件管理 → 启用 `astrbot_plugin_tg_download`

## 📖 使用方法

1. 在 Telegram 里把文件（≤20MB）**转发给 bot**
2. Bot 回复「📥 收到文件，开始下载~」
3. 下载完成，文件出现在 Alist「下载」文件夹
4. 任何设备通过 Alist / WebDAV 访问

## ⚠️ 注意事项

- **20MB 限制**：Telegram Bot API 的 `getFile` 只能下载 ≤20MB 文件，超过会被拒绝
- **网络**：国内服务器访问 Telegram 需要 Cloudflare Worker 代理
- **Aria2 地址**：AstrBot 在容器内，Aria2 地址要用**容器名**（`http://aria2:6800`），不能用 127.0.0.1

## 🐛 常见问题

**Q：插件加载失败，报 `no attribute 'event_type'`？**
A：AstrBot API 版本问题，用 `@filter.event_message_type(EventMessageType.ALL)`，并从 `astrbot.core.star.filter.event_message_type` 导入 EventMessageType。

**Q：转发文件后没反应/报 `attribute name must be string`？**
A：telegram.Message 是对象不是字典，用 `getattr(msg, k, None)` 访问属性，别用 `msg[k]`。

**Q：提交下载失败，报 `All connection attempts failed`？**
A：AstrBot 容器内 127.0.0.1 连不到 Aria2。确认 astrbot 和 aria2 在同一网络，aria2_rpc 用容器名。

**Q：插件异常会影响聊天吗？**
A：不会。AstrBot 有插件异常隔离，插件报错只影响该消息，可随时在 WebUI 禁用插件。

# astrbot_plugin_tg_download

TG 文件自动下载插件：把 Telegram 消息里的文件（文档/视频/音频/图片）自动下载到服务器，通过 Aria2 + Alist 统一管理。

## ✨ 功能

- 监听 Telegram 消息，识别文件消息（document / video / audio / photo / video_note）
- **≤20MB 文件**：自动下载到 Aria2，按类型分类到 Alist（图片/音频/视频/其他子目录）
- **20MB~2GB 文件**：询问主人「保存到本地还是服务器」，按回复处理
- **>2GB 文件**：提示超大文件，建议电脑端处理
- 下载完成自动出现在 Alist「下载」文件夹，全设备可访问

## 🔧 配置（环境变量）

插件通过环境变量配置，在 AstrBot 容器中设置：

| 环境变量 | 说明 | 示例 |
|---|---|---|
| `TG_BOT_TOKEN` | Telegram Bot Token（必填） | `123456:ABC...` |
| `TG_API_BASE` | Telegram API 地址 | `https://api.telegram.org/bot` |
| `TG_FILE_BASE` | 文件下载地址 | `https://api.telegram.org/file/bot` |
| `ARIA2_RPC` | Aria2 JSON-RPC 地址 | `http://aria2:6800/jsonrpc` |
| `ARIA2_SECRET` | Aria2 RPC 密钥（必填） | `你的密钥` |

> 💡 国内服务器访问 Telegram 需配置代理地址（如 Cloudflare Worker：`https://your-worker.workers.dev/bot`）。

## 📦 依赖

- AstrBot（Star 插件框架）
- `httpx`（异步 HTTP）
- Aria2 容器（与 AstrBot 同一 Docker 网络，容器名 `aria2`）
- Alist（挂载下载目录）

## 🚀 部署步骤

1. 安装插件（AstrBot 插件市场搜索「TG 文件下载」，或手动放入 `data/plugins/astrbot_plugin_tg_download/`）

2. 配置环境变量（Docker Compose 示例）：
```yaml
services:
  astrbot:
    environment:
      - TG_BOT_TOKEN=${TG_BOT_TOKEN}
      - TG_API_BASE=${TG_API_BASE}
      - TG_FILE_BASE=${TG_FILE_BASE}
      - ARIA2_RPC=${ARIA2_RPC}
      - ARIA2_SECRET=${ARIA2_SECRET}
```

3. 确保 AstrBot 和 Aria2 在同一 Docker 网络（compose 里加 `alist-net`）

4. 重启 AstrBot，WebUI 插件管理启用

## 📖 使用方法

1. 在 Telegram 里把文件**转发给 bot**
2. **≤20MB**：自动下载，Bot 回复下载状态
3. **20MB~2GB**：Bot 询问「保存到【本地】还是【服务器】？」，回复对应文字
4. 下载完成，文件出现在 Alist「下载」文件夹（按类型分类）

## ⚠️ 注意事项

- **20MB 限制**：Telegram Bot API 的 `getFile` 只能下载 ≤20MB 文件（20MB~2GB 的文件需要配合电脑端方案）
- **Aria2 地址**：AstrBot 在容器内，Aria2 地址用**容器名**（`http://aria2:6800`），不能用 127.0.0.1
- **敏感信息**：Bot Token / Aria2 密钥通过环境变量配置，不要写死在代码里

## 🐛 常见问题

**Q：插件加载失败，报 `no attribute 'event_type'`？**
A：AstrBot API 版本问题，用 `@filter.event_message_type(EventMessageType.ALL)`，并从 `astrbot.core.star.filter.event_message_type` 导入 EventMessageType。

**Q：转发文件后没反应/报 `attribute name must be string`？**
A：telegram.Message 是对象不是字典，用 `getattr(msg, k, None)` 访问属性，别用 `msg[k]`。

**Q：提交下载失败，报 `All connection attempts failed`？**
A：AstrBot 容器内 127.0.0.1 连不到 Aria2。确认 astrbot 和 aria2 在同一网络，aria2_rpc 用容器名。

**Q：插件异常会影响聊天吗？**
A：不会。AstrBot 有插件异常隔离，插件报错只影响该消息，可随时在 WebUI 禁用插件。

## 📄 License

MIT

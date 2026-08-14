from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.star.filter.event_message_type import EventMessageType
from astrbot.api.star import Context, Star, register

import json
import os
import httpx

@register("tg_download", "小狐狐", "TG 文件自动下载到服务器", "1.2.0")
class TgDownloadPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context, config)
        # Telegram API（默认官方地址，可配代理：环境变量 TG_API_BASE）
        self.api_base = os.environ.get("TG_API_BASE", "https://api.telegram.org/bot")
        self.bot_token = os.environ.get("TG_BOT_TOKEN", "")
        self.file_base = os.environ.get("TG_FILE_BASE", "https://api.telegram.org/file/bot")
        # Aria2（通过 Docker 网络用容器名访问；密钥必填，无默认值）
        self.aria2_rpc = os.environ.get("ARIA2_RPC", "http://aria2:6800/jsonrpc")
        self.aria2_secret = os.environ.get("ARIA2_SECRET", "")
        # 下载目录
        self.download_dir = "/downloads"
        # TG Bot API 大小限制
        self.max_size = 20 * 1024 * 1024
        # 询问上限：20MB~2GB 询问，>2GB 直接提示电脑下载
        self.ask_max = 2 * 1024 * 1024 * 1024
        # 待询问文件：{会话标识: 文件信息}（单文件场景用列表即可）
        self.pending = []
        # 分类规则：图片/音频/视频 三组，其余全部进「其他」
        self.CATEGORY_DIRS = {
            "图片": (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"),
            "音频": (".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".wma", ".opus"),
            "视频": (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"),
        }

    def _classify_dir(self, fname):
        """按扩展名分类：图片/音频/视频/其他"""
        ext = os.path.splitext(fname)[1].lower()
        for cat, exts in self.CATEGORY_DIRS.items():
            if ext in exts:
                return cat
        return "其他"

    def _ensure_dir(self, cat):
        """确保分类子目录存在并放开写权限（aria2 以 nobody 运行）"""
        d = os.path.join(self.download_dir, cat)
        os.makedirs(d, exist_ok=True)
        os.chmod(d, 0o777)
        return d

    def _extract_file(self, msg):
        """从 TG 消息里提取文件：返回 (file_id, filename, filesize) 或 None"""
        for k in ("document", "video", "audio", "video_note"):
            obj = getattr(msg, k, None)
            if obj is not None:
                if k == "video_note":
                    return obj.file_id, "video_note.mp4", obj.file_size or 0
                return obj.file_id, (obj.file_name or f"{k}.dat"), obj.file_size or 0
        photo = getattr(msg, "photo", None)
        if photo:
            obj = photo[-1]
            return obj.file_id, f"photo_{obj.file_unique_id}.jpg", obj.file_size or 0
        return None

    async def _tg_get_file(self, file_id: str):
        """调 getFile 拿文件路径"""
        url = f"{self.api_base}{self.bot_token}/getFile"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params={"file_id": file_id}, timeout=15)
                data = resp.json()
                if data.get("ok"):
                    return data["result"].get("file_path")
            except Exception as e:
                print(f"[tg_download] getFile 失败: {e}")
        return None

    async def _aria2_add(self, url: str, filename: str, dir_path: str = None):
        """提交 Aria2 下载任务（dir_path 为空则用默认下载目录）"""
        payload = {
            "jsonrpc": "2.0",
            "id": "tgdl",
            "method": "aria2.addUri",
            "params": [
                f"token:{self.aria2_secret}",
                [url],
                {"dir": dir_path or self.download_dir, "out": filename},
            ],
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(self.aria2_rpc, json=payload, timeout=30)
                return resp.json()
            except Exception as e:
                print(f"[tg_download] Aria2 提交失败: {e}")
                return {"error": str(e)}

    @filter.event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        # 拿原始消息
        message_obj = getattr(event, "message_obj", None)
        raw = getattr(message_obj, "raw_message", None) if message_obj else None
        if raw is None:
            return
        # 只处理 Telegram 平台：TG 的 raw_message 是 telegram.Update 对象
        if isinstance(raw, dict):
            return
        msg = getattr(raw, "message", None)
        if msg is None:
            return

        # ===== 先处理主人对询问的回复（本地/服务器）=====
        text = (msg.text or "").strip() if getattr(msg, "text", None) else ""
        if text in ("本地", "服务器") and self.pending:
            item = self.pending.pop(0)
            fname = item.get("fname", "")
            fsize = item.get("fsize", 0)
            size_mb = fsize / 1024 / 1024
            if text == "服务器":
                yield event.plain_result(
                    f"✅ 收到，{fname}（{size_mb:.1f}MB）将保存到【服务器】\n"
                    f"电脑端检测到文件后会自动上传到 Alist「下载」文件夹~"
                )
            else:
                yield event.plain_result(
                    f"✅ 收到，{fname}（{size_mb:.1f}MB）将保存到【电脑本地】\n"
                    f"电脑端会保留该文件~"
                )
            return

        # ===== 提取文件 =====
        result = self._extract_file(msg)
        if result is None:
            return  # 不是文件消息，交给 AI 处理
        file_id, fname, fsize = result

        # ===== 大小判断 =====
        if fsize > self.ask_max:
            # >2GB：直接提示电脑下载
            yield event.plain_result(
                f"📦 收到文件：{fname}（{fsize/1024/1024:.1f}MB）\n"
                f"⚠️ 文件超大（>2GB），电脑端将直接下载保存到本地~"
            )
            return

        if fsize > self.max_size:
            # 20MB~2GB：询问主人
            self.pending.append({"fname": fname, "fsize": fsize, "file_id": file_id})
            yield event.plain_result(
                f"📦 收到文件：{fname}（{fsize/1024/1024:.1f}MB）\n"
                f"❓ 保存到【本地】还是【服务器】？\n"
                f"（回复 本地 或 服务器；1 分钟不回复默认保存到服务器）"
            )
            return

        # ≤20MB：自动下载（按分类子目录）
        cat = self._classify_dir(fname)
        dir_path = self._ensure_dir(cat)
        yield event.plain_result(f"📥 收到文件：{fname}（{fsize/1024:.0f}KB），开始下载到【{cat}】~")

        # 拿直链
        file_path = await self._tg_get_file(file_id)
        if not file_path:
            yield event.plain_result("❌ 获取下载链接失败，请重试~")
            return

        dl_url = f"{self.file_base}{self.bot_token}/{file_path}"
        result = await self._aria2_add(dl_url, fname, dir_path)
        if result.get("result"):
            yield event.plain_result(f"✅ 已提交下载：{fname}，完成后出现在 Alist「下载/{cat}」文件夹~")
        else:
            yield event.plain_result(f"❌ 提交下载失败：{result}")

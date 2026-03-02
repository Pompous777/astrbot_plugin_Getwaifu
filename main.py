import asyncio
import json
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


WAIFU_IM_URL = "https://api.waifu.im/search?included_tags=waifu&is_nsfw=false"
NEKOS_BEST_URL = "https://nekos.best/api/v2/waifu"
CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_CLEANUP_INTERVAL_SECONDS = 10 * 60

COMMAND_TO_CATEGORY = {
    "抽老婆": "waifu",
    "抽猫娘": "neko",
    "抽忍野忍": "shinobu",
    "抽惠惠": "megumin",
    "抽欺负": "bully",
    "抽贴贴": "cuddle",
    "抽哭哭": "cry",
    "抽抱抱": "hug",
    "抽嗷呜": "awoo",
    "抽亲亲": "kiss",
    "抽舔舔": "lick",
    "抽摸摸": "pat",
    "抽得意": "smug",
    "抽敲头": "bonk",
    "抽丢飞": "yeet",
    "抽脸红": "blush",
    "抽微笑": "smile",
    "抽挥手": "wave",
    "抽击掌": "highfive",
    "抽牵手": "handhold",
    "抽吃吃": "nom",
    "抽咬咬": "bite",
    "抽飞扑": "glomp",
    "抽巴掌": "slap",
    "抽处决": "kill",
    "抽飞踢": "kick",
    "抽开心": "happy",
    "抽眨眼": "wink",
    "抽戳戳": "poke",
    "抽跳舞": "dance",
    "抽嫌弃": "cringe",
}

CATEGORY_TO_NAME = {
    "waifu": "老婆",
    "neko": "猫娘",
    "shinobu": "忍野忍",
    "megumin": "惠惠",
    "bully": "欺负",
    "cuddle": "贴贴",
    "cry": "哭哭",
    "hug": "抱抱",
    "awoo": "嗷呜",
    "kiss": "亲亲",
    "lick": "舔舔",
    "pat": "摸摸",
    "smug": "得意",
    "bonk": "敲头",
    "yeet": "丢飞",
    "blush": "脸红",
    "smile": "微笑",
    "wave": "挥手",
    "highfive": "击掌",
    "handhold": "牵手",
    "nom": "吃吃",
    "bite": "咬咬",
    "glomp": "飞扑",
    "slap": "巴掌",
    "kill": "处决",
    "kick": "飞踢",
    "happy": "开心",
    "wink": "眨眼",
    "poke": "戳戳",
    "dance": "跳舞",
    "cringe": "嫌弃",
}

COMMAND_ALIASES = (
    {cmd for cmd in COMMAND_TO_CATEGORY.keys() if cmd != "抽老婆"}
    | {f"/{cmd}" for cmd in COMMAND_TO_CATEGORY.keys()}
)


@register("Getwaifu", "SleepIsAVerb", "@机器人并发送抽老婆时返回 SFW 图片", "1.1.1")
class GetWaifuPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._cache_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_Getwaifu"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_cache_cleanup_at = 0.0
        self._recent_event_keys: dict[str, float] = {}
        self._event_dedupe_ttl_seconds = 8.0

    @staticmethod
    def _to_int(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_bot_id(self, event: AstrMessageEvent) -> int | None:
        bot = getattr(event, "bot", None)
        msg_obj = getattr(event, "message_obj", None)
        candidates = [
            getattr(bot, "self_id", None),
            getattr(msg_obj, "self_id", None),
            getattr(event, "self_id", None),
        ]
        for candidate in candidates:
            value = self._to_int(candidate)
            if value:
                return value
        return None

    def _is_at_bot(self, event: AstrMessageEvent) -> bool:
        at_ids: set[int] = set()
        for seg in event.get_messages():
            qq = self._to_int(getattr(seg, "qq", None))
            if qq:
                at_ids.add(qq)

        if not at_ids:
            return False

        bot_id = self._get_bot_id(event)
        if bot_id is None:
            return True
        return bot_id in at_ids

    def _event_key(self, event: AstrMessageEvent) -> str | None:
        msg_obj = getattr(event, "message_obj", None)
        candidates = [
            getattr(msg_obj, "message_id", None),
            getattr(event, "message_id", None),
            getattr(msg_obj, "id", None),
            getattr(event, "id", None),
        ]
        for candidate in candidates:
            if candidate is None:
                continue
            text = str(candidate).strip()
            if text:
                return text
        return None

    def _is_duplicate_event(self, event: AstrMessageEvent) -> bool:
        event_key = self._event_key(event)
        if not event_key:
            return False

        now = time.time()
        expire_before = now - self._event_dedupe_ttl_seconds
        self._recent_event_keys = {
            key: ts for key, ts in self._recent_event_keys.items() if ts >= expire_before
        }

        if event_key in self._recent_event_keys:
            return True

        self._recent_event_keys[event_key] = now
        return False

    @staticmethod
    def _http_get_json(url: str) -> dict:
        req = Request(url, headers={"User-Agent": "astrbot-plugin-getwaifu/1.0"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _pick_category_from_text(message: str) -> str:
        text = (message or "").strip()
        for command in sorted(COMMAND_TO_CATEGORY.keys(), key=len, reverse=True):
            if command in text:
                return COMMAND_TO_CATEGORY[command]
        return "waifu"

    @staticmethod
    def _valid_image_url(url: str) -> bool:
        text = (url or "").strip()
        return text.startswith("http://") or text.startswith("https://")

    def _fetch_waifu_url(self, category: str) -> str:
        errors: list[str] = []

        try:
            data = self._http_get_json(f"https://api.waifu.pics/sfw/{category}")
            image_url = str(data.get("url", "")).strip()
            if self._valid_image_url(image_url):
                return image_url
            errors.append("waifu.pics: invalid url")
        except Exception as exc:
            errors.append(f"waifu.pics: {exc}")

        if category != "waifu":
            raise ValueError("all endpoints failed: " + " | ".join(errors))

        try:
            data = self._http_get_json(WAIFU_IM_URL)
            images = data.get("images") or []
            if isinstance(images, list) and images:
                image_url = str((images[0] or {}).get("url", "")).strip()
                if self._valid_image_url(image_url):
                    return image_url
            errors.append("waifu.im: invalid response")
        except Exception as exc:
            errors.append(f"waifu.im: {exc}")

        try:
            data = self._http_get_json(NEKOS_BEST_URL)
            results = data.get("results") or []
            if isinstance(results, list) and results:
                image_url = str((results[0] or {}).get("url", "")).strip()
                if self._valid_image_url(image_url):
                    return image_url
            errors.append("nekos.best: invalid response")
        except Exception as exc:
            errors.append(f"nekos.best: {exc}")

        raise ValueError("all waifu endpoints failed: " + " | ".join(errors))

    @staticmethod
    def _infer_suffix(url: str, content_type: str | None) -> str:
        path = urlparse(url).path
        suffix = Path(path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return suffix

        ctype = (content_type or "").lower().split(";")[0].strip()
        if ctype == "image/png":
            return ".png"
        if ctype == "image/webp":
            return ".webp"
        if ctype == "image/gif":
            return ".gif"
        return ".jpg"

    def _download_image_to_cache(self, image_url: str) -> str:
        req = Request(image_url, headers={"User-Agent": "astrbot-plugin-getwaifu/1.0"})
        with urlopen(req, timeout=20) as resp:
            image_bytes = resp.read()
            suffix = self._infer_suffix(image_url, resp.headers.get("Content-Type"))

        filename = f"waifu_{int(time.time() * 1000)}{suffix}"
        save_path = self._cache_dir / filename
        save_path.write_bytes(image_bytes)
        return str(save_path)

    def _cleanup_cache_files(self, force: bool = False) -> None:
        now = time.time()
        if not force and (now - self._last_cache_cleanup_at) < CACHE_CLEANUP_INTERVAL_SECONDS:
            return

        self._last_cache_cleanup_at = now
        expire_before = now - CACHE_TTL_SECONDS

        for file_path in self._cache_dir.glob("waifu_*"):
            if not file_path.is_file():
                continue
            try:
                if file_path.stat().st_mtime < expire_before:
                    file_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("cleanup cache file failed: %s, file=%s", exc, file_path)

    def _fetch_and_cache_waifu_image(self, category: str) -> tuple[str, str]:
        self._cleanup_cache_files()
        image_url = self._fetch_waifu_url(category)
        image_path = self._download_image_to_cache(image_url)
        self._cleanup_cache_files()
        return image_path, image_url

    @filter.command("抽老婆", alias=COMMAND_ALIASES)
    async def draw_sfw_waifu(self, event: AstrMessageEvent):
        """@机器人并发送 SFW 抽卡指令时，返回对应分类图片。"""
        if not self._is_at_bot(event):
            return

        event.stop_event()

        if self._is_duplicate_event(event):
            logger.info("skip duplicate draw event")
            return

        category = self._pick_category_from_text(event.message_str)

        try:
            image_path, image_url = await asyncio.to_thread(self._fetch_and_cache_waifu_image, category)
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Get waifu failed: %s", exc)
            yield event.plain_result("抽老婆失败了，接口当前不可达（可能是 DNS/网络限制），请稍后再试。")
            return
        except Exception as exc:
            logger.exception("Unexpected error while drawing waifu: %s", exc)
            yield event.plain_result("抽老婆失败了，发生了未知错误。")
            return

        user_name = event.get_sender_name()
        category_name = CATEGORY_TO_NAME.get(category, category)
        yield event.plain_result(f"{user_name} 抽到了 {category_name}！")
        try:
            yield event.image_result(image_path)
        except Exception as exc:
            logger.warning("send local image failed: %s, fallback to remote url", exc)
            yield event.image_result(image_url)

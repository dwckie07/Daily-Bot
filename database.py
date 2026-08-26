import os
import json
import urllib.request
import asyncio
import discord
from discord.ext import tasks

GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# ==================== BỘ NHỚ TẠM (RAM CACHE) ====================
_DATA_CACHE = None
_ALLOW_CACHE = None
_SEAL_CACHE = None
_KIKI_CACHE = None

_DIRTY = {
    "user_data": False,
    "channel_allow": False,
    "seal_data": False,
    "kiki_data": False
}

_AUTO_SAVE_TASK_STARTED = False

def _fetch_gist_file_sync(filename):
    if not GITHUB_TOKEN or not GIST_ID:
        return None
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "DiscordBot"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            files = result.get("files", {})
            file_obj = files.get(filename)
            
            if file_obj and "content" in file_obj:
                content = file_obj["content"]
                return json.loads(content) if content.strip() else None
    except Exception as e:
        print(f"⚠️ Lỗi đọc Gist [{filename}]: {e}")
    return None

def _save_gist_files_sync(files_payload):
    if not GITHUB_TOKEN or not GIST_ID or not files_payload:
        return

    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot"
    }
    payload = json.dumps({"files": files_payload}).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(req):
            pass
    except Exception as e:
        print(f"⚠️ Lỗi lưu Gist: {e}")

# ==================== KHỞI TẠO NẠP TRƯỚC TOÀN BỘ CACHE ====================
async def preload_all_data():
    global _DATA_CACHE, _ALLOW_CACHE, _SEAL_CACHE, _KIKI_CACHE
    _DATA_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "user_data.json") or {}
    _ALLOW_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "channel_allow.json") or {}
    _SEAL_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "seal_data.json") or []
    _KIKI_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "kiki_data.json") or []
    print("✅ Đã nạp thành công toàn bộ Gist Data vào RAM Cache!")

def flush_all_caches_sync():
    """Lưu khẩn cấp toàn bộ dữ liệu RAM xuống Gist khi bot ngắt kết nối"""
    files_payload = {}
    if _DIRTY["user_data"] and _DATA_CACHE is not None:
        files_payload["user_data.json"] = {"content": json.dumps(_DATA_CACHE, ensure_ascii=False, indent=4)}
    if _DIRTY["channel_allow"] and _ALLOW_CACHE is not None:
        files_payload["channel_allow.json"] = {"content": json.dumps(_ALLOW_CACHE, ensure_ascii=False, indent=4)}
    if _DIRTY["seal_data"] and _SEAL_CACHE is not None:
        files_payload["seal_data.json"] = {"content": json.dumps(_SEAL_CACHE, ensure_ascii=False, indent=4)}
    if _DIRTY["kiki_data"] and _KIKI_CACHE is not None:
        files_payload["kiki_data.json"] = {"content": json.dumps(_KIKI_CACHE, ensure_ascii=False, indent=4)}

    if files_payload:
        _save_gist_files_sync(files_payload)
        for key in _DIRTY:
            _DIRTY[key] = False

# ==================== QUẢN LÝ DỮ LIỆU USER ====================
async def load_data():
    global _DATA_CACHE
    if _DATA_CACHE is None:
        _DATA_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "user_data.json") or {}
    return _DATA_CACHE

async def save_data(data):
    global _DATA_CACHE
    _DATA_CACHE = data
    _DIRTY["user_data"] = True

# ==================== VÒNG LẶP TỰ ĐỘNG LƯU (15s/lần) ====================
@tasks.loop(seconds=15)
async def _auto_save_loop():
    await asyncio.to_thread(flush_all_caches_sync)

def start_auto_save_loop(bot=None):
    global _AUTO_SAVE_TASK_STARTED
    if not _AUTO_SAVE_TASK_STARTED:
        _auto_save_loop.start()
        _AUTO_SAVE_TASK_STARTED = True

# ==================== QUẢN LÝ KÊNH ĐƯỢC PHÉP ====================
async def load_allowed_channels(bot=None):
    global _ALLOW_CACHE
    if _ALLOW_CACHE is None:
        _ALLOW_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "channel_allow.json") or {}
    
    data = _ALLOW_CACHE
    if bot and data:
        cleaned_data = {}
        has_deleted = False

        for cid_str, perms in list(data.items()):
            if not cid_str.isdigit():
                has_deleted = True
                continue

            cid = int(cid_str)
            channel = bot.get_channel(cid)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(cid)
                except (discord.NotFound, discord.HTTPException):
                    channel = None

            if channel is not None:
                cleaned_data[cid_str] = perms
            else:
                has_deleted = True

        if has_deleted:
            await save_allowed_channels(cleaned_data)
            return cleaned_data

    return data

async def save_allowed_channels(data):
    global _ALLOW_CACHE
    _ALLOW_CACHE = data
    _DIRTY["channel_allow"] = True

# ==================== QUẢN LÝ DỮ LIỆU HẢI CẨU (SEAL) ====================
async def load_seal_data():
    global _SEAL_CACHE
    if _SEAL_CACHE is None:
        _SEAL_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "seal_data.json") or []
    return _SEAL_CACHE

async def save_seal_data(data):
    global _SEAL_CACHE
    _SEAL_CACHE = data
    _DIRTY["seal_data"] = True

# ==================== QUẢN LÝ DỮ LIỆU KIKI ====================
async def load_kiki_data():
    global _KIKI_CACHE
    if _KIKI_CACHE is None:
        _KIKI_CACHE = await asyncio.to_thread(_fetch_gist_file_sync, "kiki_data.json") or []
    return _KIKI_CACHE

async def save_kiki_data(data):
    global _KIKI_CACHE
    _KIKI_CACHE = data
    _DIRTY["kiki_data"] = True

# ==================== TIỆN ÍCH HELPER ====================
def get_streak_text(streak_days: int) -> str:
    if streak_days < 3:
        return f"🧊 {max(0, streak_days)} ngày"
    return f"🔥 {streak_days} ngày"

def format_points(points: int, shorten: bool = False) -> str:
    if shorten:
        if points >= 1_000_000:
            val = round(points / 1_000_000, 1)
            return f"{val:.1f}M".replace(".", ",") if val % 1 != 0 else f"{int(val)}M"
        elif points >= 1_000:
            val = round(points / 1_000, 1)
            return f"{val:.1f}k".replace(".", ",") if val % 1 != 0 else f"{int(val)}k"
        return str(points)
    return f"{points:,}".replace(",", ".")
        

import os
import json
import aiohttp
import asyncio
from discord.ext import tasks

# ================= CẤU HÌNH GITHUB GIST =================
# Nên dùng biến môi trường (Environment Variables) để bảo mật Token
GIST_ID = os.environ.get("GIST_ID", "ĐIỀN_GIST_ID_CỦA_BẠN_VÀO_ĐÂY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "ĐIỀN_TOKEN_CỦA_BẠN_VÀO_ĐÂY")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}
GIST_URL = f"https://api.github.com/gists/{GIST_ID}"

# ================= QUẢN LÝ BỘ NHỚ ĐỆM (CACHE) =================
_DATA_CACHE = None
_CHANNELS_CACHE = None
_SEALS_CACHE = None  # Thêm cache cho hải cẩu
_IS_DIRTY = False  # Cờ đánh dấu khi có thay đổi dữ liệu

# ================= CÁC HÀM HỖ TRỢ HIỂN THỊ =================
def format_points(points: int) -> str:
    """Định dạng số điểm (vd: 1000 -> 1,000)"""
    return f"{points:,}"

def get_streak_text(streak: int) -> str:
    """Hiển thị chuỗi streak kèm biểu tượng"""
    return f"{streak} ngày {'🔥' if streak >= 3 else '🌱'}"

# ================= TƯƠNG TÁC API GITHUB =================
async def _fetch_gist():
    """Tải dữ liệu từ Gist bằng aiohttp"""
    async with aiohttp.ClientSession() as session:
        async with session.get(GIST_URL, headers=HEADERS) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Lỗi tải Gist: {response.status}")
                return None

async def _update_gist(files_data: dict):
    """Cập nhật dữ liệu lên Gist"""
    payload = {"files": files_data}
    async with aiohttp.ClientSession() as session:
        async with session.patch(GIST_URL, headers=HEADERS, json=payload) as response:
            if response.status != 200:
                print(f"Lỗi lưu Gist: {response.status}")

# ================= QUẢN LÝ DỮ LIỆU NGƯỜI DÙNG =================
async def load_data() -> dict:
    global _DATA_CACHE
    if _DATA_CACHE is not None:
        return _DATA_CACHE

    gist_data = await _fetch_gist()
    if gist_data and "files" in gist_data and "data.json" in gist_data["files"]:
        content = gist_data["files"]["data.json"]["content"]
        _DATA_CACHE = json.loads(content)
    else:
        _DATA_CACHE = {}
    return _DATA_CACHE

async def save_data(data: dict):
    """Cập nhật cache và bật cờ thông báo có thay đổi"""
    global _DATA_CACHE, _IS_DIRTY
    _DATA_CACHE = data
    _IS_DIRTY = True

# ================= QUẢN LÝ PHÂN QUYỀN KÊNH =================
async def load_allowed_channels(bot=None) -> dict:
    global _CHANNELS_CACHE
    if _CHANNELS_CACHE is not None:
        return _CHANNELS_CACHE

    gist_data = await _fetch_gist()
    if gist_data and "files" in gist_data and "channels.json" in gist_data["files"]:
        content = gist_data["files"]["channels.json"]["content"]
        _CHANNELS_CACHE = json.loads(content)
    else:
        _CHANNELS_CACHE = {}
    return _CHANNELS_CACHE

async def save_allowed_channels(data: dict):
    global _CHANNELS_CACHE, _IS_DIRTY
    _CHANNELS_CACHE = data
    _IS_DIRTY = True

# ================= QUẢN LÝ DỮ LIỆU SEALS =================
async def load_seals() -> dict:
    global _SEALS_CACHE
    if _SEALS_CACHE is not None:
        return _SEALS_CACHE

    gist_data = await _fetch_gist()
    if gist_data and "files" in gist_data and "seals.json" in gist_data["files"]:
        _SEALS_CACHE = json.loads(gist_data["files"]["seals.json"]["content"])
    else:
        _SEALS_CACHE = {}
    return _SEALS_CACHE

async def save_seals(data: dict):
    global _SEALS_CACHE, _IS_DIRTY
    _SEALS_CACHE = data
    _IS_DIRTY = True

# ================= VÒNG LẶP AUTO-SAVE =================
@tasks.loop(seconds=15)
async def auto_save_loop():
    """Tự động lưu dữ liệu lên Gist mỗi 15 giây nếu có thay đổi"""
    global _IS_DIRTY
    if _IS_DIRTY:
        files_payload = {}
        if _DATA_CACHE is not None:
            files_payload["data.json"] = {"content": json.dumps(_DATA_CACHE, indent=4)}
        if _CHANNELS_CACHE is not None:
            files_payload["channels.json"] = {"content": json.dumps(_CHANNELS_CACHE, indent=4)}
        if _SEALS_CACHE is not None:
            files_payload["seals.json"] = {"content": json.dumps(_SEALS_CACHE, indent=4)}
            
        if files_payload:
            await _update_gist(files_payload)
            _IS_DIRTY = False

@auto_save_loop.before_loop
async def before_auto_save():
    # Đợi bot sẵn sàng trước khi chạy vòng lặp
    await asyncio.sleep(5)
    

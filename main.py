import os
import signal
import sys
import asyncio
import discord
from discord.ext import commands
from keep_alive import keep_alive
from database import load_allowed_channels, start_auto_save_loop, preload_all_data, flush_all_caches_sync

BOT_TOKEN = os.environ.get("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=["k.", "K."], 
    intents=intents, 
    case_insensitive=True,
    help_command=None
)

# ==================== Graceful Shutdown (Bắt tín hiệu Render tắt/restart) ====================
def handle_shutdown(sig, frame):
    print("⚠️ Phát hiện tín hiệu ngắt/restart từ Render! Tiến hành xả dữ liệu khẩn cấp...")
    flush_all_caches_sync()
    print("✅ Đã lưu toàn bộ RAM Cache xuống Gist an toàn.")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

@bot.check
async def restrict_channel(ctx):
    if ctx.guild and ctx.author.guild_permissions.administrator: 
        return True
    allowed_channels = await load_allowed_channels()
    ch_perms = allowed_channels.get(str(ctx.channel.id), {})
    if isinstance(ch_perms, bool):
        return ch_perms
    return ch_perms.get("command", False) is True

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Bớt spam lại nha! Thử lại sau **{error.retry_after:.1f}s**.", delete_after=3)
    elif isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        pass
    else:
        print(f"❌ Lỗi thực thi lệnh: {error}")

@bot.event
async def on_ready():
    await preload_all_data()
    start_auto_save_loop(bot)
    print(f"🤖 Bot {bot.user.name} đã kết nối thành công và sẵn sàng xử lý!")

async def main():
    keep_alive()
    async with bot:
        await bot.load_extension("build.set_up")
        await bot.load_extension("build.check")
        await bot.load_extension("build.member")
        await bot.load_extension("build.rank")
        await bot.load_extension("build.admin")
        await bot.load_extension("build.seal")
        await bot.load_extension("build.kiki")
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
    

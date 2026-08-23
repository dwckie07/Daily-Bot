import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import auto_save_loop
from keep_alive import keep_alive  # Tích hợp web server giữ cho Render luôn online

load_dotenv()
# Nhận linh hoạt tên biến môi trường BOT_TOKEN hoặc DISCORD_TOKEN
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class DailyQuestBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("k.", "K."),
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Quét tự động tất cả các file .py trong thư mục build/
        build_dir = "build"
        if os.path.exists(build_dir):
            for root, _, files in os.walk(build_dir):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        # Chuyển đường dẫn tệp thành định dạng module của Python (ví dụ: build.admin)
                        relative_path = os.path.relpath(os.path.join(root, file), ".")
                        module_name = relative_path[:-3].replace(os.sep, ".")
                        
                        try:
                            await self.load_extension(module_name)
                            print(f"✅ Đã tải Module: {module_name}")
                        except Exception as e:
                            print(f"❌ Lỗi tải Module {module_name}: {e}")

        # Khởi động vòng lặp tự động lưu
        if not auto_save_loop.is_running():
            auto_save_loop.start()
            print("🔄 Đã khởi động vòng lặp Auto-save dữ liệu.")

    # Bắt lỗi toàn cục cho tất cả các lệnh
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ KHÔNG CÓ QUYỀN", description="Bạn cần quyền **Administrator** để dùng lệnh này!", color=discord.Color.red())
            await ctx.send(embed=embed)
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            embed = discord.Embed(title="⚠️ SAI CÚ PHÁP", description=f"Vui lòng kiểm tra lại cú pháp lệnh `{ctx.command.name}`.", color=discord.Color.gold())
            await ctx.send(embed=embed)

    async def on_ready(self):
        print("-" * 30)
        print(f"🚀 Bot đã online: {self.user.display_name} (ID: {self.user.id})")
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.listening, name="k.help | Daily Quest")
        )

if __name__ == "__main__":
    keep_alive()  # Mở port cho Render nhận diện dịch vụ thành công
    bot = DailyQuestBot()
    bot.run(TOKEN)

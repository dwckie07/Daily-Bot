import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone, time
from database import load_data, save_data, load_allowed_channels, format_points, get_streak_text

def get_vn_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam (UTC+7)"""
    return datetime.now(timezone.utc) + timedelta(hours=7)

class CheckCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_reset_task.start()

    def cog_unload(self):
        self.daily_reset_task.cancel()

    # ================= 1. XỬ LÝ NHẬN NHIỆM VỤ =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Kiểm tra xem kênh có được phép gửi ảnh điểm danh không
        allowed_channels = await load_allowed_channels()
        channel_id_str = str(message.channel.id)
        if channel_id_str not in allowed_channels or not allowed_channels[channel_id_str].get("image"):
            return

        # Kiểm tra tin nhắn có đính kèm ảnh hoặc chứa link không
        has_media = len(message.attachments) > 0 or "http://" in message.content or "https://" in message.content
        if not has_media:
            return

        # Xử lý dữ liệu
        data = await load_data()
        user_id = str(message.author.id)
        user_info = data.setdefault(user_id, {"points": 0, "last_date": "", "streak": 0, "total_quests": 0, "checkin_today": 0})
        
        today = str(get_vn_time().date())

        # Chặn spam nếu đã điểm danh
        if user_info.get("last_date") == today and user_info.get("checkin_today", 0) > 0:
            await message.add_reaction("❌")
            msg = await message.reply(f"⚠️ {message.author.mention}, bạn đã hoàn thành nhiệm vụ hôm nay rồi!", delete_after=10)
            return

        # Tính toán Streak & Điểm
        yesterday = str(get_vn_time().date() - timedelta(days=1))
        if user_info.get("last_date") == yesterday:
            user_info["streak"] += 1
        elif user_info.get("last_date") != today:
            user_info["streak"] = 1 # Bắt đầu chuỗi mới

        streak = user_info["streak"]
        bonus_points = 5 if streak >= 3 else 0
        total_points = 100 + bonus_points

        # Cập nhật thông số
        user_info["points"] += total_points
        user_info["total_quests"] += 1
        user_info["last_date"] = today
        user_info["checkin_today"] = 1
        
        await save_data(data)

        # Trả kết quả
        await message.add_reaction("✅")
        await message.add_reaction("🔄")
        if bonus_points > 0:
            await message.add_reaction("🔥")

        bonus_text = " *(+5 streak)*" if bonus_points > 0 else ""
        embed = discord.Embed(
            title="✅ ĐIỂM DANH THÀNH CÔNG",
            description=f"Chúc mừng {message.author.mention} đã hoàn thành nhiệm vụ!\n**+{total_points} KiPoints**{bonus_text}",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Tổng điểm", value=f"**{format_points(user_info['points'])}** KP")
        embed.add_field(name="🔥 Chuỗi ngày", value=f"**{get_streak_text(streak)}**")
        await message.reply(embed=embed)

    # ================= 2. ADMIN CLICK NÚT 🔄 ĐỂ HỦY =================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or str(payload.emoji) != "🔄":
            return
            
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        
        # Chỉ Admin mới được dùng nút này
        if not member.guild_permissions.administrator:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        # Giả lập lại lệnh k.deny
        ctx = await self.bot.get_context(message)
        admin_cog = self.bot.get_cog("AdminCog")
        if admin_cog:
            await admin_cog.refund_user(ctx, message.author)

    # ================= 3. RESET STREAK TỰ ĐỘNG =================
    # Chạy vào 00:00 giờ VN mỗi ngày (17:00 UTC)
    @tasks.loop(time=time(hour=17, minute=0, tzinfo=timezone.utc))
    async def daily_reset_task(self):
        data = await load_data()
        today = str(get_vn_time().date())
        changed = False

        for uid, info in data.items():
            # Nếu hôm nay chưa điểm danh, cắt streak
            if info.get("last_date") != today:
                if info.get("streak", 0) > 0:
                    info["streak"] = 0
                    changed = True
            
            # Đặt lại trạng thái checkin trong ngày
            if info.get("checkin_today", 0) != 0:
                info["checkin_today"] = 0
                changed = True

        if changed:
            await save_data(data)

async def setup(bot):
    await bot.add_cog(CheckCog(bot))

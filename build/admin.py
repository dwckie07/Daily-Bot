import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from database import load_data, save_data, get_streak_text, format_points

# Mẫu dữ liệu mặc định
DEFAULT_USER_DATA = {"points": 0, "last_date": "", "streak": 0, "total_quests": 0, "checkin_today": 0}

def get_vn_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    return datetime.now(timezone.utc) + timedelta(hours=7)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= BẮT LỖI CHUNG CHO TOÀN BỘ LỆNH TRONG COG =================
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ KHÔNG CÓ QUYỀN", description="Bạn cần quyền **Administrator** để dùng lệnh này!", color=discord.Color.red())
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            embed = discord.Embed(title="⚠️ SAI CÚ PHÁP", description=f"Vui lòng xem lại cú pháp lệnh `{ctx.command.name}` hoặc gõ `k.help admin`.", color=discord.Color.gold())
        else:
            embed = discord.Embed(title="❌ LỖI HỆ THỐNG", description=f"`{error}`", color=discord.Color.red())
        await ctx.send(embed=embed)

    # ================= HÀM HỖ TRỢ XỬ LÝ DỮ LIỆU CƠ BẢN =================
    async def _update_stat(self, user_id: str, field: str, amount: int):
        data = await load_data()
        user_info = data.setdefault(user_id, DEFAULT_USER_DATA.copy())
        user_info[field] = max(0, user_info.get(field, 0) + amount)
        await save_data(data)
        return user_info

    # ================= CÁC LỆNH QUẢN TRỊ =================
    @commands.command(name="add")
    @commands.has_permissions(administrator=True)
    async def add_diem(self, ctx, member: discord.Member, amount: int):
        user_info = await self._update_stat(str(member.id), "points", amount)
        
        embed = discord.Embed(title="🔺 CỘNG KIPOINTS", description=f"Đã cộng **+{amount} KiPoints** cho {member.mention}!", color=discord.Color.green())
        embed.add_field(name="💰 Tổng KiPoints Mới", value=f"**{format_points(user_info['points'])}** KiPoints")
        embed.set_footer(text=f"Thực hiện bởi Admin: {ctx.author.display_name}")
        await ctx.send(embed=embed)

        if log_cog := self.bot.get_cog("LogCog"):
            await log_cog.log_add_points(target_id=member.id, points=amount, actor=ctx.author, reason="Lệnh k.add")

    @commands.command(name="remove", aliases=["rm"])
    @commands.has_permissions(administrator=True)
    async def remove_diem(self, ctx, member: discord.Member, amount: int):
        user_info = await self._update_stat(str(member.id), "points", -amount)
        
        embed = discord.Embed(title="🔻 TRỪ KIPOINTS", description=f"Đã trừ **-{amount} KiPoints** của {member.mention}!", color=discord.Color.red())
        embed.add_field(name="💰 Tổng KiPoints Còn Lại", value=f"**{format_points(user_info['points'])}** KiPoints")
        embed.set_footer(text=f"Thực hiện bởi Admin: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="addstreak", aliases=["adds"])
    @commands.has_permissions(administrator=True)
    async def add_streak(self, ctx, member: discord.Member, amount: int):
        data = await load_data()
        user_id = str(member.id)
        user_info = data.setdefault(user_id, DEFAULT_USER_DATA.copy())
        
        user_info["streak"] = max(0, user_info.get("streak", 0) + amount)
        
        # Chỉnh sửa last_date để bảo toàn streak cho ngày tiếp theo nếu chưa điểm danh hôm nay
        today = get_vn_time().date()
        if user_info.get("last_date") != str(today):
            user_info["last_date"] = str(today - timedelta(days=1))

        await save_data(data)
        
        embed = discord.Embed(title="🔥 CỘNG STREAK", description=f"Đã cộng **+{amount} ngày streak** cho {member.mention}!", color=discord.Color.green())
        embed.add_field(name="🔥 Chuỗi Streak Hiện Tại", value=f"**{get_streak_text(user_info['streak'])}**")
        embed.set_footer(text=f"Thực hiện bởi Admin: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="removestreak", aliases=["rms"])
    @commands.has_permissions(administrator=True)
    async def remove_streak(self, ctx, member: discord.Member, amount: int):
        user_info = await self._update_stat(str(member.id), "streak", -amount)
        
        embed = discord.Embed(title="🔻 TRỪ STREAK", description=f"Đã trừ **-{amount} ngày streak** của {member.mention}!", color=discord.Color.red())
        embed.add_field(name="🔥 Chuỗi Streak Còn Lại", value=f"**{get_streak_text(user_info['streak'])}**")
        embed.set_footer(text=f"Thực hiện bởi Admin: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="reset", aliases=["rs"])
    @commands.has_permissions(administrator=True)
    async def reset_user(self, ctx, target: str = None):
        if not target:
            embed = discord.Embed(title="⚠️ SAI CÚ PHÁP LỆNH RESET", description="• `k.reset @User`\n• `k.reset all`\n• `k.reset all_streak`", color=discord.Color.gold())
            return await ctx.send(embed=embed)

        data = await load_data()
        target_clean = target.lower()

        if target_clean == "all":
            if not data: return await ctx.send(embed=discord.Embed(title="📋 KHÔNG CÓ DỮ LIỆU", color=discord.Color.gold()))
            await save_data({})
            embed = discord.Embed(title="💥 RESET TOÀN BỘ THÀNH CÔNG", description="Dữ liệu của **TẤT CẢ** thành viên đã được đưa về 0.", color=discord.Color.red())
            return await ctx.send(embed=embed)

        if target_clean == "all_streak":
            if not data: return await ctx.send(embed=discord.Embed(title="📋 KHÔNG CÓ DỮ LIỆU", color=discord.Color.gold()))
            for uid in data: data[uid]["streak"] = 0
            await save_data(data)
            embed = discord.Embed(title="🔥 RESET STREAK TOÀN BỘ THÀNH CÔNG", description="Chuỗi Streak của **TẤT CẢ** thành viên đã được đưa về 0.", color=discord.Color.orange())
            return await ctx.send(embed=embed)

        try:
            member = await commands.MemberConverter().convert(ctx, target)
            if str(member.id) in data:
                del data[str(member.id)]
                await save_data(data)
                embed = discord.Embed(title="🔄 RESET DỮ LIỆU THÀNH CÔNG", description=f"Toàn bộ dữ liệu của {member.mention} đã đưa về 0.", color=discord.Color.red())
            else:
                embed = discord.Embed(title="⚠️ KHÔNG TÌM THẤY", description=f"{member.mention} chưa có dữ liệu.", color=discord.Color.gold())
            await ctx.send(embed=embed)
        except commands.BadArgument:
            await ctx.send(embed=discord.Embed(title="⚠️ LỖI", description="Vui lòng tag `@User`, nhập `all` hoặc `all_streak`!", color=discord.Color.gold()))

    @commands.command(name="deny", aliases=["dn"])
    @commands.has_permissions(administrator=True)
    async def refund_user(self, ctx, member: discord.Member):
        data = await load_data()
        user_info = data.get(str(member.id))
        today = get_vn_time().date()

        if not user_info or user_info.get("total_quests", 0) == 0 or user_info.get("last_date") != str(today):
            return await ctx.send(embed=discord.Embed(title="⚠️ KHÔNG THỂ HOÀN TRẢ", description=f"{member.mention} **chưa điểm danh ngày hôm nay**", color=discord.Color.gold()))

        current_streak = user_info.get("streak", 0)
        amount, bonus_msg = (105, " *(Bao gồm +5 streak)*") if current_streak >= 3 else (100, "")

        user_info["points"] = max(0, user_info.get("points", 0) - amount)
        user_info["total_quests"] = max(0, user_info.get("total_quests", 0) - 1)
        user_info["streak"] = max(0, current_streak - 1)
        user_info["last_date"] = str(today - timedelta(days=1))
        user_info["checkin_today"] = max(0, user_info.get("checkin_today", 0) - 1)

        await save_data(data)

        embed = discord.Embed(title="🔄 HOÀN TRẢ LƯỢT ĐIỂM DANH", description=f"📢 {member.mention}\n**Nhiệm vụ này đã kết thúc!\nHãy làm nhiệm vụ mới**", color=discord.Color.blue())
        embed.add_field(name="🔻 KiPoints Trừ", value=f"**-{amount}** KiPoints{bonus_msg}", inline=False)
        embed.add_field(name="💰 KiPoints Còn Lại", value=f"**{format_points(user_info['points'])}** KiPoints", inline=True)
        embed.add_field(name="🔥 Streak Khôi Phục", value=f"**{get_streak_text(user_info['streak'])}**", inline=True)
        await ctx.send(embed=embed)

        if log_cog := self.bot.get_cog("LogCog"):
            await log_cog.log_deny(target_id=member.id, actor=ctx.author, reason="Hoàn trả bằng k.deny")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))

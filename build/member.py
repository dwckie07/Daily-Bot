import discord
from discord.ext import commands
from database import load_allowed_channels

# Dữ liệu nội dung cho lệnh Help
HELP_DATA = {
    "member": {
        "title": "👤 NHÓM LỆNH THÀNH VIÊN (MEMBER)",
        "desc": "Các lệnh sử dụng cho tất cả thành viên trong máy chủ:",
        "color": discord.Color.green(),
        "commands": "- `help`: Xem hướng dẫn sử dụng lệnh.\n- `rule`: Xem quy định & cách tính điểm.\n- `profile @User`: Xem hồ sơ nhiệm vụ cá nhân.\n- `top <số trang>`: Xem bảng xếp hạng KiPoints.\n- `avatar @User`: Xem ảnh đại diện (avatar) chất lượng HD (4096px)."
    },
    "admin": {
        "title": "⚙️ NHÓM LỆNH QUẢN TRỊ (ADMIN)",
        "desc": "Nhóm lệnh quản trị điểm số & streak (Chỉ Admin).",
        "color": discord.Color.red(),
        "commands": "- `add @User <số KiPoints>`: Cộng KiPoints cho thành viên.\n- `remove @User <số KiPoints>`: Trừ KiPoints.\n- `addstreak @User <số ngày>`: Cộng chuỗi streak.\n- `removestreak @User <số ngày>`: Trừ chuỗi streak.\n- `deny @User`: Hủy kết quả điểm danh hôm nay.\n- `reset @User/all`: Đặt lại toàn bộ dữ liệu của 1 người hoặc tất cả."
    },
    "setup": {
        "title": "🛠️ NHÓM LỆNH CÀI ĐẶT (SET UP)",
        "desc": "Nhóm lệnh cài đặt phân quyền & kênh (Chỉ Admin).",
        "color": discord.Color.orange(),
        "commands": "- `allow <#kênh/ID> <image/command> <true/false>`: Quản lý quyền.\n- `allowlist`: Xem danh sách phân quyền hiện tại.\n- `lock`: Khóa kênh làm nhiệm vụ.\n- `unlock`: Mở khóa kênh làm nhiệm vụ."
    }
}

# Ánh xạ các từ viết tắt của lệnh help
HELP_ALIASES = {"mem": "member", "ad": "admin", "set up": "setup", "set_up": "setup"}

class MemberCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= BẮT LỖI CHUNG =================
    async def cog_command_error(self, ctx, error):
        embed = discord.Embed(title="❌ LỖI THỰC THI", description=f"`{error}`", color=discord.Color.red())
        await ctx.send(embed=embed)

    # ================= HELPER =================
    def _add_footer(self, embed, ctx):
        embed.set_footer(text=f"Yêu cầu bởi {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        return embed

    # ================= CÁC LỆNH =================
    @commands.command(name="avatar", aliases=["av"])
    async def avatar_command(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        avatar_url = target.display_avatar.with_size(4096).url

        embed = discord.Embed(
            title=f"🖼️ AVATAR CỦA {target.display_name.upper()}",
            description=f"🔗 [Nhấn vào đây để tải ảnh gốc HD]({avatar_url})",
            color=discord.Color.blue()
        )
        embed.set_image(url=avatar_url)
        await ctx.send(embed=self._add_footer(embed, ctx))

    @commands.command(name="rule", aliases=["r"])
    async def rule_command(self, ctx):
        allowed_data = await load_allowed_channels(self.bot)
        img_chs, cmd_chs = [], []

        if allowed_data:
            for cid, perms in allowed_data.items():
                if isinstance(perms, dict):
                    if perms.get("image"): img_chs.append(f"<#{cid}>")
                    if perms.get("command"): cmd_chs.append(f"<#{cid}>")
                elif isinstance(perms, bool) and perms:
                    cmd_chs.append(f"<#{cid}>")

        img_str = ", ".join(img_chs) if img_chs else "*kênh chưa được thiết lập*"
        cmd_str = ", ".join(cmd_chs) if cmd_chs else "*kênh chưa được thiết lập*"

        embed = discord.Embed(title="📜 QUY ĐỊNH & NỘI QUY ĐIỂM DANH", color=discord.Color.gold())
        embed.add_field(name="📖 1. Hình thức làm Daily Quest:", value=f"- Mỗi ngày **Ki Ki** sẽ đưa ra một nhiệm vụ.\n- Mọi người sẽ làm nhiệm vụ và gửi vào {img_str} để điểm danh.", inline=False)
        embed.add_field(name="📊 2. Cách tính điểm:", value="- Thả emoji: ✅ Hoàn thành | ❌ Đã làm | 🔥 Thưởng streak.\n- Hoàn thành nhiệm vụ: **+100 KiPoints**.\n- Đạt chuỗi streak **(≥ 3 ngày)**: **+5 KiPoints**.\n- Qua ngày mới bot sẽ khoá kênh kết thúc nhiệm vụ.", inline=False)
        embed.add_field(name="🚫 3. Về hành vi sai phạm:", value="- Làm sai nhiệm vụ / nội dung không phù hợp sẽ bị từ chối và yêu cầu làm lại.\n- Các nội dung phải theo luật của server.", inline=False)
        embed.add_field(name="📃 4. Về lệnh của bot:", value=f"- Bot dùng cú pháp `k.<lệnh>` / `K.<lệnh>`\n- Kênh được phép dùng lệnh: {cmd_str}\n- Nhập lệnh `help` để xem danh sách.", inline=False)
        
        await ctx.send(embed=self._add_footer(embed, ctx))

    @commands.command(name="help", aliases=["h"])
    async def help_command(self, ctx, *, group: str = None):
        if not group:
            embed = discord.Embed(
                title="📜 HƯỚNG DẪN SỬ DỤNG LỆNH (HELP)",
                description="Sử dụng cú pháp `k.help <nhóm lệnh>` để xem chi tiết danh sách lệnh.",
                color=discord.Color.blue()
            )
            embed.add_field(name="📂 Các nhóm lệnh khả dụng:", value="- `k.help member`: Lệnh cho thành viên.\n- `k.help admin`: Lệnh quản trị (Chỉ Admin).\n- `k.help set up`: Lệnh cài đặt (Chỉ Admin).", inline=False)
            return await ctx.send(embed=self._add_footer(embed, ctx))

        group_clean = group.lower().strip()
        # Ánh xạ alias (ví dụ: 'ad' -> 'admin')
        group_key = HELP_ALIASES.get(group_clean, group_clean)

        if group_key in HELP_DATA:
            data = HELP_DATA[group_key]
            embed = discord.Embed(title=data["title"], description=data["desc"], color=data["color"])
            embed.add_field(name="📌 Danh sách lệnh:", value=data["commands"], inline=False)
            await ctx.send(embed=self._add_footer(embed, ctx))
        else:
            embed = discord.Embed(title="⚠️ NHÓM LỆNH KHÔNG HỢP LỆ", description="Vui lòng chọn 1 trong các nhóm:\n• `k.help member`\n• `k.help admin`\n• `k.help setup`", color=discord.Color.gold())
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MemberCog(bot))
      

import discord
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from collections import OrderedDict
from database import load_data, format_points

# ================= CẤU HÌNH CACHE & FONT =================
MAX_AVATAR_CACHE = 50
AVATAR_CACHE = OrderedDict()

# Hàm helper để nạp Font (Thay đổi đường dẫn font của bạn ở đây)
def get_font(size):
    return ImageFont.load_default() # Thay bằng: ImageFont.truetype("đường_dẫn_font.ttf", size)

# ================= XỬ LÝ HÌNH ẢNH =================
async def fetch_avatar(session, url: str) -> Image.Image:
    """Tải và bo tròn avatar, có sử dụng LRU Cache để tối ưu RAM"""
    if url in AVATAR_CACHE:
        AVATAR_CACHE.move_to_end(url)
        return AVATAR_CACHE[url]

    async with session.get(url) as resp:
        if resp.status != 200:
            return Image.new("RGBA", (150, 150), (255, 255, 255, 0))
        data = await resp.read()
        
    img = Image.open(BytesIO(data)).convert("RGBA").resize((150, 150))
    
    # Tạo mask bo tròn
    mask = Image.new("L", (150, 150), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)
    
    circular_img = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
    circular_img.paste(img, (0, 0), mask=mask)
    
    # Xử lý LRU Cache
    AVATAR_CACHE[url] = circular_img
    if len(AVATAR_CACHE) > MAX_AVATAR_CACHE:
        AVATAR_CACHE.popitem(last=False)
        
    return circular_img

def _draw_profile_card(avatar: Image.Image, user_name: str, stats: dict) -> BytesIO:
    """Hàm vẽ thẻ Profile bằng Pillow (Thay thế tọa độ vẽ của bạn vào đây)"""
    bg = Image.new("RGBA", (800, 300), (30, 30, 30, 255)) # Thay bằng ảnh nền của bạn
    bg.paste(avatar, (50, 75), avatar)
    
    draw = ImageDraw.Draw(bg)
    font_large = get_font(40)
    font_small = get_font(25)
    
    draw.text((230, 80), user_name, font=font_large, fill="white")
    draw.text((230, 140), f"KiPoints: {format_points(stats.get('points', 0))}", font=font_small, fill="gold")
    draw.text((230, 180), f"Streak: {stats.get('streak', 0)} ngày", font=font_small, fill="orange")
    
    buffer = BytesIO()
    bg.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# ================= GIAO DIỆN NÚT BẤM BẢNG XẾP HẠNG =================
class TopView(discord.ui.View):
    def __init__(self, bot, sorted_users, total_pages, current_page=1):
        super().__init__(timeout=60)
        self.bot = bot
        self.sorted_users = sorted_users
        self.total_pages = total_pages
        self.current_page = current_page
        self._update_buttons()

    def _update_buttons(self):
        self.btn_prev.disabled = self.current_page <= 1
        self.btn_next.disabled = self.current_page >= self.total_pages

    async def _update_message(self, interaction: discord.Interaction):
        # Tạo hàm vẽ bảng xếp hạng (bạn chèn logic vẽ Top vào đây)
        embed = discord.Embed(title=f"🏆 BẢNG XẾP HẠNG (Trang {self.current_page}/{self.total_pages})", color=discord.Color.gold())
        
        start_idx = (self.current_page - 1) * 10
        page_users = self.sorted_users[start_idx:start_idx+10]
        
        desc = ""
        for i, (uid, stats) in enumerate(page_users, start=start_idx+1):
            desc += f"**#{i}** - <@{uid}>: **{format_points(stats['points'])}** KP\n"
        embed.description = desc

        self._update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀ Trang trước", style=discord.ButtonStyle.primary, custom_id="prev_page")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        await self._update_message(interaction)

    @discord.ui.button(label="Trang sau ▶", style=discord.ButtonStyle.primary, custom_id="next_page")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        await self._update_message(interaction)

# ================= LỚP COG CHÍNH =================
class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command(name="profile", aliases=["p"])
    async def show_profile(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        
        msg = await ctx.send("⏳ Đang tải thẻ thông tin...")
        
        data = await load_data()
        user_stats = data.get(str(target.id), {"points": 0, "streak": 0})
        
        avatar_url = target.display_avatar.replace(size=256).url
        avatar_img = await fetch_avatar(self.session, avatar_url)
        
        # Chạy tác vụ vẽ ảnh trong thread riêng để không block bot
        buffer = await self.bot.loop.run_in_executor(None, _draw_profile_card, avatar_img, target.display_name, user_stats)
        
        file = discord.File(fp=buffer, filename="profile.png")
        await msg.edit(content=None, attachments=[file])

    @commands.command(name="top")
    async def show_top(self, ctx):
        data = await load_data()
        if not data:
            return await ctx.send(embed=discord.Embed(title="⚠️ CHƯA CÓ DỮ LIỆU", color=discord.Color.gold()))

        # Sắp xếp giảm dần theo điểm
        sorted_users = sorted(data.items(), key=lambda x: x[1].get("points", 0), reverse=True)
        total_pages = max(1, (len(sorted_users) + 9) // 10)

        view = TopView(self.bot, sorted_users, total_pages, 1)
        
        embed = discord.Embed(title=f"🏆 BẢNG XẾP HẠNG (Trang 1/{total_pages})", color=discord.Color.gold())
        desc = ""
        for i, (uid, stats) in enumerate(sorted_users[:10], start=1):
            desc += f"**#{i}** - <@{uid}>: **{format_points(stats['points'])}** KP\n"
        embed.description = desc

        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(RankCog(bot))
      

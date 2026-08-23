import discord
from discord.ext import commands
import random
from database import load_seals, save_seals, load_allowed_channels

class SealCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= 1. GHI NHẬN ẢNH TỪ KÊNH ĐƯỢC CẤP QUYỀN =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn của bot hoặc tin nhắn nhắn riêng (DM)
        if message.author.bot or not message.guild:
            return

        # Kiểm tra xem kênh có được bật quyền 'seal' không
        allowed_channels = await load_allowed_channels()
        ch_id = str(message.channel.id)
        
        if ch_id not in allowed_channels or not allowed_channels[ch_id].get("seal"):
            return

        # Kiểm tra xem tin nhắn có đính kèm ảnh không
        if not message.attachments:
            return
            
        img_url = message.attachments[0].url
        msg_link = message.jump_url

        # Tải dữ liệu từ database
        seals_data = await load_seals()
        
        # Đánh số ID tự động tăng dựa trên số lượng ảnh hiện có
        new_id = str(len(seals_data) + 1)
        
        seals_data[new_id] = {
            "id": new_id,
            "message_id": message.id,  # Lưu lại để xóa khi cần
            "author_id": message.author.id,
            "img_url": img_url,
            "msg_link": msg_link
        }
        
        await save_seals(seals_data)
        
        # Thả reaction báo hiệu lưu thành công
        await message.add_reaction("🦭")
        await message.add_reaction("✅")

    # ================= 2. QUẢN TRỊ VIÊN XÓA ẢNH (RE-INDEX) =================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Chỉ xử lý khi có người thả ❌ và người đó không phải là bot
        if payload.user_id == self.bot.user.id or str(payload.emoji.name) != "❌":
            return
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        member = guild.get_member(payload.user_id)
        # Chỉ những ai có quyền Admin mới được gỡ ảnh
        if not member or not member.guild_permissions.administrator:
            return

        seals_data = await load_seals()
        target_key = None
        
        # Quét tìm bức ảnh có message_id trùng với tin nhắn vừa bị thả ❌
        for key, seal in seals_data.items():
            if seal.get("message_id") == payload.message_id:
                target_key = key
                break
                
        if target_key:
            # 1. Xóa ảnh khỏi database
            del seals_data[target_key]
            
            # 2. Dồn lại toàn bộ ID (Re-index) để không bị nhảy số
            new_seals_data = {}
            for new_index, (old_key, seal_info) in enumerate(seals_data.items(), start=1):
                str_index = str(new_index)
                seal_info["id"] = str_index
                new_seals_data[str_index] = seal_info
                
            await save_seals(new_seals_data)
            
            # 3. Thay đổi biểu cảm trên tin nhắn gốc thành thùng rác
            channel = self.bot.get_channel(payload.channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(payload.message_id)
                    # Gỡ tất cả biểu cảm cũ và thêm 🗑️
                    await msg.clear_reactions()
                    await msg.add_reaction("🗑️")
                except discord.Forbidden:
                    # Nếu bot không có quyền "Manage Messages" để clear_reactions
                    await msg.add_reaction("🗑️")
                except discord.NotFound:
                    pass

    # ================= 3. LỆNH GỌI ẢNH NGẪU NHIÊN =================
    @commands.command(name="seal")
    async def random_seal(self, ctx):
        seals_data = await load_seals()
        
        if not seals_data:
            embed = discord.Embed(
                title="⚠️ KHO TRỐNG", 
                description="Kho hải cẩu hiện đang trống! Hãy đóng góp thêm hình ảnh bằng cách gửi vào kênh được cấp quyền.", 
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        # Lấy ngẫu nhiên 1 key (ID) từ dictionary
        chosen_id = random.choice(list(seals_data.keys()))
        seal_info = seals_data[chosen_id]

        embed = discord.Embed(
            title=f"🦭 Hải cẩu số #{seal_info['id']} tới đây!!!",
            description=f"📸 **[Nhấn vào đây để xem tin nhắn gốc]({seal_info['msg_link']})**\n👤 Đóng góp bởi: <@{seal_info['author_id']}>",
            color=discord.Color.teal()
        )
        embed.set_image(url=seal_info['img_url'])
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SealCog(bot))
  

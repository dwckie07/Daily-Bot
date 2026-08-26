import re
import random
import asyncio
from collections import deque
import discord
from discord.ext import commands
from database import load_allowed_channels, load_kiki_data, save_kiki_data

URL_REGEX = re.compile(r'https?://[^\s]+', re.IGNORECASE)

# Bộ nhớ đệm 3 ảnh xuất hiện gần nhất để tránh lặp trùng
RECENT_KIKI_IDS = deque(maxlen=3)

class KikiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        allowed_channels = await load_allowed_channels(self.bot)
        channel_id = str(message.channel.id)

        if channel_id not in allowed_channels:
            return

        perm = allowed_channels[channel_id]
        has_kiki_perm = perm.get("kiki", False) if isinstance(perm, dict) else False

        if not has_kiki_perm:
            return

        image_url = None

        if message.attachments:
            attachment = message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image/"):
                image_url = attachment.url
        elif URL_REGEX.search(message.content):
            await asyncio.sleep(1.5)
            try:
                fetched_msg = await message.channel.fetch_message(message.id)
                if fetched_msg.embeds:
                    emb = fetched_msg.embeds[0]
                    if emb.image:
                        image_url = emb.image.url
                    elif emb.thumbnail:
                        image_url = emb.thumbnail.url
            except Exception:
                pass

            if not image_url:
                match = URL_REGEX.search(message.content)
                if match:
                    image_url = match.group(0)

        if not image_url:
            return

        kikis = await load_kiki_data()
        new_id = len(kikis) + 1

        kiki_entry = {
            "id": new_id,
            "url": image_url,
            "message_id": str(message.id),
            "channel_id": str(message.channel.id),
            "credit": None
        }
        kikis.append(kiki_entry)
        await save_kiki_data(kikis)

        await message.add_reaction("✅")
        await message.add_reaction("❌")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id or str(payload.emoji) != "❌":
            return

        allowed_channels = await load_allowed_channels(self.bot)
        channel_id_str = str(payload.channel_id)
        if channel_id_str not in allowed_channels:
            return

        perm = allowed_channels[channel_id_str]
        has_kiki_perm = perm.get("kiki", False) if isinstance(perm, dict) else False
        if not has_kiki_perm:
            return

        kikis = await load_kiki_data()
        msg_id = str(payload.message_id)

        target_index = None
        for idx, item in enumerate(kikis):
            if item.get("message_id") == msg_id:
                target_index = idx
                break

        if target_index is None:
            return

        kikis.pop(target_index)

        for idx, item in enumerate(kikis):
            item["id"] = idx + 1

        await save_kiki_data(kikis)

        channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(payload.message_id)
                await msg.clear_reactions()
                await msg.add_reaction("🗑️")
            except Exception:
                pass

    @commands.command(name="credit")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def credit(self, ctx, message_id_or_id: str, *, credit_info: str):
        kikis = await load_kiki_data()
        target_item = None

        for item in kikis:
            if item.get("message_id") == message_id_or_id or str(item.get("id")) == message_id_or_id:
                target_item = item
                break

        if not target_item:
            embed = discord.Embed(
                title="❌ KHÔNG TÌM THẤY",
                description=f"Không tìm thấy ảnh nào trong kho Kiki khớp với ID tin nhắn / ID ảnh: `{message_id_or_id}`",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        target_item["credit"] = credit_info
        await save_kiki_data(kikis)

        embed = discord.Embed(
            title="✅ THÊM CREDIT THÀNH CÔNG",
            description=f"Đã gán credit **{credit_info}** cho ảnh Kiki #{target_item['id']} (Message ID: `{target_item['message_id']}`)",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="kiki")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def kiki(self, ctx):
        kikis = await load_kiki_data()
        if not kikis:
            embed = discord.Embed(
                title="🎨 KIKI",
                description="Kho hiện chưa có ảnh/GIF Kiki nào!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Cơ chế lọc ảnh trùng 3 lượt gần nhất
        available = [k for k in kikis if k["id"] not in RECENT_KIKI_IDS]
        if not available:
            available = kikis

        chosen = random.choice(available)
        RECENT_KIKI_IDS.append(chosen["id"])

        embed = discord.Embed(
            title=f"🎨 Kiki #{chosen['id']}",
            color=discord.Color.purple()
        )
        embed.set_image(url=chosen["url"])

        credit_val = chosen.get("credit")
        if credit_val:
            embed.set_footer(text=f"Artist: {credit_val} | Tổng số: {len(kikis)}")
        else:
            embed.set_footer(text=f"Tổng số ảnh trong kho: {len(kikis)}")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(KikiCog(bot))
    

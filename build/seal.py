import re
import random
import asyncio
from collections import deque
import discord
from discord.ext import commands
from database import load_allowed_channels, load_seal_data, save_seal_data

URL_REGEX = re.compile(r'https?://[^\s]+', re.IGNORECASE)

# Bộ nhớ đệm 3 ảnh xuất hiện gần nhất để tránh lặp trùng
RECENT_SEAL_IDS = deque(maxlen=3)

class SealCog(commands.Cog):
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
        has_seal_perm = perm.get("seal", False) if isinstance(perm, dict) else False

        if not has_seal_perm:
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

        seals = await load_seal_data()
        new_id = len(seals) + 1

        seal_entry = {
            "id": new_id,
            "url": image_url,
            "message_id": str(message.id),
            "channel_id": str(message.channel.id)
        }
        seals.append(seal_entry)
        await save_seal_data(seals)

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
        has_seal_perm = perm.get("seal", False) if isinstance(perm, dict) else False
        if not has_seal_perm:
            return

        seals = await load_seal_data()
        msg_id = str(payload.message_id)

        target_index = None
        for idx, item in enumerate(seals):
            if item.get("message_id") == msg_id:
                target_index = idx
                break

        if target_index is None:
            return

        seals.pop(target_index)

        for idx, item in enumerate(seals):
            item["id"] = idx + 1

        await save_seal_data(seals)

        channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(payload.message_id)
                await msg.clear_reactions()
                await msg.add_reaction("🗑️")
            except Exception:
                pass

    @commands.command(name="seal")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def seal(self, ctx):
        seals = await load_seal_data()
        if not seals:
            embed = discord.Embed(
                title="🦭 HẢI CẨU",
                description="Kho hiện chưa có ảnh/GIF hải cẩu nào!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Cơ chế lọc ảnh trùng 3 lượt gần nhất
        available = [s for s in seals if s["id"] not in RECENT_SEAL_IDS]
        if not available:
            available = seals

        chosen = random.choice(available)
        RECENT_SEAL_IDS.append(chosen["id"])

        embed = discord.Embed(
            title=f"🦭 Hải Cẩu #{chosen['id']}",
            color=discord.Color.blue()
        )
        embed.set_image(url=chosen["url"])
        embed.set_footer(text=f"Tổng số ảnh/GIF trong kho: {len(seals)}")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SealCog(bot))
    

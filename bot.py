import os
import json
import asyncio
import discord
from discord.ext import commands
import instaloader

# ===== ENV VARIABLES =====
TOKEN = os.getenv("DISCORD_TOKEN")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

if not TOKEN or not INSTAGRAM_USERNAME:
    print("❌ Missing DISCORD_TOKEN or INSTAGRAM_USERNAME")
    exit(1)

# ===== CONFIG FILE =====
CONFIG_FILE = "config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ===== DISCORD SETUP =====
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== INSTAGRAM =====
L = instaloader.Instaloader()
posted_posts = set()


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    bot.loop.create_task(check_instagram())


@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    """Set the channel where Instagram posts will be sent"""
    data = load_config()
    data["channel_id"] = ctx.channel.id
    save_config(data)

    await ctx.send(f"✅ Instagram posts will be sent in {ctx.channel.mention}")


@bot.command()
async def test(ctx):
    """Test if channel is saved"""
    data = load_config()
    channel_id = data.get("channel_id")

    if not channel_id:
        await ctx.send("❌ No channel set. Use `!setchannel`")
    else:
        await ctx.send("✅ Channel is set correctly!")


async def check_instagram():
    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            data = load_config()
            channel_id = data.get("channel_id")

            if not channel_id:
                await asyncio.sleep(60)
                continue

            channel = bot.get_channel(channel_id)
            if not channel:
                await asyncio.sleep(60)
                continue

            profile = instaloader.Profile.from_username(
                L.context, INSTAGRAM_USERNAME
            )
            latest_post = next(profile.get_posts())
            post_url = f"https://www.instagram.com/p/{latest_post.shortcode}/"

            if post_url not in posted_posts:
                await channel.send(f"📸 **New Instagram post!**\n{post_url}")
                posted_posts.add(post_url)

        except Exception as e:
            print("Instagram error:", e)

        await asyncio.sleep(300)  # 5 minutes


bot.run(TOKEN)

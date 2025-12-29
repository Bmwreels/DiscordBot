import os
import sys
import discord
import asyncio
import instaloader
import json
import time

# ================= FILES =================
POSTED_FILE = "posted_posts.json"
CONFIG_FILE = "config.json"

# ================= CONFIG =================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

config = load_config()

# ================= POSTED POSTS =================
def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_posted(posts):
    with open(POSTED_FILE, "w") as f:
        json.dump(list(posts)[-50:], f)

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

if not TOKEN or not INSTAGRAM_USERNAME:
    print("❌ Missing environment variables")
    sys.exit(1)

CHANNEL_ID = config.get("channel_id")

# ================= DISCORD =================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

L = instaloader.Instaloader()
posted_posts = load_posted()
start_time = time.time()

# ================= INSTAGRAM TASK =================
async def check_instagram():
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            if not CHANNEL_ID:
                await asyncio.sleep(60)
                continue

            channel = client.get_channel(CHANNEL_ID)
            if not channel:
                await asyncio.sleep(60)
                continue

            profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)

            for post in profile.get_posts():
                if post.is_pinned:
                    continue

                url = f"https://www.instagram.com/p/{post.shortcode}/"

                if url not in posted_posts:
                    await channel.send(url)
                    posted_posts.add(url)
                    save_posted(posted_posts)

                break

        except Exception as e:
            print("Instagram error:", e)

        await asyncio.sleep(300)

# ================= COMMAND HANDLER =================
@client.event
async def on_message(message):
    global CHANNEL_ID

    if message.author.bot:
        return

    content = message.content

    # ---- SET CHANNEL ----
    if content.lower() == "!setchannel":
        if not message.author.guild_permissions.manage_channels:
            await message.channel.send("❌ You need **Manage Channels** permission.")
            return

        CHANNEL_ID = message.channel.id
        config["channel_id"] = CHANNEL_ID
        save_config(config)

        await message.channel.send(f"✅ Channel set to {message.channel.mention}")

    # ---- SAY ----
    elif content.lower().startswith("!say "):
        text = content[5:]
        if text.strip():
            await message.channel.send(text)
        else:
            await message.channel.send("❌ Usage: `!say your message`")

    # ---- PING ----
    elif content.lower() == "!ping":
        latency = round(client.latency * 1000)
        await message.channel.send(f"🏓 Pong! `{latency}ms`")

    # ---- STATUS ----
    elif content.lower() == "!status":
        uptime = int(time.time() - start_time)
        channel = f"<#{CHANNEL_ID}>" if CHANNEL_ID else "Not set"

        await message.channel.send(
            f"**🤖 Bot Status**\n"
            f"• Uptime: `{uptime}s`\n"
            f"• Instagram: `{INSTAGRAM_USERNAME}`\n"
            f"• Channel: {channel}"
        )

    # ---- HELP ----
    elif content.lower() == "!help":
        await message.channel.send(
            "**📜 Bot Commands**\n"
            "`!setchannel` – Set Instagram post channel\n"
            "`!say <text>` – Make bot say something\n"
            "`!ping` – Check bot latency\n"
            "`!status` – Bot info\n"
            "`!help` – Show this message"
        )

# ================= READY =================
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(check_instagram())

# ================= RUN =================
try:
    client.run(TOKEN)
except discord.errors.PrivilegedIntentsRequired:
    print("❌ Enable MESSAGE CONTENT INTENT in Discord portal")
    sys.exit(1)

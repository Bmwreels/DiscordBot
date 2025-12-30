import os
import sys
import discord
import asyncio
import instaloader
import json
import time
from discord.ext import tasks

# ================= RAILWAY STORAGE PATH =================
# We use /app/data/ because that's where Railway Volumes mount by default
DATA_DIR = "/app/data"

# Create the directory if it doesn't exist (for local testing)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

POSTED_FILE = os.path.join(DATA_DIR, "posted_posts.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# ================= CONFIG & LOADING =================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_posted():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except:
            return set()
    return set()

def save_posted(posts):
    post_list = list(posts)[-50:]
    with open(POSTED_FILE, "w") as f:
        json.dump(post_list, f)

# ================= BOT SETUP =================
config = load_config()
TOKEN = os.getenv("DISCORD_TOKEN")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

if not TOKEN or not INSTAGRAM_USERNAME:
    print("❌ Missing environment variables")
    sys.exit(1)

CHANNEL_ID = config.get("channel_id")
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
L = instaloader.Instaloader()
posted_posts = load_posted()
start_time = time.time()

async def fetch_latest_post():
    global CHANNEL_ID
    if not CHANNEL_ID: return "no_channel"
    channel = client.get_channel(int(CHANNEL_ID))
    if not channel: return "error_channel"

    try:
        profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
        new_found = False
        count = 0
        for post in profile.get_posts():
            if count >= 4: break
            count += 1
            if post.is_pinned: continue
            
            url = f"https://www.instagram.com/p/{post.shortcode}/"
            if url not in posted_posts:
                await channel.send(f"📸 **New post from {INSTAGRAM_USERNAME}!**\n{url}")
                posted_posts.add(url)
                save_posted(posted_posts)
                new_found = True
                break
        return "new_post" if new_found else "no_new_post"
    except Exception as e:
        return str(e)

@tasks.loop(minutes=10)
async def check_instagram_loop():
    if CHANNEL_ID:
        await fetch_latest_post()

@client.event
async def on_message(message):
    global CHANNEL_ID
    if message.author.bot: return
    content = message.content.lower().strip()

    if content == "!setchannel":
        if message.author.guild_permissions.manage_channels:
            CHANNEL_ID = message.channel.id
            config["channel_id"] = CHANNEL_ID
            save_config(config)
            await message.channel.send(f"✅ Channel set to {message.channel.mention}")

    elif content == "!status":
        uptime = int(time.time() - start_time)
        await message.channel.send(f"**🤖 Status**\n• Target: `{INSTAGRAM_USERNAME}`\n• Uptime: `{uptime // 60}m`")

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    if not check_instagram_loop.is_running():
        check_instagram_loop.start()

client.run(TOKEN)

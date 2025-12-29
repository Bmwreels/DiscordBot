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
        json.dump(data, f, indent=4)

config = load_config()

# ================= POSTED POSTS =================
def load_posted():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_posted(posts):
    with open(POSTED_FILE, "w") as f:
        # Keep the last 100 posts to ensure we don't re-post old content
        json.dump(list(posts)[-100:], f)

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

if not TOKEN or not INSTAGRAM_USERNAME:
    print("❌ Missing environment variables (DISCORD_TOKEN or INSTAGRAM_USERNAME)")
    sys.exit(1)

CHANNEL_ID = config.get("channel_id")

# ================= SETUP =================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

L = instaloader.Instaloader()
# Spoof user agent to look more like a browser
L.context._session.headers.update({'User-Agent': 'Mozilla/5.0'}) 

posted_posts = load_posted()
start_time = time.time()

# ================= CORE LOGIC =================
async def fetch_latest_post():
    """Logic separated so it can be called by loop or command"""
    global CHANNEL_ID
    if not CHANNEL_ID:
        return None

    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return "error_channel"

    try:
        profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
        
        # Check top 4 posts (to bypass up to 3 pinned posts)
        for post in profile.get_posts():
            if post.is_pinned:
                continue
            
            url = f"https://www.instagram.com/p/{post.shortcode}/"
            
            if url not in posted_posts:
                await channel.send(f"📸 **New post from {INSTAGRAM_USERNAME}!**\n{url}")
                posted_posts.add(url)
                save_posted(posted_posts)
                return "new_post"
            
            # If the first non-pinned post is already in our list, stop.
            break 
        return "no_new_post"

    except Exception as e:
        print(f"Instagram error: {e}")
        return str(e)

# ================= BACKGROUND TASK =================
async def check_instagram_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        print(f"🔍 Checking Instagram for {INSTAGRAM_USERNAME}...")
        await fetch_latest_post()
        # Increased to 10 mins (600s) to avoid 429 Rate Limits
        await asyncio.sleep(600)

# ================= COMMAND HANDLER =================
@client.event
async def on_message(message):
    global CHANNEL_ID
    if message.author.bot: return
    content = message.content.lower()

    if content == "!setchannel":
        if not message.author.guild_permissions.manage_channels:
            return await message.channel.send("❌ Permission denied.")
        CHANNEL_ID = message.channel.id
        config["channel_id"] = CHANNEL_ID
        save_config(config)
        await message.channel.send(f"✅ Channel set to {message.channel.mention}")

    elif content == "!check":
        await message.channel.send("🔍 Checking for new posts...")
        result = await fetch_latest_post()
        if result == "new_post":
            await message.channel.send("✅ Found and posted!")
        elif result == "no_new_post":
            await message.channel.send("👍 Everything is up to date.")
        else:
            await message.channel.send(f"⚠️ Error: `{result}`")

    elif content == "!status":
        uptime = int(time.time() - start_time)
        await message.channel.send(
            f"**🤖 Status**\n• Uptime: `{uptime}s`\n• Target: `{INSTAGRAM_USERNAME}`\n• Channel: <#{CHANNEL_ID}>"
        )

# ================= RUN =================
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(check_instagram_loop())

try:
    client.run(TOKEN)
except discord.errors.PrivilegedIntentsRequired:
    print("❌ Enable MESSAGE CONTENT INTENT in Discord portal")

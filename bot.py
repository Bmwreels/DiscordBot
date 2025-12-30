import os
import sys
import discord
import asyncio
import instaloader
import json
import time
from discord.ext import tasks

# ================= FILES =================
POSTED_FILE = "posted_posts.json"
CONFIG_FILE = "config.json"

# ================= CONFIG =================
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

config = load_config()

# ================= POSTED POSTS =================
def load_posted():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r") as f:
                # Ensure we load as a list then convert to set
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except:
            return set()
    return set()

def save_posted(posts):
    # Keep only the last 50 posts to prevent the JSON file from growing too large
    # and ensure it stays as a simple list for JSON compatibility
    post_list = list(posts)[-50:]
    with open(POSTED_FILE, "w") as f:
        json.dump(post_list, f)

# ================= ENV & SETUP =================
TOKEN = os.getenv("DISCORD_TOKEN")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

if not TOKEN or not INSTAGRAM_USERNAME:
    print("❌ Missing environment variables (DISCORD_TOKEN or INSTAGRAM_USERNAME)")
    sys.exit(1)

CHANNEL_ID = config.get("channel_id")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Simple Instaloader setup (No Login)
L = instaloader.Instaloader()

posted_posts = load_posted()
start_time = time.time()

# ================= CORE LOGIC =================
async def fetch_latest_post():
    global CHANNEL_ID
    if not CHANNEL_ID:
        return "no_channel"

    channel = client.get_channel(int(CHANNEL_ID))
    if not channel:
        return "error_channel"

    try:
        # Load profile anonymously
        profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
        
        new_found = False
        # We only check the first few posts to avoid rate limits
        count = 0
        for post in profile.get_posts():
            if count >= 4: break # Check top 4 (accounts for pinned posts)
            count += 1
            
            if post.is_pinned:
                continue
            
            url = f"https://www.instagram.com/p/{post.shortcode}/"
            
            if url not in posted_posts:
                await channel.send(f"📸 **New post from {INSTAGRAM_USERNAME}!**\n{url}")
                posted_posts.add(url)
                save_posted(posted_posts)
                new_found = True
                break # Only post the single newest one per check
        
        return "new_post" if new_found else "no_new_post"

    except Exception as e:
        print(f"Instagram error: {e}")
        return str(e)

# ================= BACKGROUND TASK =================
@tasks.loop(minutes=10)
async def check_instagram_loop():
    if not CHANNEL_ID:
        return
    print(f"🔍 Checking Instagram for @{INSTAGRAM_USERNAME}...")
    await fetch_latest_post()

# ================= COMMAND HANDLER =================
@client.event
async def on_message(message):
    global CHANNEL_ID
    if message.author.bot: return
    
    content = message.content.lower().strip()

    if content == "!setchannel":
        if not message.author.guild_permissions.manage_channels:
            return await message.channel.send("❌ Permission denied.")
        CHANNEL_ID = message.channel.id
        config["channel_id"] = CHANNEL_ID
        save_config(config)
        await message.channel.send(f"✅ Success! Instagram updates for **{INSTAGRAM_USERNAME}** will post here.")

    elif content == "!check":
        await message.channel.send("🔍 Checking for new posts...")
        result = await fetch_latest_post()
        if result == "new_post":
            await message.channel.send("✅ New post found and sent!")
        elif result == "no_new_post":
            await message.channel.send("👍 No new posts found.")
        elif result == "no_channel":
            await message.channel.send("⚠️ Use `!setchannel` in the desired channel first.")
        else:
            await message.channel.send(f"⚠️ Error: `{result}`")

    elif content == "!status":
        uptime_sec = int(time.time() - start_time)
        # Convert seconds to readable format
        uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m"
        chan_mention = f"<#{CHANNEL_ID}>" if CHANNEL_ID else "None"
        
        await message.channel.send(
            f"**🤖 Bot Status**\n"
            f"• Target: `{INSTAGRAM_USERNAME}`\n"
            f"• Channel: {chan_mention}\n"
            f"• Uptime: `{uptime_str}`"
        )

# ================= RUN =================
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    if not check_instagram_loop.is_running():
        check_instagram_loop.start()

try:
    client.run(TOKEN)
except discord.errors.PrivilegedIntentsRequired:
    print("❌ ERROR: You must enable 'Message Content Intent' in the Discord Dev Portal!")

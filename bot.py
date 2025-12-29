
import os
import sys
import discord
import asyncio
import instaloader
import json

# File to persist posted Instagram posts
POSTED_FILE = "posted_posts.json"

def load_posted():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_posted(posts):
    try:
        # Keep only the last 50 to avoid file growing too large
        list_posts = list(posts)[-50:]
        with open(POSTED_FILE, "w") as f:
            json.dump(list_posts, f)
    except Exception as e:
        print("Error saving posted posts:", e)

# Load environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

# Stop if anything is missing
if not TOKEN or not CHANNEL_ID or not INSTAGRAM_USERNAME:
    print("❌ Missing environment variables.")
    sys.exit(1)

CHANNEL_ID = int(CHANNEL_ID)

# Configure intents
intents = discord.Intents.default()
intents.message_content = True 

client = discord.Client(intents=intents)
L = instaloader.Instaloader()
posted_posts = load_posted()

async def check_instagram():
    global CHANNEL_ID
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            channel = client.get_channel(CHANNEL_ID)
            if channel:
                profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
                # Iterate through posts and find the first non-pinned one
                for post in profile.get_posts():
                    if post.is_pinned:
                        continue
                        
                    post_url = f"https://www.instagram.com/p/{post.shortcode}/"
                    
                    if post_url not in posted_posts:
                        await channel.send(post_url)
                        posted_posts.add(post_url)
                        save_posted(posted_posts)
                    
                    # Once we've checked the latest non-pinned post, we stop
                    break
            else:
                print(f"⚠️ Channel {CHANNEL_ID} not found.")

        except Exception as e:
            print("Instagram error:", e)

        await asyncio.sleep(300)

@client.event
async def on_message(message):
    global CHANNEL_ID
    if message.author == client.user:
        return

    if message.content.startswith("!setchannel"):
        if message.author.guild_permissions.manage_channels:
            CHANNEL_ID = message.channel.id
            await message.channel.send(f"✅ Notification channel set to <#{CHANNEL_ID}>")
        else:
            await message.channel.send("❌ You need 'Manage Channels' permission.")

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(check_instagram())

try:
    client.run(TOKEN)
except discord.errors.PrivilegedIntentsRequired:
    print("\n❌ FATAL ERROR: Privileged Intents Required (Enable MESSAGE CONTENT INTENT in portal)\n")
    sys.exit(1)

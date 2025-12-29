
import os
import sys
import discord
import asyncio
import instaloader

# Load environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

# Debug logs (visible in Render)
print("DEBUG ENV:")
print("TOKEN:", "OK" if TOKEN else "MISSING")
print("CHANNEL_ID:", CHANNEL_ID)
print("INSTAGRAM_USERNAME:", INSTAGRAM_USERNAME)

# Stop if anything is missing
if not TOKEN or not CHANNEL_ID or not INSTAGRAM_USERNAME:
    print("❌ Missing environment variables. Fix them in Render.")
    sys.exit(1)

CHANNEL_ID = int(CHANNEL_ID)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

L = instaloader.Instaloader()
posted_posts = set()

async def check_instagram():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            profile = instaloader.Profile.from_username(
                L.context, INSTAGRAM_USERNAME
            )
            latest_post = next(profile.get_posts())
            post_url = f"https://www.instagram.com/p/{latest_post.shortcode}/"

            if post_url not in posted_posts:
                await channel.send(f"📸 New Instagram post!\n{post_url}")
                posted_posts.add(post_url)

        except Exception as e:
            print("Instagram error:", e)

        await asyncio.sleep(300)  # 5 minutes

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(check_instagram())

client.run(TOKEN)

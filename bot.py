import discord
import asyncio
import instaloader

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
INSTAGRAM_USERNAME = "https://www.instagram.com/bmw.reels.in/?igsh=c3FraDRmYnZvbnM%3D#"

client = discord.Client(intents=discord.Intents.default())
L = instaloader.Instaloader()
posted_posts = set()

async def check_instagram():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
            latest_post = next(profile.get_posts())
            post_url = f"https://www.instagram.com/p/{latest_post.shortcode}/"

            if post_url not in posted_posts:
                await channel.send(f"New Instagram post: {post_url}")
                posted_posts.add(post_url)

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(300)  # Check every 5 minutes

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

client.loop.create_task(check_instagram())

client.run(TOKEN)

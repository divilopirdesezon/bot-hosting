import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

initial_extensions = [
    "cogs.vps",
    "cogs.faq",
    "cogs.verify",
    "cogs.ticket",
    "cogs.preturi",
    "cogs.invite",
    "cogs.donat"
]

async def load_extensions():
    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Error loading {ext}: {e}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="🎮 byteshield.biz!")
    )

    await load_extensions()

    try:
        synced = await bot.tree.sync()
        print(f"🔁 Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Sync error: {e}")

bot.run(TOKEN)
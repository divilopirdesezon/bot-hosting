import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
import pytz

DONATE_FILE = "donatii.json"
COOLDOWN_FILE = "cooldown_donate.json"
TZ = pytz.timezone("Europe/Bucharest")

def load_json(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

class Donate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="donate", description="Trimite o donație (PSF) cu motiv, sumă și cod")
    @app_commands.describe(motiv="Motivul donației", suma="Suma în EUR (maxim 50)", cod="Codul PSF")
    async def donate(self, interaction: discord.Interaction, motiv: str, suma: float, cod: str):
        user_id = str(interaction.user.id)
        cooldowns = load_json(COOLDOWN_FILE)
        now = datetime.now(TZ)

        if suma > 50:
            await interaction.response.send_message("❌ Suma maximă acceptată este de 50 EUR.", ephemeral=True)
            return

        # Cooldown
        if user_id in cooldowns:
            last_used = datetime.strptime(cooldowns[user_id], "%Y-%m-%d %H:%M:%S")
            if now < last_used + timedelta(hours=1):
                remaining = (last_used + timedelta(hours=1)) - now
                minutes = int(remaining.total_seconds() // 60)
                await interaction.response.send_message(f"⏳ Poți folosi comanda din nou în {minutes} minute.", ephemeral=True)
                return

        # Salvare donație
        donatii = load_json(DONATE_FILE)
        new_id = (donatii[-1]["id"] + 1) if donatii else 1

        donatie = {
            "id": new_id,
            "user_id": user_id,
            "username": str(interaction.user),
            "motiv": motiv,
            "suma": suma,
            "cod": cod,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
        }

        donatii.append(donatie)
        save_json(DONATE_FILE, donatii)

        cooldowns[user_id] = now.strftime("%Y-%m-%d %H:%M:%S")
        save_json(COOLDOWN_FILE, cooldowns)

        await interaction.response.send_message(
            f"✅ Donație #{new_id} înregistrată!\n📌 **Motiv:** {motiv}\n💶 **Sumă:** {suma:.2f} EUR\n🔑 **Cod:** ||{cod}||",
            ephemeral=True
        )

    @app_commands.command(name="dstatus", description="Afișează totalul donațiilor")
    async def dstatus(self, interaction: discord.Interaction):
        donatii = load_json(DONATE_FILE)
        total = sum([d.get("suma", 0) for d in donatii])
        await interaction.response.send_message(f"💰 Total donații: **{total:.2f} EUR**", ephemeral=False)

    @app_commands.command(name="check", description="Verifică detalii despre o donație după ID")
    @app_commands.describe(donatie_id="ID-ul donației")
    async def check(self, interaction: discord.Interaction, donatie_id: int):
        donatii = load_json(DONATE_FILE)
        donatie = next((d for d in donatii if d["id"] == donatie_id), None)
        if not donatie:
            await interaction.response.send_message("❌ Donația nu a fost găsită.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Donația #{donatie_id}", color=0x00ff99)
        embed.add_field(name="User", value=f"<@{donatie['user_id']}> ({donatie['username']})", inline=False)
        embed.add_field(name="Motiv", value=donatie["motiv"], inline=False)
        embed.add_field(name="Sumă", value=f"{donatie['suma']:.2f} EUR", inline=True)
        embed.add_field(name="Cod", value=f"||{donatie['cod']}||", inline=True)
        embed.set_footer(text=f"Data: {donatie['timestamp']}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dremove", description="Șterge o donație după ID (admin only)")
    @app_commands.describe(donatie_id="ID-ul donației de șters")
    async def dremove(self, interaction: discord.Interaction, donatie_id: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nu ai permisiunea să ștergi donații.", ephemeral=True)
            return

        donatii = load_json(DONATE_FILE)
        updated = [d for d in donatii if d["id"] != donatie_id]

        if len(updated) == len(donatii):
            await interaction.response.send_message("❌ Donația nu a fost găsită.", ephemeral=True)
            return

        save_json(DONATE_FILE, updated)
        await interaction.response.send_message(f"🗑️ Donația #{donatie_id} a fost ștearsă cu succes.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Donate(bot))
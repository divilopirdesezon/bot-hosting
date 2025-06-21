import discord
from discord import app_commands
from discord.ext import commands

class Preturi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="preturi", description="Afișează planurile de hosting")
    async def preturi(self, interaction: discord.Interaction):
        # Verifică dacă userul este owner
        if interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ Doar ownerul serverului poate folosi această comandă.", ephemeral=True)

        try:
            with open("preturi.txt", "r", encoding="utf-8") as f:
                content = f.read()

            embed = discord.Embed(
                title="📋 Lista de Prețuri Hosting",
                description=content,
                color=discord.Color.blue()
            )
            embed.set_footer(text="ByteShield Hosting")

            await interaction.response.send_message(embed=embed)

        except FileNotFoundError:
            await interaction.response.send_message("❌ Fișierul `preturi.txt` nu a fost găsit.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Preturi(bot))
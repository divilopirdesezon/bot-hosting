import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
from datetime import datetime

GUILD_ID = int(os.getenv("GUILD_ID"))
NOTIFY_ROLE_ID = int(os.getenv("NOTIFY_ROLE_ID"))
vps_data_file = "vps_data.json"

def load_data():
    if not os.path.exists(vps_data_file):
        return []
    with open(vps_data_file, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(vps_data_file, 'w') as f:
        json.dump(data, f, indent=4)

class VPSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_vps_expiry.start()

    def cog_unload(self):
        self.check_vps_expiry.cancel()

    @app_commands.command(name="addvps", description="Adaugă un VPS nou")
    @app_commands.describe(user="ID utilizator", expiration="Data expirării", added_by="ID adăugător", ip="IP VPS")
    async def addvps(self, interaction: discord.Interaction, user: str, expiration: str, added_by: str, ip: str):
        notify_role = discord.utils.get(interaction.guild.roles, id=NOTIFY_ROLE_ID)
        if notify_role not in interaction.user.roles:
            await interaction.response.send_message("Nu ai permisiunea.", ephemeral=True)
            return

        try:
            expire_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            vps_number = len(load_data()) + 1
        except ValueError:
            await interaction.response.send_message("Format dată invalid.", ephemeral=True)
            return

        data = load_data()
        data.append({"user_id": user, "expiration": str(expire_date), "added_by": added_by, "vps_number": vps_number, "ip": ip})
        save_data(data)

        embed = discord.Embed(title="VPS Adăugat", color=discord.Color.green())
        embed.add_field(name="Deținător", value=user)
        embed.add_field(name="Expiră", value=expiration)
        embed.add_field(name="Adăugat de", value=added_by)
        embed.add_field(name="IP", value=ip)
        embed.add_field(name="Număr VPS", value=str(vps_number))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="vps", description="Afișează toate VPS-urile")
    async def vps(self, interaction: discord.Interaction):
        data = load_data()
        if not data:
            await interaction.response.send_message("Nu există VPS-uri.")
            return

        per_page = 5
        pages = [data[i:i + per_page] for i in range(0, len(data), per_page)]
        total_pages = len(pages)

        def create_embed(page_index):
            page_data = pages[page_index]
            embed = discord.Embed(title=f"VPS-uri (Pagina {page_index + 1}/{total_pages})", color=discord.Color.blue())
            for entry in page_data:
                embed.add_field(
                    name=f"VPS #{entry['vps_number']}",
                    value=f"User: <@{entry['user_id']}>\nExpiră: {entry['expiration']}\nIP: `{entry['ip']}`",
                    inline=False
                )
            return embed

        class Paginator(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=180)
                self.page = 0

            @discord.ui.button(label="◀️ Înapoi", style=discord.ButtonStyle.blurple)
            async def back(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                if self.page > 0:
                    self.page -= 1
                    await interaction_button.response.edit_message(embed=create_embed(self.page), view=self)

            @discord.ui.button(label="Înainte ▶️", style=discord.ButtonStyle.blurple)
            async def next(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                if self.page < total_pages - 1:
                    self.page += 1
                    await interaction_button.response.edit_message(embed=create_embed(self.page), view=self)

        view = Paginator()
        await interaction.response.send_message(embed=create_embed(0), view=view)

    @app_commands.command(name="renewvps", description="Prelungește un VPS")
    @app_commands.describe(vps_number="Număr VPS", new_expiration="Noua dată (YYYY-MM-DD)")
    async def renewvps(self, interaction: discord.Interaction, vps_number: int, new_expiration: str):
        notify_role = discord.utils.get(interaction.guild.roles, id=NOTIFY_ROLE_ID)
        if notify_role not in interaction.user.roles:
            await interaction.response.send_message("Nu ai permisiunea.", ephemeral=True)
            return

        try:
            new_date = datetime.strptime(new_expiration, "%Y-%m-%d").date()
        except ValueError:
            await interaction.response.send_message("Dată invalidă.", ephemeral=True)
            return

        data = load_data()
        for entry in data:
            if entry["vps_number"] == vps_number:
                entry["expiration"] = str(new_date)
                save_data(data)
                await interaction.response.send_message(f"VPS #{vps_number} prelungit.", ephemeral=True)
                return

        await interaction.response.send_message("VPS negăsit.", ephemeral=True)

    @app_commands.command(name="removevps", description="Șterge un VPS")
    @app_commands.describe(vps_number="Număr VPS de șters")
    async def removevps(self, interaction: discord.Interaction, vps_number: int):
        notify_role = discord.utils.get(interaction.guild.roles, id=NOTIFY_ROLE_ID)
        if notify_role not in interaction.user.roles:
            await interaction.response.send_message("Nu ai permisiunea.", ephemeral=True)
            return

        data = load_data()
        new_data = [entry for entry in data if entry.get("vps_number") != vps_number]

        if len(data) == len(new_data):
            await interaction.response.send_message("VPS negăsit.", ephemeral=True)
        else:
            save_data(new_data)
            await interaction.response.send_message("VPS șters cu succes.", ephemeral=True)

    @tasks.loop(hours=24)
    async def check_vps_expiry(self):
        today = datetime.now().date()
        data = load_data()
        guild = self.bot.get_guild(GUILD_ID)
        channel = discord.utils.get(guild.text_channels, name="notificari-vps")
        role = guild.get_role(NOTIFY_ROLE_ID)

        for entry in data:
            exp_date = datetime.strptime(entry["expiration"], "%Y-%m-%d").date()
            if exp_date == today:
                await channel.send(f"{role.mention}, VPS #{entry['vps_number']} deținut de <@{entry['user_id']}> expiră azi!")

async def setup(bot):
    await bot.add_cog(VPSCog(bot))


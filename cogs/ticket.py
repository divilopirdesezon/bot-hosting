import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from datetime import datetime, time
import pytz

CONFIG_FILE = "tickets_config.json"
ACTIVE_FILE = "active_tickets.json"
TZ = pytz.timezone("Europe/Bucharest")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_active():
    if not os.path.exists(ACTIVE_FILE):
        return {}
    with open(ACTIVE_FILE, "r") as f:
        return json.load(f)

def save_active(data):
    with open(ACTIVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

class CloseButton(discord.ui.View):
    def __init__(self, author: discord.Member, log_channel: discord.TextChannel, staff_role: discord.Role):
        super().__init__(timeout=None)
        self.author = author
        self.log_channel = log_channel
        self.staff_role = staff_role

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author and self.staff_role not in interaction.user.roles:
            await interaction.response.send_message("⛔ Doar autorul sau staff-ul poate închide acest ticket.", ephemeral=True)
            return

        active = load_active()
        if str(self.author.id) in active:
            del active[str(self.author.id)]
            save_active(active)

        await interaction.channel.delete()
        await self.log_channel.send(f"📨 Ticket închis de {interaction.user.mention} pentru {self.author.mention}.")

class CreateTicketView(discord.ui.View):
    def __init__(self, category: discord.CategoryChannel, log_channel: discord.TextChannel, staff_role: discord.Role):
        super().__init__(timeout=None)
        self.category = category
        self.log_channel = log_channel
        self.staff_role = staff_role

    @discord.ui.button(label="📩 Creează Ticket", style=discord.ButtonStyle.primary)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        now = datetime.now(TZ).time()
        if now < time(9, 0) or now > time(17, 0):
            await interaction.response.send_message("🕙 Poți deschide tickete doar între 9:00 și 17:00 (ora României).", ephemeral=True)
            return

        guild = interaction.guild
        author = interaction.user

        active = load_active()
        if str(author.id) in active:
            ticket_channel = guild.get_channel(active[str(author.id)]["channel_id"])
            if ticket_channel:
                await interaction.response.send_message(f"⛔ Ai deja un ticket deschis: {ticket_channel.mention}", ephemeral=True)
                return
            else:
                del active[str(author.id)]
                save_active(active)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        if self.staff_role:
            overwrites[self.staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{author.name.lower().replace(' ', '-')}-{random.randint(1000, 9999)}",
            category=self.category,
            overwrites=overwrites,
            topic=f"Ticket deschis de {author}"
        )

        embed = discord.Embed(
            title="🎫 Ticket Deschis",
            description=f"Salut {author.mention}, un membru al echipei te va ajuta în curând.",
            color=discord.Color.blurple()
        )
        await channel.send(embed=embed, view=CloseButton(author, self.log_channel, self.staff_role))

        active[str(author.id)] = {
            "channel_id": channel.id,
            "guild_id": guild.id,
            "opened_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        }
        save_active(active)

        await interaction.response.send_message(f"✅ Ticket creat: {channel.mention}", ephemeral=True)

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settickets", description="Configurează sistemul de tickete")
    @app_commands.describe(category="Categoria pentru canale de tickete", log_channel="Canalul pentru loguri", staff_role="Rolul care poate vedea și închide ticketele")
    async def settickets(self, interaction: discord.Interaction, category: discord.CategoryChannel, log_channel: discord.TextChannel, staff_role: discord.Role):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("⛔ Doar owner-ul poate configura ticketele.", ephemeral=True)
            return

        config = load_config()
        config[str(interaction.guild.id)] = {
            "category_id": category.id,
            "log_channel_id": log_channel.id,
            "staff_role_id": staff_role.id
        }
        save_config(config)

        embed = discord.Embed(
            title="🎫 Creează un Ticket",
            description="Apasă pe butonul de mai jos pentru a deschide un canal privat cu staff-ul.",
            color=discord.Color.blue()
        )

        if interaction.guild.banner:
            embed.set_image(url=interaction.guild.banner.url)

        await interaction.channel.send(embed=embed, view=CreateTicketView(category, log_channel, staff_role))
        await interaction.response.send_message("✅ Sistemul de tickete a fost configurat.", ephemeral=True)

    @app_commands.command(name="closeticket", description="Închide un ticket")
    async def closeticket(self, interaction: discord.Interaction):
        config = load_config().get(str(interaction.guild.id))
        if not config:
            await interaction.response.send_message("⚠️ Sistemul de tickete nu este configurat.", ephemeral=True)
            return

        staff_role = interaction.guild.get_role(config["staff_role_id"])

        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("⛔ Doar staff-ul poate închide tickete prin comandă.", ephemeral=True)
            return

        active = load_active()
        for uid, info in list(active.items()):
            if info["channel_id"] == interaction.channel.id:
                del active[uid]
                save_active(active)
                break

        await interaction.channel.delete()
        log_channel = interaction.guild.get_channel(config["log_channel_id"])
        await log_channel.send(f"📨 Ticket închis de {interaction.user.mention} folosind comanda.")

async def setup(bot):
    await bot.add_cog(TicketCog(bot))
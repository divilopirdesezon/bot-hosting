import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os

INVITE_CONFIG = "invite_config.json"
INVITE_CACHE = {}

def load_invite_config():
    if not os.path.exists(INVITE_CONFIG):
        return {}
    with open(INVITE_CONFIG, "r") as f:
        return json.load(f)

def save_invite_config(data):
    with open(INVITE_CONFIG, "w") as f:
        json.dump(data, f, indent=4)

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}
        self.update_invites.start()

    def cog_unload(self):
        self.update_invites.cancel()

    @tasks.loop(minutes=5)
    async def update_invites(self):
        for guild in self.bot.guilds:
            try:
                self.invite_cache[guild.id] = await guild.invites()
            except:
                pass

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                self.invite_cache[guild.id] = await guild.invites()
            except:
                self.invite_cache[guild.id] = []

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            guild = member.guild
            invites_before = self.invite_cache.get(guild.id, [])
            invites_after = await guild.invites()
            self.invite_cache[guild.id] = invites_after

            used_invite = None
            for invite in invites_after:
                for old in invites_before:
                    if invite.code == old.code and invite.uses > old.uses:
                        used_invite = invite
                        break

            config = load_invite_config()
            log_channel_id = config.get(str(guild.id))
            if not log_channel_id:
                return

            log_channel = guild.get_channel(log_channel_id)
            if not log_channel:
                return

            if used_invite:
                inviter = used_invite.inviter
                await log_channel.send(f"📥 {member.mention} a fost invitat de {inviter.mention} folosind codul `{used_invite.code}`.")
            else:
                await log_channel.send(f"📥 {member.mention} a intrat, dar nu am putut detecta invitația.")
        except Exception as e:
            print(f"[Invite Tracker Error]: {e}")

    @app_commands.command(name="setinvitelog", description="Setează canalul unde să fie trimise logurile de invitații.")
    @app_commands.describe(channel="Canalul de loguri")
    async def setinvitelog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Doar administratorii pot folosi această comandă.", ephemeral=True)
            return

        config = load_invite_config()
        config[str(interaction.guild.id)] = channel.id
        save_invite_config(config)

        await interaction.response.send_message(f"✅ Canalul de loguri pentru invitații a fost setat la {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
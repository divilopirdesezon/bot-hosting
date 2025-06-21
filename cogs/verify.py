import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_FILE = "verify_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

class VerifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setverify", description="Configure the verification system")
    @app_commands.describe(channel="The channel where the verification message will be sent", role="The role to assign")
    async def setverify(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("⛔ Only the server owner can use this command.", ephemeral=True)
            return

        config = load_config()
        config[str(interaction.guild.id)] = {
            "channel_id": channel.id,
            "role_id": role.id
        }
        save_config(config)

        embed = discord.Embed(
            title="✅ Verification Required",
            description="Click the ✅ reaction to gain full access to the server.\n\n"
                        "After verifying, you will have full access to the channels and can interact with other members.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Verification handled by the server bot.")
        embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.add_field(name="Instructions", value="1. Click the ✅ reaction to verify yourself.\n"
                                                   "2. After verification, you will receive the member role.\n\n"
                                                   "Now that you're registered, say hello in chat and let’s get to know each other!")

        message = await channel.send(embed=embed)

        await message.add_reaction("✅")

        config[str(interaction.guild.id)]["message_id"] = message.id
        save_config(config)

        await interaction.response.send_message(f"✅ Verification system has been configured in {channel.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return

        config = load_config()
        for guild_id, data in config.items():
            if str(reaction.message.id) == str(data.get("message_id")):
                role = reaction.message.guild.get_role(data["role_id"])
                if role:
                    member = reaction.message.guild.get_member(user.id)
                    if member and role not in member.roles:
                        await member.add_roles(role)
                        await user.send("✅ You have been successfully verified! Welcome to the server! Now that you’re registered, say hi in the chat!")
                    else:
                        await user.send("✅ You are already verified.")
                else:
                    await user.send("⚠️ The verification role could not be found.")
                return

async def setup(bot):
    await bot.add_cog(VerifyCog(bot))
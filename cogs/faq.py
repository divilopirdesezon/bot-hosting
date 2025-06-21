import discord
from discord import app_commands
from discord.ext import commands
import os
import json

GUILD_ID = int(os.getenv("GUILD_ID"))
NOTIFY_ROLE_ID = int(os.getenv("NOTIFY_ROLE_ID"))
AUTHORIZED_USER_IDS = {753179409682399332, 1135863271363186768, 348516511352094720}

faq_data_file = "faq_data.json"

def load_faq_data():
    if not os.path.exists(faq_data_file):
        return []
    with open(faq_data_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_faq_data(data):
    with open(faq_data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class FAQCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_faq", description="Adaugă o întrebare frecventă (FAQ)")
    @app_commands.describe(question="Întrebarea completă", answer="Răspunsul", keywords="Cuvinte cheie separate prin virgulă")
    async def add_faq(self, interaction: discord.Interaction, question: str, answer: str, keywords: str):
        notify_role = discord.utils.get(interaction.guild.roles, id=NOTIFY_ROLE_ID)
        if notify_role not in interaction.user.roles and interaction.user.id not in AUTHORIZED_USER_IDS:
            await interaction.response.send_message("⛔ Nu ai permisiunea să adaugi FAQ-uri.", ephemeral=True)
            return

        faq_data = load_faq_data()
        new_id = 1 if not faq_data else max(entry['id'] for entry in faq_data) + 1
        keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]

        new_faq = {
            "id": new_id,
            "question": question,
            "answer": answer,
            "keywords": keyword_list
        }
        faq_data.append(new_faq)
        save_faq_data(faq_data)

        embed = discord.Embed(title="✅ FAQ Adăugat!", color=discord.Color.green())
        embed.add_field(name="Întrebare", value=question, inline=False)
        embed.add_field(name="Răspuns", value=answer, inline=False)
        embed.add_field(name="Cuvinte cheie", value=', '.join(keyword_list), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="faq", description="Caută un FAQ după cuvinte cheie sau ID")
    @app_commands.describe(query="ID-ul FAQ-ului sau cuvinte cheie")
    async def faq(self, interaction: discord.Interaction, query: str):
        faq_data = load_faq_data()
        results = []

        try:
            query_id = int(query)
            for entry in faq_data:
                if entry['id'] == query_id:
                    results.append(entry)
                    break
        except ValueError:
            search_terms = query.lower().split()
            for entry in faq_data:
                if any(term in kw for term in search_terms for kw in entry['keywords']) or \
                   any(term in entry['question'].lower() or term in entry['answer'].lower() for term in search_terms):
                    results.append(entry)

        if not results:
            await interaction.response.send_message("Niciun rezultat găsit.", ephemeral=True)
            return

        embed = discord.Embed(title="❓ Rezultate FAQ", color=discord.Color.blue())
        for entry in results[:5]:
            embed.add_field(
                name=f"FAQ #{entry['id']}: {entry['question']}",
                value=f"**Răspuns:** {entry['answer']}\n**Cuvinte cheie:** {', '.join(entry['keywords'])}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remove_faq", description="Șterge un FAQ după ID")
    @app_commands.describe(faq_id="ID-ul FAQ-ului")
    async def remove_faq(self, interaction: discord.Interaction, faq_id: int):
        notify_role = discord.utils.get(interaction.guild.roles, id=NOTIFY_ROLE_ID)
        if notify_role not in interaction.user.roles and interaction.user.id not in AUTHORIZED_USER_IDS:
            await interaction.response.send_message("⛔ Nu ai permisiunea să ștergi FAQ-uri.", ephemeral=True)
            return

        faq_data = load_faq_data()
        initial_len = len(faq_data)
        faq_data = [entry for entry in faq_data if entry['id'] != faq_id]

        if len(faq_data) == initial_len:
            await interaction.response.send_message(f"FAQ-ul cu ID {faq_id} nu a fost găsit.", ephemeral=True)
        else:
            save_faq_data(faq_data)
            await interaction.response.send_message(f"✅ FAQ #{faq_id} a fost șters.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(FAQCog(bot))
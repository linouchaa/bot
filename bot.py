from datetime import datetime
from urllib.parse import urljoin  # Ajout de l'import pour construire les URLs complètes

import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

# --- LIRE LE TOKEN DEPUIS token.txt ---
try:
    import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
except FileNotFoundError:
    print("Erreur : fichier token.txt non trouvé.")
    BOT_TOKEN = None

if not BOT_TOKEN:
    print("Erreur : le token Discord est vide dans token.txt.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)

prev_results = {}
started_tasks = {}

@bot.event
async def on_ready() -> None:
    current_time = datetime.now().strftime("%H:%M")
    print(f"[{current_time}] Bot en ligne.")

@bot.command(name="start")
async def start(ctx: commands.context.Context, arg: str = None) -> None:
    if ctx.author.id in started_tasks:
        embed = discord.Embed(title="Recherche déjà en cours.", color=0xc20000)
        await ctx.channel.send(embed=embed)
        return

    if arg is None:
        embed = discord.Embed(title="Aucune URL entrée.", color=0xc20000)
        await ctx.channel.send(embed=embed)
        return

    task = tasks.loop(minutes=1)(scrap)
    task.start(ctx, arg)
    started_tasks[ctx.author.id] = task
    prev_results[ctx.author.id] = set()

    current_time = datetime.now().strftime("%H:%M")
    print(f"[{current_time}] Recherche commencée.")
    embed = discord.Embed(title="Recherche commencée.", color=0x0f8000)
    await ctx.channel.send(embed=embed)

@bot.command(name="stop")
async def stop(ctx: commands.context.Context) -> None:
    if ctx.author.id not in started_tasks:
        embed = discord.Embed(title="Aucune recherche en cours.", color=0xc20000)
        await ctx.channel.send(embed=embed)
        return

    started_tasks[ctx.author.id].cancel()
    del started_tasks[ctx.author.id]
    del prev_results[ctx.author.id]

    current_time = datetime.now().strftime("%H:%M")
    print(f"[{current_time}] Recherche arrêtée.")
    embed = discord.Embed(title="Recherche arrêtée.", color=0xc20000)
    await ctx.channel.send(embed=embed)

# --- Fonction scrap modifiée ---
async def scrap(ctx: commands.context.Context, url: str) -> None:
    current_time = datetime.now().strftime("%H:%M")

    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"[{current_time}] Erreur lors du téléchargement de la page (Code: {response.status_code}).")
            # On ne notifie l'utilisateur que si l'erreur persiste, pour éviter le spam.
            return
    except requests.exceptions.RequestException as e:
        print(f"[{current_time}] Erreur de connexion: {e}")
        return

    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    elements = soup.find_all("div", class_="fr-card svelte-12dfls6")

    # On crée un ensemble pour stocker les résidences formatées
    current_residences = set()
    for element in elements:
        # On cherche la balise <p> qui contient la ville
        city_tag = element.find("p", class_="fr-card__detail")
        city = city_tag.text.strip() if city_tag else "Ville non précisée"

        # On cherche la balise <a> pour le nom et le lien
        a_tag = element.find("a")
        if a_tag:
            name = a_tag.text.strip()
            link = a_tag.get("href")
            
            # On s'assure que le lien est complet
            if link:
                full_link = urljoin(url, link)
            else:
                continue # On ignore si pas de lien

            # On formate la chaîne avec la ville, le nom et le lien
            current_residences.add(f"**{city}** - [{name}]({full_link})")

    if not current_residences:
        print(f"[{current_time}] Aucun logement trouvé sur la page.")
        prev_results[ctx.author.id] = set()
        return

    # On compare avec les résultats précédents pour trouver les nouveautés
    new_residences = current_residences - prev_results.get(ctx.author.id, set())

    if not new_residences:
        print(f"[{current_time}] Aucun nouveau logement trouvé.")
        return

    # On met à jour les résultats pour la prochaine vérification
    prev_results[ctx.author.id] = current_residences
    
    # On trie les nouveaux logements pour un affichage propre
    sorted_new_residences = sorted(list(new_residences))

    print(f"[{current_time}] Logement(s) trouvé(s) ({len(sorted_new_residences)}):")
    print("\n".join(f"- {res}" for res in sorted_new_residences))
    
    embed = discord.Embed(
        title=f"Nouveau(x) logement(s) trouvé(s) ({len(sorted_new_residences)})",
        description="\n".join(f"- {res}" for res in sorted_new_residences),
        color=0x0f8000
    )
    await ctx.author.send(embed=embed)

bot.run(BOT_TOKEN)
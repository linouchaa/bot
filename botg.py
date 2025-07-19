import os
import asyncio
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Affichage du répertoire et des fichiers (utile pour Railway)
print("Répertoire courant :", os.getcwd())
print("Liste des fichiers dans /app :", os.listdir("/app"))

# Récupération du token Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
print("Token:", BOT_TOKEN)

# Tâches en cours par utilisateur
tasks = {}

# Fonction de scraping
async def scrap(user_id: int, context: ContextTypes.DEFAULT_TYPE, url: str):
    while True:
        try:
            now = datetime.now().strftime("%H:%M")
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            elements = soup.find_all("div", class_="fr-card svelte-12dfls6")

            results = []
            for el in elements:
                city = el.find("p", class_="fr-card__detail")
                a_tag = el.find("a")
                if not a_tag:
                    continue
                name = a_tag.text.strip()
                link = urljoin(url, a_tag.get("href", "#"))
                city_name = city.text.strip() if city else "Ville inconnue"
                results.append(f"**{city_name}** - [{name}]({link})")

            if results:
                message = "\n".join(f"- {r}" for r in sorted(results))
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📋 *Résultats à {now}* – {len(results)} logement(s)\n{message}",
                    parse_mode="Markdown",
                    disable_notification=False
                )
                print(f"[{now}] {len(results)} logements envoyés.")
            else:
                print(f"[{now}] Aucun résultat trouvé.")

        except Exception as e:
            print(f"Erreur lors du scraping : {e}")

        await asyncio.sleep(3)  # Attente de 10 secondes

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in tasks:
        await update.message.reply_text("🔁 Surveillance déjà en cours.")
        return

    if not context.args:
        await update.message.reply_text("❗ Utilise `/start <url>` pour lancer.")
        return

    url = context.args[0]
    task = asyncio.create_task(scrap(user_id, context, url))
    tasks[user_id] = task
    await update.message.reply_text("✅ Surveillance démarrée. Tu recevras les résultats régulièrement.")

# Commande /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in tasks:
        tasks[user_id].cancel()
        del tasks[user_id]
        await update.message.reply_text("⛔ Surveillance arrêtée.")
    else:
        await update.message.reply_text("⚠️ Aucun processus de surveillance actif.")

# Lancer le bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
        app.add_handler(CommandHandler("groupid", groupid))


    print("🚀 Bot Telegram lancé.")
    app.run_polling()


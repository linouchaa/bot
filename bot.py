import os
import asyncio
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("Token:", BOT_TOKEN)

prev_results = {}
tasks = {}

# Fonction principale de scraping
async def scrap(user_id: int, context: ContextTypes.DEFAULT_TYPE, url: str):
    while True:
        try:
            now = datetime.now().strftime("%H:%M")
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            elements = soup.find_all("div", class_="fr-card svelte-12dfls6")

            found = set()
            for el in elements:
                city = el.find("p", class_="fr-card__detail")
                a_tag = el.find("a")
                if not a_tag: continue
                name = a_tag.text.strip()
                link = urljoin(url, a_tag.get("href", "#"))
                city_name = city.text.strip() if city else "Ville inconnue"
                found.add(f"**{city_name}** - [{name}]({link})")

            new_items = found - prev_results.get(user_id, set())
            if new_items:
                prev_results[user_id] = found
                message = "\n".join(f"- {r}" for r in sorted(new_items))
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🚨 *Nouveaux logements ({len(new_items)})* 🚨\n{message}",
                    parse_mode="Markdown",
                    disable_notification=False  # 🔔 sonnerie activée
                )
                print(f"[{now}] Nouveaux logements trouvés : {len(new_items)}")
            else:
                print(f"[{now}] Aucun changement.")

        except Exception as e:
            print(f"Erreur : {e}")

        await asyncio.sleep(20)

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in tasks:
        await update.message.reply_text("🔁 Déjà en cours.")
        return

    if not context.args:
        await update.message.reply_text("❗ Envoie une URL après `/start`")
        return

    url = context.args[0]
    task = asyncio.create_task(scrap(user_id, context, url))
    tasks[user_id] = task
    prev_results[user_id] = set()
    await update.message.reply_text("✅ Surveillance lancée. Tu recevras une alerte si quelque chose change.")

# Commande /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in tasks:
        tasks[user_id].cancel()
        del tasks[user_id]
        del prev_results[user_id]
        await update.message.reply_text("⛔ Surveillance arrêtée.")
    else:
        await update.message.reply_text("⚠️ Aucune surveillance en cours.")

# Lancer le bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))

    print("🚀 Bot Telegram en ligne.")
    app.run_polling()

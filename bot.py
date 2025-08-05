import json
import feedparser
import re
import random
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

# --- Чтение конфига ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN = config["telegram_token"]
ADMIN_ID = config["admin_id"]
KEYWORDS = [kw.lower() for kw in config["keywords"]]
RSS_RUSSIA = config["rss_feeds_russia"]
RSS_INT = config["rss_feeds_international"]
RATIO_RU = config["ratio_russia"]
RATIO_INT = config["ratio_international"]

bot = Bot(token=TOKEN)

def fetch_news(feed_urls):
    news = []
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                summary = entry.get("summary", "")
                link = entry.link
                text_to_check = f"{title} {summary}".lower()
                if any(re.search(rf"\b{kw}\b", text_to_check) for kw in KEYWORDS):
                    news.append({
                        "title": title,
                        "summary": summary[:150] + "...",
                        "link": link
                    })
        except Exception as e:
            print(f"Ошибка при парсинге {url}: {e}")
    return news

def format_news(russian_news, international_news):
    ru_count = int(len(russian_news) * RATIO_RU)
    int_count = int(len(international_news) * RATIO_INT)
    selected_ru = random.sample(russian_news, min(ru_count, len(russian_news)))
    selected_int = random.sample(international_news, min(int_count, len(international_news)))
    all_news = selected_ru + selected_int
    random.shuffle(all_news)
    text = "Еженедельная подборка новостей:\n\n"
    for i, item in enumerate(all_news, 1):
        text += f"{i}. [{item['title']}]({item['link']})\n{item['summary']}\n\n"
    return text

def send_digest(context: CallbackContext):
    ru_news = fetch_news(RSS_RUSSIA)
    int_news = fetch_news(RSS_INT)
    if not ru_news and not int_news:
        context.bot.send_message(chat_id=ADMIN_ID, text="Новостей по ключевым словам не найдено.")
        return
    message = format_news(ru_news, int_news)
    context.bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode="Markdown")

def manual_digest(update: Update, context: CallbackContext):
    send_digest(context)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("digest", manual_digest))

    scheduler = BackgroundScheduler()
    schedule_time = config["schedule_time"].split(":")
    scheduler.add_job(send_digest, 'cron', day_of_week=config["schedule_day"],
                      hour=int(schedule_time[0]), minute=int(schedule_time[1]), args=[updater.job_queue])
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

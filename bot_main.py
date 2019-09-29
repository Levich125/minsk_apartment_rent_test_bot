import json
from telegram.ext import Updater, CommandHandler, MessageHandler,    Filters, InlineQueryHandler
from onliner_scraper import OnlinerScraper
from realt_scraper import RealtScraper
from kvartirant_scraper import KvartirantScraper

OS = OnlinerScraper()
RS = RealtScraper()
KS = KvartirantScraper()

config_params = json.load(open("./config_and_cookies.json", 'r'))

KEY = config_params['bot_key']


def get_apartments_onliner(bot, job):
    cnt = next(OS.main())
    if cnt:
        job.context.message.reply_text(cnt)


def get_apartments_realt(bot, job):
    cnt = next(RS.main())
    if cnt:
        job.context.message.reply_text('REALT UPDATE\n' + cnt[:2000])


def get_apartments_kvartirant(bot, job):
    cnt = next(KS.main())
    if cnt:
        job.context.message.reply_text('KVARTIRANT UPDATE\n' + cnt[:5000])


def start(bot, update, job_queue):
    update.message.reply_text('bot active')
    job = job_queue.run_repeating(get_apartments_onliner, 10, context=update)
    job = job_queue.run_repeating(get_apartments_realt, 60, context=update)
    job = job_queue.run_repeating(get_apartments_kvartirant, 60, context=update)


def stop(bot, update, job_queue):
    update.message.reply_text('bot disabled')
    job = job_queue.stop()


def main():
    updater = Updater(KEY)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start, pass_job_queue=True))
    dp.add_handler(CommandHandler("stop", stop, pass_job_queue=True))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

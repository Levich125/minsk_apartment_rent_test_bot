# telegram:
# https://medium.freecodecamp.org/learn-to-build-your-first-bot-in-telegram-with-python-4c99526765e4
# https://github.com/python-telegram-bot/python-telegram-bot

from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
import requests
import json

config_params = json.load(open("./config_and_cookies.json", 'r'))

KEY = config_params['bot_key']
MASTER = config_params['master']


def get_url():
    contents = requests.get('https://random.dog/woof.json').json()
    url = contents['url']
    return url


def bop(bot, update):
    url = get_url()
    chat_id = update.message.chat_id
    bot.send_photo(chat_id=chat_id, photo=url)
    # bot.sendMessage(chat_id=chat_id, )
    update.message.reply_text(chat_id)


def echo(bot, update):
    print('echo')
    update.message.reply_text('Hell no')


def start(bot, update):
    update.message.reply_text('Hi!')


def main():
    updater = Updater(KEY)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler('bop', bop))
    dp.add_handler(MessageHandler(Filters.text, echo))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

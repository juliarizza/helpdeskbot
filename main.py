import os.path
import telegram
import redis
import gettext
import configparser

from functools import wraps
from telegram.ext import Updater, CommandHandler, MessageHandler,\
                         RegexHandler, Filters

# Configuring bot
config = configparser.ConfigParser()
config.read_file(open('config.ini'))

# Connecting to Telegram API
# Updater retrieves information and dispatcher connects commands
updater = Updater(token=config['DEFAULT']['token'])
dispatcher = updater.dispatcher

# Config the translations
lang_pt = gettext.translation("pt_BR", localedir="locale", languages=["pt_BR"])
def _(msg): return msg

# Connecting to Redis db
db = redis.StrictRedis(host=config['DB']['host'],
                       port=config['DB']['port'],
                       db=config['DB']['db'])


def user_language(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        lang = db.get(str(update.message.chat_id))

        global _

        if lang == b"pt_BR":
            # If language is pt_BR, translates
            _ = lang_pt.gettext
        else:
            # If not, leaves as en_US
            def _(msg): return msg

        result = func(bot, update, *args, **kwargs)
        return result
    return wrapped


@user_language
def start(bot, update):
    """
        Shows an welcome message and help info about the available commands.
    """
    me = bot.get_me()

    # Welcome message
    msg = _("Hello!\n")
    msg += _("I'm {0} and I came here to help you.\n").format(me.first_name)
    msg += _("What would you like to do?\n\n")
    msg += _("/support - Opens a new support ticket\n")
    msg += _("/settings - Settings of your account\n\n")

    # Commands menu
    main_menu_keyboard = [[telegram.KeyboardButton('/support')],
                          [telegram.KeyboardButton('/settings')]]
    reply_kb_markup = telegram.ReplyKeyboardMarkup(main_menu_keyboard,
                                                   resize_keyboard=True,
                                                   one_time_keyboard=True)

    # Send the message with menu
    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     reply_markup=reply_kb_markup)


@user_language
def support(bot, update):
    """
        Sends the support message. Some kind of "How can I help you?".
    """
    bot.send_message(chat_id=update.message.chat_id,
                     text=_("Please, tell me what you need support with :)"))


@user_language
def support_message(bot, update):
    """
        Receives a message from the user.

        If the message is a reply to the user, the bot speaks with the user
        sending the message content. If the message is a request from the user,
        the bot forwards the message to the support group.
    """
    if update.message.reply_to_message and \
       update.message.reply_to_message.forward_from:
        # If it is a reply to the user, the bot replies the user
        bot.send_message(chat_id=update.message.reply_to_message
                         .forward_from.id,
                         text=update.message.text)
    else:
        # If it is a request from the user, the bot forwards the message
        # to the group
        bot.forward_message(chat_id=int(config['DEFAULT']['support_chat_id']),
                            from_chat_id=update.message.chat_id,
                            message_id=update.message.message_id)
        bot.send_message(chat_id=update.message.chat_id,
                         text=_("Give me some time to think. Soon I will return to you with an answer."))


@user_language
def settings(bot, update):
    """
        Configure the messages language using a custom keyboard.
    """
    # Languages message
    msg = _("Please, choose a language:\n")
    msg += "en_US - English (US)\n"
    msg += "pt_BR - Português (Brasil)\n"

    # Languages menu
    languages_keyboard = [
        [telegram.KeyboardButton('en_US - English (US)')],
        [telegram.KeyboardButton('pt_BR - Português (Brasil)')]
    ]
    reply_kb_markup = telegram.ReplyKeyboardMarkup(languages_keyboard,
                                                   resize_keyboard=True,
                                                   one_time_keyboard=True)

    # Sends message with languages menu
    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     reply_markup=reply_kb_markup)


@user_language
def kb_settings_select(bot, update, groups):
    """
        Updates the user's language based on it's choice.
    """
    chat_id = update.message.chat_id
    language = groups[0]

    # Available languages
    languages = {"pt_BR": "Português (Brasil)",
                 "en_US": "English (US)"}

    # If the language choice matches the expression AND is a valid choice
    if language in languages.keys():
        # Sets the user's language
        db.set(str(chat_id), language)
        bot.send_message(chat_id=chat_id,
                         text=_("Language updated to {0}")
                         .format(languages[language]))
    else:
        # If it is not a valid choice, sends an warning
        bot.send_message(chat_id=chat_id,
                         text=_("Unknown language! :("))


@user_language
def unknown(bot, update):
    """
        Placeholder command when the user sends an unknown command.
    """
    msg = _("Sorry, I don't know what you're asking for.")
    bot.send_message(chat_id=update.message.chat_id,
                     text=msg)

# creating handlers
start_handler = CommandHandler('start', start)
support_handler = CommandHandler('support', support)
support_msg_handler = MessageHandler([Filters.text], support_message)
settings_handler = CommandHandler('settings', settings)
get_language_handler = RegexHandler('^([a-z]{2}_[A-Z]{2}) - .*',
                                    kb_settings_select,
                                    pass_groups=True)
help_handler = CommandHandler('help', start)
unknown_handler = MessageHandler([Filters.command], unknown)

# adding handlers
dispatcher.add_handler(start_handler)
dispatcher.add_handler(support_handler)
dispatcher.add_handler(settings_handler)
dispatcher.add_handler(get_language_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(unknown_handler)

# Message handler must be the last one
dispatcher.add_handler(support_msg_handler)

# to run this program:
# updater.start_polling()
# to stop it:
# updater.stop()

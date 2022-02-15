import logging
import requests
import urllib.parse
import os
from dotenv import load_dotenv

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)
load_dotenv()

API_URL = os.environ.get("API_URL")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")


SERVERS, DURATION, GOTDURATION = range(3)


def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation"""
    reply_keyboard = [['Mute', 'Unmute', 'Cancel']]

    update.message.reply_text(
        'Peertube UptimeBot '
        'Send /cancel to stop talking to me.\n\n'
        'What do you want to do?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Command'
        ),
    )

    return SERVERS


def server_list(update: Update, context: CallbackContext) -> int:
    """Get servers and filter out muted/unmuted"""
    context.user_data["selected_command"] = update.message.text
    selected_command = context.user_data["selected_command"]
    logger.info("Command: %s", selected_command)

    if selected_command=="Cancel":
        cancel(update,context)
        return ConversationHandler.END


    try:
        reply_keyboard = []

        r = requests.get(
            API_URL + "/Peertube/List" 
        )
        data = r.json()
        for server in data:
            if selected_command == "Mute" and server["mutedTo"]:
                continue
            if selected_command == "Unmute" and not server["mutedTo"]:
                continue
            parsed_url = urllib.parse.urlparse(server["url"])
            t = []
            t.append(parsed_url.netloc)
            reply_keyboard.append(t)

    except Exception as ex:
        logger.info("error: %s", ex.message)
        return ""



    update.message.reply_text(
        f'Select server to {selected_command}',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Server'
        ),
    )

    return DURATION

def duration(update: Update, context: CallbackContext) -> int:
    """Stores the info about the selected_server."""
    context.user_data["selected_server"] = update.message.text
    selected_server = context.user_data["selected_server"]
    logger.info("selected_server: %s", selected_server)



    if context.user_data["selected_command"]=="Unmute":
        context.user_data["selected_duration"] = ""
        response = executecommand(context)

        update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )

        context.user_data["selected_command"] = ""
        context.user_data["selected_server"] = ""

        return ConversationHandler.END


    reply_keyboard = [['1 min', '10 min'],['30 min','60 min']]

    update.message.reply_text(
        'Select mute duration',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Duration'
        ),
    )

    return GOTDURATION

def gotduration(update: Update, context: CallbackContext) -> int:
    """Stores the info about the selected_duration."""
    context.user_data["selected_duration"] = update.message.text
    selected_duration = context.user_data["selected_duration"]
    logger.info("selected_duration: %s", selected_duration)

    response = executecommand(context)
    update.message.reply_text(
        response, reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    logger.info("User canceled the conversation.")
    update.message.reply_text(
        'Bye!', reply_markup=ReplyKeyboardRemove()
    )
    # Erase all session info
    context.user_data["selected_command"] = ""
    context.user_data["selected_server"] = ""
    context.user_data["selected_duration"] = ""

    return ConversationHandler.END

def executecommand(context: CallbackContext):
    logger.info("EXECUTE COMMAND: %s %s %s", context.user_data["selected_command"], context.user_data["selected_server"], context.user_data["selected_duration"])


    context.user_data["selected_command"] = ""
    context.user_data["selected_server"] = ""
    context.user_data["selected_duration"] = ""

    # TODO uncomment in production!!!
    '''
    command  = API_URL + "/Peertube/" + context.user_data["selected_command"] + "?url=" + context.user_data["selected_server"]
    if context.user_data["selected_command"] == "Mute":
        t = context.user_data["selected_duration"].split()[0]
        command = command + "&minutes=" + t

    payload={}
    headers = {
    'accept': '*/*'
    }

    response = requests.request("POST", command, headers=headers, data=payload)

    return response.text
    '''

    # TODO comment in production!!!
    return "Executed!"


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states
    conv_handler = ConversationHandler(
        #entry_points=[CommandHandler('start', start)],
        entry_points=[MessageHandler(Filters.text, start)],
        states={
            SERVERS: [MessageHandler(Filters.regex('^(Mute|Unmute|Cancel)$'), server_list)],
            DURATION: [MessageHandler(Filters.text, duration)],
            GOTDURATION: [MessageHandler(Filters.text, gotduration)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
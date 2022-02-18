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
DEBUG = os.environ.get("DEBUG")


API, SERVERS, DURATION, GOTDURATION, GOTSERVERNAME = range(5)

def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation"""
    # Erase all session info
    erase_context(context)

    user = update.message.from_user
    logger.info("%s: %s %s %s", user.first_name, user.last_name, user.username, user.id)

    reply_keyboard = [['Node'], ['NodeProxy'],['Peertube'],['Cancel']]

    update.message.reply_text(
        'Peertube UptimeBot '
        'Send /cancel to stop talking to me.\n\n'
        'What do you want to do?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='API'
        ),
    )

    return API

def commands(update: Update, context: CallbackContext) -> int:
    """Select command"""
    context.user_data["selected_api"] = update.message.text

    if update.message.text=="Cancel":
        cancel(update,context)
        return ConversationHandler.END
        
    reply_keyboard = [['Mute', 'Unmute'],['Add','Delete'],['Cancel']]

    update.message.reply_text(
        'Send /cancel to stop talking to me.\n\n'
        'Select command',
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

    if selected_command=="Add":
        update.message.reply_text('Add server',  reply_markup=ReplyKeyboardRemove())
        return GOTSERVERNAME

    try:
        reply_keyboard = []

        r = requests.get(
            API_URL + "/"+context.user_data["selected_api"]+"/List" 
        )
        data = r.json()
        for server in data:
            if selected_command == "Mute" and server["mutedTo"]:
                continue
            if selected_command == "Unmute" and not server["mutedTo"]:
                continue
            # For Delete command - take all servers

            parsed_url = urllib.parse.urlparse(server["url"])
            t = []
            t.append(parsed_url.netloc)
            reply_keyboard.append(t)

    except Exception as ex:
        logger.info("error: %s", ex.message)
        return ConversationHandler.END



    update.message.reply_text(
        f'Select server to {selected_command}',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Server'
        ),
    )
    if selected_command == "Delete" :
        return GOTSERVERNAME

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
        context.user_data["selected_api"] = ""

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
    erase_context(context)


    return ConversationHandler.END


def gotservername(update: Update, context: CallbackContext) -> int:
    """Stores the info about the selected_server."""
    context.user_data["selected_server"] = update.message.text
    selected_server = context.user_data["selected_server"]
    logger.info("selected_server: %s", selected_server)

    response = executecommand(context)
    update.message.reply_text(
        response, reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def executecommand(context: CallbackContext):
    msg= f"EXECUTE : {context.user_data['selected_api']}, {context.user_data['selected_command']}, {context.user_data['selected_server']}, {context.user_data['selected_duration']}"
    logger.info(msg)

    command  = API_URL + "/"+context.user_data["selected_api"]+"/" + context.user_data["selected_command"] + "?url=" + context.user_data["selected_server"]
    if context.user_data["selected_command"] == "Mute":
        t = context.user_data["selected_duration"].split()[0]
        command = command + "&minutes=" + t

    payload={}
    headers = {
        'accept': '*/*'
    }

    if DEBUG:
       return msg 

    # Production
    try:
        response = requests.request("POST", command, headers=headers, data=payload)
    except Exception as ex:
        logger.info("error: %s", ex.message)
        return ex.message

    if response.status_code != 200:
        return f'Error: {response.status_code}: {response.text}'

    if response.text == "":
        return msg

    return response.text

def erase_context(context: CallbackContext):
    context.user_data["selected_command"] = ""
    context.user_data["selected_server"] = ""
    context.user_data["selected_duration"] = ""
    context.user_data["selected_api"] = ""

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
            API: [MessageHandler(Filters.regex('^(Node|NodeProxy|Peertube|Cancel)$'), commands)],
            SERVERS: [MessageHandler(Filters.regex('^(Mute|Unmute|Add|Delete|Cancel)$'), server_list)],
            DURATION: [MessageHandler(Filters.text, duration)],
            GOTDURATION: [MessageHandler(Filters.text, gotduration)],
            GOTSERVERNAME: [MessageHandler(Filters.text, gotservername)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()

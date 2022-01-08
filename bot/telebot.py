import logging
import datetime
import configparser
import argparse
import inspect
import re
from mwt import MWT
from dbhelper import DBHelper
from telegram.ext import CommandHandler, Updater

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

db = DBHelper()

parser = argparse.ArgumentParser(
    description="Bot for helping in administration in DevOps groups in TG"
)

parser.add_argument(
    "-b",
    "--bottoken",
    dest="bottoken",
    type=str,
    default="1231423",
    help="Bot token for TG API",
)
parser.add_argument(
    "-e",
    "--environment",
    dest="environment",
    type=str,
    default="config.ini",
    help="Environment for bot",
)

args = parser.parse_args()
bottoken = args.bottoken
environment = args.environment

config = configparser.ConfigParser()
config.read(environment)

updater = Updater(token=bottoken, use_context=True)
dispatcher = updater.dispatcher


# Get admins list
@MWT(timeout=60 * 60)
def get_admin_ids(context, chat_id):
    """Returns a list of admin IDs for a given chat. Results are cached for 1 hour."""
    return [admin.user.id for admin in context.bot.get_chat_administrators(chat_id)]


# User commands


# Administrator commands

# - Warn some user
def warn(update, context, args):
    user_id = update.message.reply_to_message.from_user.id
    user_username = update.message.reply_to_message.from_user.username
    admin_username = re.sub("[_]", "\_", update.message.from_user.username)
    warn = int(0)
    section = str(update.message.chat.id)
    in_section = section in config.sections()
    command_name = inspect.currentframe().f_code.co_name
    feature_flag = config.get(section, command_name) == "on"
    admins = update.message.from_user.id in get_admin_ids(
        context, update.message.chat_id
    )
    if in_section and feature_flag and admins:
        db.add_user(user_id, user_username, warn)
        db.add_warn(user_id, user_username, warn)
        warn_text = db.count_warn(user_id)
        reason = str(" ".join(args))
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="@"
            + str(user_username)
            + " your warn count: "
            + str(warn_text)
            + str("/3.")
            + "If you get 3 warns you will be banned for 3 days."
            + "\n"
            + "Admin: @"
            + admin_username
            + "\n"
            + "Reason: "
            + reason,
            reply_to_message_id=update.message.message_id,
        )
        context.bot.deleteMessage(
            chat_id=update.message.chat.id, message_id=update.message.message_id
        )
    if warn_text >= 3:
        db.delete_warn(user_id, user_username, warn)
        context.bot.restrict_chat_member(
            chat_id=update.message.chat_id,
            user_id=update.message.reply_to_message.from_user.id,
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            until_date=datetime.datetime.now() + datetime.timedelta(days=3),
        )


warn_handler = CommandHandler("warn", warn, pass_args=True, run_async=True)
dispatcher.add_handler(warn_handler)


# - Unwarn user
def unwarn(update, context):
    user_id = update.message.reply_to_message.from_user.id
    user_username = update.message.reply_to_message.from_user.username
    warn = int(0)
    section = str(update.message.chat.id)
    in_section = section in config.sections()
    command_name = inspect.currentframe().f_code.co_name
    feature_flag = config.get(section, command_name) == "on"
    admins = update.message.from_user.id in get_admin_ids(
        context, update.message.chat_id
    )
    if in_section and feature_flag and admins:
        db.unwarn(user_id, user_username, warn)
        warn_text = db.count_warn(user_id)
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="@"
            + str(update.message.reply_to_message.from_user.username)
            + " your warn count: "
            + str(warn_text)
            + str("/3.")
            + "If you get 3 warns you will be banned for 3 days.",
            reply_to_message_id=update.message.message_id,
        )
        context.bot.deleteMessage(
            chat_id=update.message.chat.id, message_id=update.message.message_id
        )


unwarn_handler = CommandHandler("unwarn", unwarn, run_async=True)
dispatcher.add_handler(unwarn_handler)


def main():
    db.setup()


if __name__ == "__main__":
    main()
updater.start_polling()

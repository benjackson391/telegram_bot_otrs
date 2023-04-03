import logging

from decouple import config

from tgbot import constants, helper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

log = logging.getLogger(__name__)


def debug(msg):
    if config("DEBUG"):
        logging.info(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    debug("def common.start")

    if not context.user_data.get(constants.USER_IS_AUTHORIZED):
        context.user_data[constants.USER_IS_AUTHORIZED] = False
        context.user_data[constants.CUSTOMER_USER_LOGIN] = ""

        auth = helper._otrs_request(
            "auth", {"TelegramLogin": update.message.from_user.username}
        )
        if "Error" not in auth:
            context.user_data[constants.USER_IS_AUTHORIZED] = True
            context.user_data[constants.CUSTOMER_USER_LOGIN] = auth["CustomerUserLogin"]

    text = (
        "Вы можете создать, обновить или проверить статус вашей заявки. "
        "Для остановки бота просто напишите /stop"
    )

    not_auth_buttons = [
        InlineKeyboardButton(
            text="Авторизоваться", callback_data=str(constants.AUTHORISATION)
        ),
    ]

    auth_buttons = [
        InlineKeyboardButton(
            text="Новая заявка", callback_data=str(constants.NEW_TICKET)
        ),
        InlineKeyboardButton(
            text="Проверить статус", callback_data=str(constants.CHECK_TICKET)
        ),
        InlineKeyboardButton(
            text="Обновить заявку", callback_data=str(constants.UPDATE_TICKET)
        ),
    ]

    keyboard = InlineKeyboardMarkup(
        list(
            map(
                lambda b: [b],
                auth_buttons
                if context.user_data[constants.USER_IS_AUTHORIZED]
                else not_auth_buttons,
            )
        )
    )

    if context.user_data.get(constants.START_OVER):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "Добро пожаловать в систему постановки заявок EFSOL"
        )
        await update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[constants.START_OVER] = False
    return constants.SELECTING_ACTION


async def end_second_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    debug("def common.end_second_level")
    context.user_data[constants.START_OVER] = True
    await start(update, context)

    return constants.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("До встречи.")

    return constants.END

import logging, random, re

from tgbot import common, constants, helper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


async def ask_for_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, current_step=""
) -> str:
    logging.debug("def ask_for_input")

    if not current_step:
        current_step = update.callback_query.data

    # update ticket
    if bool(re.match("^COMMENT_\d+$", current_step)):
        current_step = str(constants.UPDATE_TICKET)
        context.user_data[constants.TICKET_ID] = update.callback_query.data.split("_")[
            -1
        ]

    context.user_data[constants.CURRENT_STEP] = current_step

    if context.user_data[constants.CONFIRMATION_CODE_STATUS] == 0:
        confirmation_code_text = (
            "Для подтверждения адреса электронной почты введите код из письма"
        )
    elif context.user_data[constants.CONFIRMATION_CODE_STATUS] == 1:
        confirmation_code_text = "Код неверный, попробуйте еще раз"
    else:
        confirmation_code_text = "Код верный"
        context.user_data[constants.USER_IS_AUTHORIZED] = True

        confirm_account = helper._otrs_request(
            "confirm_account",
            {
                "Email": context.user_data[constants.EMAIL],
                "TelegramLogin": update.message.from_user.username,
            },
        )

        await common.start(update, context)
        return constants.END

    text_map = {
        str(
            constants.AUTHORISATION
        ): f"Введите свой адрес электронный почты, который зарегистрирован в OTRS",
        str(constants.CONFIRMATION_CODE): confirmation_code_text,
        str(constants.UPDATE_TICKET): f"Введите комментарий",
    }

    text = text_map[current_step]

    if context.user_data[constants.EMAIL_NOT_FOUND]:
        text = f"Адрес {context.user_data[constants.EMAIL]} не найден в OTRS, попробуйте другой адрес"
        context.user_data[constants.EMAIL_NOT_FOUND] = False

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text)
    else:
        await update.message.reply_text(text=text)

    return constants.TYPING


async def save_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.debug("def save_input")

    input_text = update.message.text

    if context.user_data[constants.CURRENT_STEP] == str(constants.AUTHORISATION):
        logging.debug("AUTHORISATION")
        context.user_data[constants.EMAIL] = input_text
        return await authorisation(update, context)
    elif context.user_data[constants.CURRENT_STEP] == str(constants.CONFIRMATION_CODE):
        logging.debug(f"CONFIRMATION_CODE")
        context.user_data[constants.CONFIRMATION_CODE_STATUS] = (
            2
            if int(context.user_data[constants.CONFIRMATION_CODE]) == int(input_text)
            else 1
        )
        return await ask_for_input(update, context, str(constants.CONFIRMATION_CODE))


async def authorisation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.debug("def authorisation")

    context.user_data[constants.CONFIRMATION_CODE] = random.randint(100000, 999999)
    confirm_account = helper._otrs_request(
        "confirm_account",
        {
            "Email": context.user_data[constants.EMAIL],
            "Code": context.user_data[constants.CONFIRMATION_CODE],
        },
    )

    if not bool(confirm_account["data"]):
        context.user_data[constants.EMAIL_NOT_FOUND] = True
        context.user_data[constants.CURRENT_STEP] = str(constants.AUTHORISATION)
    else:
        context.user_data[constants.EMAIL_NOT_FOUND] = False
        context.user_data[constants.CURRENT_STEP] = str(constants.CONFIRMATION_CODE)

    return await ask_for_input(
        update, context, context.user_data[constants.CURRENT_STEP]
    )

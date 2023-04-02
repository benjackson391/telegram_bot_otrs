import logging, random, re

from tgbot import common, constants, helper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


async def entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, current_step=""
) -> str:
    common.debug("def auth.entry")

    text = "Введите свой адрес электронный почты, который зарегистрирован в OTRS"

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)

    return constants.EMAIL


async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def auth.email_handler")
    email = update.message.text
    code = random.randint(100000, 999999)

    context.user_data[constants.EMAIL] = email
    context.user_data[constants.CONFIRMATION_CODE] = code

    confirm_account = helper._otrs_request(
        "confirm_account",
        {
            "Email": email,
            "Code": code,
        },
    )

    text = f"""Адрес {email} не найден в OTRS!\nПопробуйте другой адрес"""
    ret = constants.EMAIL

    if confirm_account and confirm_account.get("sent"):
        text = f"""Проверочный код отправлен на {email}\nДля подтверждения адреса электронной почты введите код из письма"""
        ret = constants.CONFIRMATION_CODE

    await update.message.reply_text(text=text)
    return ret


async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def auth.code_handler")
    code = update.message.text

    text = "Код неверный, попробуйте еще раз"
    ret = constants.CONFIRMATION_CODE

    if context.user_data[constants.CONFIRMATION_CODE] == int(code):
        text = "Код верный"
        ret = constants.SELECTING_ACTION
        context.user_data[constants.USER_IS_AUTHORIZED] = True  # ?

        confirm_account = helper._otrs_request(
            "confirm_account",
            {
                "Email": context.user_data[constants.EMAIL],
                "TelegramLogin": update.message.from_user.username,
            },
        )

        if not confirm_account or confirm_account.get("updated") != 1:
            text += ", но не удалось обновить telegram логин у пользователя,\nобратитесь к администратору"

    await update.message.reply_text(
        text=text, reply_markup=InlineKeyboardMarkup([helper.get_return_button()])
    )
    return ret

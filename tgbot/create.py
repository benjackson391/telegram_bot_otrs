import base64, logging, io, os, sys

from tgbot import helper, constants
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)

buffer = io.BytesIO()


async def new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def create.new_ticket")

    context.user_data[constants.NEW_TICKET] = {}

    keyboard = InlineKeyboardMarkup([helper.get_return_button()])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Введите тему заявки",
        reply_markup=keyboard,
    )
    return constants.SUBJECT


async def subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def create.subject_handler")

    context.user_data[constants.NEW_TICKET][constants.SUBJECT] = update.message.text

    await update.message.reply_text(text="Введите описание заявки")

    return constants.BODY


async def body_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def create.body_handler")
    context.user_data[constants.NEW_TICKET][constants.BODY] = update.message.text

    buttons = [
        [
            InlineKeyboardButton(text="Да", callback_data=str(constants.UPLOAD)),
            InlineKeyboardButton(text="Нет", callback_data=str(constants.CREATE)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        text="Прикрепить файл?",
        reply_markup=keyboard,
    )
    return constants.ATTACHMENT


async def attachment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def create.attachment_upload")

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Приложите файл до 20Mb")
    return constants.CREATE_WITH_ATTACHMENT


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def create.create")

    new_ticket = context.user_data.get(constants.NEW_TICKET)

    # TODO fix this place
    customer_user = context.user_data.get(constants.CUSTOMER_USER_LOGIN)
    if not customer_user:
        customer_user = context.user_data.get(constants.EMAIL)

    json = {
        "Ticket": {
            "Title": new_ticket[constants.SUBJECT],
            "Queue": "spam",
            "TypeID": 3,  # Запрос на обслуживание
            "CustomerUser": customer_user,
            "StateID": 1,  # new
            "PriorityID": 3,  # normal
            "OwnerID": 1,  # admin
            "LockID": 1,  # unlick
        },
        "Article": {
            "CommunicationChannel": "Internal",
            "SenderType": "customer",
            "Charset": "utf-8",
            "MimeType": "text/plain",
            "From": customer_user,
            "Subject": new_ticket[constants.SUBJECT],
            "Body": new_ticket[constants.BODY],
        },
    }

    if update.message and update.message.document:
        new_file = await context.bot.get_file(update.message.document.file_id)

        await new_file.download_to_memory(buffer)

        content = base64.b64encode(buffer.getvalue()).decode("utf-8")

        json["Attachment"] = {
            "Content": content,
            "ContentType": update.message.document.mime_type,
            "Filename": update.message.document.file_name,
        }

    # заглушка для тестирования
    # ticket_create = {"TicketNumber": 123}
    ticket_create = helper._otrs_request("create", json)

    keyboard = InlineKeyboardMarkup([helper.get_return_button()])

    text = f"Ваша обращение принято. Номер заявки #{ticket_create['TicketNumber']}"
    helper._redis_update(customer_user, [ticket_create["TicketNumber"]])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    return constants.ATTACHMENT

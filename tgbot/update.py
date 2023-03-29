import logging, base64, io
from tgbot import check, constants, helper

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)
buffer = io.BytesIO()

async def update_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def update.update_tickets")

    context.user_data[constants.TICKETS] = helper.collect_tickets(
        context.user_data[constants.CUSTOMER_USER_LOGIN]
    )

    buttons = helper.build_ticket_buttons(context.user_data[constants.TICKETS])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Выберите заявку, которую необходимо обновить", reply_markup=keyboard
    )

    return constants.SHOW_TICKETS


async def update_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def update.update_ticket")

    context.user_data[constants.UPDATE_TICKET] = {}

    ticket_id = update.callback_query.data.split("_")[-1]

    context.user_data[constants.UPDATE_TICKET][constants.TICKET_ID] = ticket_id

    ticket = context.user_data.get(constants.TICKETS)[ticket_id]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["Owner"]}
        Статус: {ticket["State"]}
        Предельное время решения: {'SolutionTimeDestinationDate' in ticket and ticket["SolutionTimeDestinationDate"] or None}
    """

    buttons = [
        [
            InlineKeyboardButton(
                text="Добавьте комментарий",
                callback_data=str(constants.COMMENT),
            )
        ],
        helper.get_return_button(),
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return constants.UPDATE_TICKET


async def add_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def add_comment")

    context.user_data[constants.TICKET_ID] = update.callback_query.data.split("_")[-1]

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Введите комментарий")

    return constants.ATTACHMENT


async def comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def update.comment_handler")
    context.user_data[constants.UPDATE_TICKET][constants.COMMENT] = update.message.text

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


async def update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.debug("def update.update")

    to_update = context.user_data.get(constants.UPDATE_TICKET)

    json = {
        "TicketID": to_update.get(constants.TICKET_ID),
        "Article": {
            "CommunicationChannel": "Internal",
            "SenderType": "customer",
            "Charset": "utf-8",
            "MimeType": "text/plain",
            "From": context.user_data.get(constants.CUSTOMER_USER_LOGIN),
            "Subject": "Telegram message",
            "Body": to_update.get(constants.COMMENT),
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

    ticket_update = helper._otrs_request(
        "update",
        json
    )

    text = f"Ваша обращение #{ticket_update['TicketNumber']} обновлено!"

    keyboard = InlineKeyboardMarkup([helper.get_return_button()])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    return constants.ATTACHMENT

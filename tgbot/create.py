import base64, logging, io, os, sys, bot_utils
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

(
    NEW_TICKET,  # 0
    SUBJECT,  # 1
    BODY,  # 2
    ATTACHMENT,  # 3
    UPLOAD,  # 4
    FINISH,  # 5
    CREATE,  # 6
    CREATE_WITH_ATTACHMENT,  # 7
    FILE_PATH,  # 8
    FILE_NAME,  # 9
    FILE_TYPE,  # 10
) = range(0, 11)

OVERVIEW = 25
STOPPING = 26
SELECTING_ACTION = 15
CUSTOMER_USER_LOGIN = 25

log = logging.getLogger(__name__)

buffer = io.BytesIO()


async def new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.info("def create.new_ticket")

    context.user_data[NEW_TICKET] = {}

    buttons = [
        [
            InlineKeyboardButton(
                text="Назад", callback_data=str(ConversationHandler.END)
            ),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Введите название заявки",
        reply_markup=keyboard,
    )
    return SUBJECT


async def subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.info("def create.subject_handler")

    context.user_data[NEW_TICKET][SUBJECT] = update.message.text

    await update.message.reply_text(text="Введите описание заявки")

    return BODY


async def body_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.info("def create.body_handler")
    context.user_data[NEW_TICKET][BODY] = update.message.text

    buttons = [
        [
            InlineKeyboardButton(text="Да", callback_data=str(UPLOAD)),
            InlineKeyboardButton(text="Нет", callback_data=str(CREATE)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        text="Прикрепить файл?",
        reply_markup=keyboard,
    )
    return ATTACHMENT


async def attachment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.info("def create.attachment_upload")

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Приложите файл до 20Mb")
    return CREATE_WITH_ATTACHMENT


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.info("def create.create")

    new_ticket = context.user_data.get(NEW_TICKET)

    json = {
        "Ticket": {
            "Title": new_ticket[SUBJECT],
            "Queue": "spam",
            "TypeID": 3,  # Запрос на обслуживание
            "CustomerUser": context.user_data.get(CUSTOMER_USER_LOGIN),
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
            "From": context.user_data.get(CUSTOMER_USER_LOGIN),
            "Subject": new_ticket[SUBJECT],
            "Body": new_ticket[BODY],
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
    ticket_create = bot_utils._otrs_request("create", json)
    # ticket_create = {"TicketNumber": 123}
    buttons = [
        [
            InlineKeyboardButton(text="Назад", callback_data=str(STOPPING)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    log.info(json)
    text = f"Ваша обращение принято. Номер заявки #{ticket_create['TicketNumber']}"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    return ConversationHandler.END

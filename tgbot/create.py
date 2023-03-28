import base64, logging, io, os, sys, bot_utils
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

(
    NEW_TICKET,
    SUBJECT,
    BODY,
    ATTACHMENT,
    UPLOAD,
    FINISH,
    CREATE,
    FILE_PATH,
    FILE_NAME,
    FILE_TYPE,
) = range(0, 10)

OVERVIEW = 24
STOPPING = 25
SELECTING_ACTION = 14
CUSTOMER_USER_LOGIN = 24

log = logging.getLogger(__name__)


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
    return UPLOAD


async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.info("def create.upload")

    file_id = update.message.document.file_id
    file_name = update.message.document.file_name
    mime_type = update.message.document.mime_type

    new_file = await context.bot.get_file(file_id)

    path = f"downloads/{file_id}"
    path_to_file = f"{path}/{file_name}"

    context.user_data[NEW_TICKET][FILE_PATH] = path_to_file
    context.user_data[NEW_TICKET][FILE_NAME] = file_name
    context.user_data[NEW_TICKET][FILE_TYPE] = mime_type

    os.makedirs(path, exist_ok=True)

    await new_file.download_to_drive(f"downloads/{file_id}/{file_name}")

    return CREATE


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    log.info("def create.create")

    new_ticket = context.user_data.get(NEW_TICKET)

    log.info(context.user_data)
    log.info(new_ticket)

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

    file_name = new_ticket.get(FILE_PATH)
    if file_name:
        with open(file_name, "rb") as image_file:
            json["Attachment"] = {
                "Content": base64.b64encode(image_file.read()),
                "ContentType": new_ticket[FILE_TYPE],
                "Filename": new_ticket[FILE_NAME],
            }

    log.info(json)

    ticket_create = bot_utils._otrs_request("create", json)
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
        text=f"Заявка #{ticket_create['TicketNumber']} создана!",
        reply_markup=keyboard,
    )

    return CREATE

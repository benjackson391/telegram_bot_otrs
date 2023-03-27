#!/usr/bin/env python

import json, html, http, logging, requests, traceback, random, re
from typing import Any, Dict, Tuple

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from rich.traceback import install
from rich.logging import RichHandler

install(show_locals=True)

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

logger = logging.getLogger("rich")

END = ConversationHandler.END

(
    # states
    USER_IS_AUTHORIZED,  # 0
    AUTHORISATION,  # 1
    NEW_TICKET,  # 2
    CHECK_TICKET,  # 3
    UPDATE_TICKET,  # 4
    START_OVER,  # 5
    SELECTING_ACTION,  # 6
    CURRENT_STEP,  # 7
    TYPING,  # 8
    AUTHORISATION_PROCESS,  # 9
    AUTH_PROCESS,  # 10
    CONFIRMATION_CODE,  # 11
    CONFIRMATION_CODE_STATUS,  # 12
    START_OVER,  # 13
    CUSTOMER_USER_LOGIN,  # 14
    SELECTING_FEATURE,  # 15
    OVERVIEW,  # 16
    STOPPING,  # 17
    TICKETS,  # 18
    TICKET_ID,  # 19
    NEW_COMMENT,  # 20
    # new_ticket
    SUBJECT, # 21
    BODY, # 22
    ATTACHMENT, # 23
    CREATE, # 24
    # attributes
    EMAIL,
    # errors
    EMAIL_NOT_FOUND
    # ) = map(chr, range(0, 10))
) = range(0, 27)


otrs_url = "https://otrs.efsol.ru/otrs/nph-genericinterface.pl/Webservice/bot"
otrs_user = "telegram_bot"
otrs_password = "GBYudLWmfGQV"


def _otrs_request(path: str, json: str) -> Any:
    logger.info("def _otrs_request")

    logger.info(f"path: {path}")
    logger.info(f"request: {json}")
    json["UserLogin"] = otrs_user
    json["Password"] = otrs_password

    response = requests.post(f"{otrs_url}/{path}", json=json)
    response_json = response.json()
    logger.info(f"code: {response.status_code}")
    logger.info(f"raw: {response_json}")

    return response_json


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def start")

    if not context.user_data.get(USER_IS_AUTHORIZED):
        context.user_data[USER_IS_AUTHORIZED] = False
        context.user_data[CONFIRMATION_CODE_STATUS] = 0
        context.user_data[CUSTOMER_USER_LOGIN] = ""

        auth = _otrs_request(
            "auth", {"TelegramLogin": update.message.from_user.username}
        )
        if "Error" not in auth:
            context.user_data[USER_IS_AUTHORIZED] = True
            context.user_data[CUSTOMER_USER_LOGIN] = auth["CustomerUserLogin"]

    context.user_data[EMAIL_NOT_FOUND] = False

    text = (
        "Вы можете создать, обновить или проверить статус вашей заявки. "
        "Для остановки бота просто напишите /stop"
    )

    not_auth_buttons = [
        InlineKeyboardButton(text="Авторизоваться", callback_data=str(AUTHORISATION)),
    ]

    auth_buttons = [
        InlineKeyboardButton(text="Новая заявка", callback_data=str(NEW_TICKET)),
        InlineKeyboardButton(text="Проверить статус", callback_data=str(CHECK_TICKET)),
        InlineKeyboardButton(text="Обновить заявку", callback_data=str(UPDATE_TICKET)),
    ]

    keyboard = InlineKeyboardMarkup(
        list(
            map(
                lambda b: [b],
                auth_buttons
                if context.user_data[USER_IS_AUTHORIZED]
                else not_auth_buttons,
            )
        )
    )

    logging.info(update)

    if context.user_data.get(START_OVER):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "Добро пожаловать в систему постановки заявок EFSOL"
        )
        await update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_ACTION


async def authorisation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logger.info("def authorisation")

    context.user_data[CONFIRMATION_CODE] = random.randint(100000, 999999)
    confirm_account = _otrs_request(
        "confirm_account",
        {
            "Email": context.user_data[EMAIL],
            "Code": context.user_data[CONFIRMATION_CODE],
        },
    )

    logger.info(confirm_account)

    if not bool(confirm_account["data"]):
        context.user_data[EMAIL_NOT_FOUND] = True
        context.user_data[CURRENT_STEP] = str(AUTHORISATION)
    else:
        context.user_data[EMAIL_NOT_FOUND] = False
        context.user_data[CURRENT_STEP] = str(CONFIRMATION_CODE)

    return await ask_for_input(update, context, context.user_data[CURRENT_STEP])


async def ask_for_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, current_step=""
) -> str:
    logging.info("def ask_for_input")

    logging.info(f"current_step: {current_step}")

    if not current_step:
        current_step = update.callback_query.data

    # update ticket
    if bool(re.match("^NEW_COMMENT_\d+$", current_step)):
        current_step = str(UPDATE_TICKET)
        context.user_data[TICKET_ID] = update.callback_query.data.split("_")[-1]

    context.user_data[CURRENT_STEP] = current_step

    if context.user_data[CONFIRMATION_CODE_STATUS] == 0:
        confirmation_code_text = (
            "Для подтверждения адреса электронной почты введите код из письма"
        )
    elif context.user_data[CONFIRMATION_CODE_STATUS] == 1:
        confirmation_code_text = "Код неверный, попробуйте еще раз"
    else:
        confirmation_code_text = "Код верный"
        context.user_data[USER_IS_AUTHORIZED] = True

        confirm_account = _otrs_request(
            "confirm_account",
            {
                "Email": context.user_data[EMAIL],
                "TelegramLogin": update.message.from_user.username,
            },
        )

        await start(update, context)
        return END

    text_map = {
        str(
            AUTHORISATION
        ): f"Введите свой адрес электронный почты, который зарегистрирован в OTRS",
        str(CONFIRMATION_CODE): confirmation_code_text,
        str(UPDATE_TICKET): f"Введите комментарий",
    }

    text = text_map[current_step]

    if context.user_data[EMAIL_NOT_FOUND]:
        text = f"Адрес {context.user_data[EMAIL]} не найден в OTRS, попробуйте другой адрес"
        context.user_data[EMAIL_NOT_FOUND] = False

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text)
    else:
        await update.message.reply_text(text=text)

    return TYPING


async def save_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logger.info("def save_input")
    logger.info(context.user_data)

    input_text = update.message.text

    if context.user_data[CURRENT_STEP] == str(AUTHORISATION):
        logger.info("AUTHORISATION")
        context.user_data[EMAIL] = input_text
        return await authorisation(update, context)
    elif context.user_data[CURRENT_STEP] == str(CONFIRMATION_CODE):
        logger.info(f"CONFIRMATION_CODE")
        context.user_data[CONFIRMATION_CODE_STATUS] = (
            2 if int(context.user_data[CONFIRMATION_CODE]) == int(input_text) else 1
        )
        return await ask_for_input(update, context, str(CONFIRMATION_CODE))
    elif context.user_data[CURRENT_STEP] == str(UPDATE_TICKET):
        logger.info(f"CONFIRMATION_CODE")
        ticket_update = _otrs_request(
            "update",
            {
                "TicketID": context.user_data[TICKET_ID],
                "Article": {
                    "CommunicationChannel": "Internal",
                    "SenderType": "customer",
                    "Charset": "utf-8",
                    "MimeType": "text/plain",
                    "From": context.user_data[CUSTOMER_USER_LOGIN],
                    "Subject": "Telegram message",
                    "Body": input_text,
                },
            },
        )
        context.user_data[START_OVER] = False
        return await start(update, context)


async def end_second_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("def end_second_level")
    context.user_data[START_OVER] = True
    await start(update, context)

    return END


async def update_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def update_tickets")

    context.user_data[CURRENT_STEP] = str(UPDATE_TICKET)
    auth = _otrs_request(
        "search", {
            "CustomerUserLogin": context.user_data[CUSTOMER_USER_LOGIN],
            "StateType": ['open', 'new', 'pending reminder'],
        }
    )

    user_data = context.user_data
    buttons = []
    tickets = {}
    if "TicketID" in auth:
        user_data[TICKETS] = {}

        for id in auth["TicketID"]:
            ticket_data = _otrs_request(f"ticket/{id}", {}).get("Ticket")[0]

            user_data[TICKETS][id] = ticket_data

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f'#{ticket_data["TicketNumber"]}: {ticket_data["Title"]}',
                        callback_data=f"TICKET_{id}",
                    )
                ]
            )
    buttons.append([InlineKeyboardButton(text="Назад", callback_data=str(END))])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Выберите заявку, которую необходимо обновить", reply_markup=keyboard
    )

    return SELECTING_FEATURE


async def update_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def show_ticket")

    context.user_data[TICKET_ID] = update.callback_query.data.split("_")[-1]
    ticket = context.user_data.get(TICKETS)[context.user_data[TICKET_ID]]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["Owner"]}
        Статус: {ticket["State"]}
        Предельное время решения: {'SolutionTimeDestinationDate' in ticket and ticket["SolutionTimeDestinationDate"] or None}

        Какую информацию нужно обновить?
    """

    buttons = [
        [
            InlineKeyboardButton(
                text="Добавьте комментарий",
                callback_data=f"NEW_COMMENT_{context.user_data[TICKET_ID]}",
            )
        ],
        # [InlineKeyboardButton(text="Прикрепить файл", callback_data=str(NEW_TICKET))],
        [InlineKeyboardButton(text="Назад", callback_data=str(NEW_TICKET))],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_FEATURE


async def check_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def check_tickets")
    auth = _otrs_request(
        "search", {
            "CustomerUserLogin": context.user_data[CUSTOMER_USER_LOGIN],
            "StateType": ['open', 'new', 'pending reminder'],

        }
    )

    user_data = context.user_data
    buttons = []
    tickets = {}
    if "TicketID" in auth:
        user_data[TICKETS] = {}

        for id in auth["TicketID"]:
            ticket_data = _otrs_request(f"ticket/{id}", {}).get("Ticket")[0]

            user_data[TICKETS][id] = ticket_data

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f'#{ticket_data["TicketNumber"]}: {ticket_data["Title"]}',
                        callback_data=f"TICKET_{id}",
                    )
                ]
            )
    
    buttons.append([InlineKeyboardButton(text="Назад", callback_data=str(END))])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Открытые заявки", reply_markup=keyboard
    )

    return SELECTING_FEATURE


async def show_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def show_ticket")

    context.user_data[TICKET_ID] = update.callback_query.data.split("_")[-1]
    ticket = context.user_data.get(TICKETS)[context.user_data[TICKET_ID]]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["Owner"]}
        Статус: {ticket["State"]}
        Предельное время решения: {'SolutionTimeDestinationDate' in ticket and ticket["SolutionTimeDestinationDate"] or None}
    """

    buttons = [[InlineKeyboardButton(text="Назад", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[START_OVER] = True

    return SELECTING_FEATURE


async def new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def new_ticket")

    buttons = [
        [
            InlineKeyboardButton(text="Тема", callback_data=str(SUBJECT)),
        ],
        [
            InlineKeyboardButton(text="Описание", callback_data=str(BODY)),
            # ],[
            #     InlineKeyboardButton(text="Файл", callback_data=str(ATTACHMENT)),
        ],
        [
            InlineKeyboardButton(text="Обзор", callback_data=str(OVERVIEW)),
        ],
        [
            InlineKeyboardButton(text="Создать", callback_data=str(CREATE)),
        ],
        [
            InlineKeyboardButton(text="Назад", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we collect features for a new person, clear the cache and save the gender
    if not context.user_data.get(START_OVER):
        context.user_data[NEW_TICKET] = {}
        text = "Please select a feature to update."

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    # But after we do that, we need to send a new message
    else:
        text = "Got it! Please select a feature to update."

        if update.message:
            await update.message.reply_text(text=text, reply_markup=keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )

    context.user_data[START_OVER] = False
    return SELECTING_FEATURE


async def end_second_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[START_OVER] = True
    await start(update, context)

    return END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await update.message.reply_text("До встречи.")

    return STOPPING


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("До встречи.")

    return END


async def show_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def show_data")
    logging.info(context.user_data)

    new_ticket = context.user_data.get(NEW_TICKET)

    text = f"Тема: {new_ticket.get(str(SUBJECT))}\nOписание: {new_ticket.get(str(BODY))}"

    buttons = [[InlineKeyboardButton(text="Назад", callback_data=str(NEW_TICKET))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[START_OVER] = True

    return SELECTING_FEATURE

async def create_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def create_ticket")

    new_ticket = context.user_data.get(NEW_TICKET)

    ticket_create = _otrs_request(
        "create",
        {
            "Ticket": {
                "Title": new_ticket.get(str(SUBJECT)),
                "Queue": "spam",
                "TypeID": 3, # Запрос на обслуживание
                "CustomerUser": context.user_data[CUSTOMER_USER_LOGIN],
                "StateID": 1, # new
                "PriorityID": 3, # normal
                "OwnerID": 1, # admin
                "LockID": 1, # unlick
            },
            "Article": {
                "CommunicationChannel": "Internal",
                "SenderType": "customer",
                "Charset": "utf-8",
                "MimeType": "text/plain",
                "From": context.user_data[CUSTOMER_USER_LOGIN],
                "Subject": new_ticket.get(str(SUBJECT)),
                "Body": new_ticket.get(str(BODY)),
            },
        },
    )


    buttons = [[InlineKeyboardButton(text="Назад", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=f"Заявка #{ticket_create.get('TicketNumber')} создана!", reply_markup=keyboard)

async def ask_for_input_old(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def ask_for_input")

    context.user_data[CURRENT_STEP] = update.callback_query.data
    text = f"Введите текст"

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)

    return TYPING

async def save_input_old(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Save input for feature and return to feature selection."""
    user_data = context.user_data
    user_data[NEW_TICKET][context.user_data[CURRENT_STEP]] = update.message.text

    user_data[START_OVER] = True

    return await new_ticket(update, context)

def main() -> None:
    application = (
        Application.builder()
        .token("5803013436:AAFvFrnlyr5P-RdGjU0Yn2dMKh6uiCNUrA8")
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                # auth
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(
                            ask_for_input, pattern="^" + str(AUTHORISATION) + "$"
                        )
                    ],
                    states={
                        TYPING: [
                            MessageHandler(filters.TEXT & ~filters.COMMAND, save_input),
                        ],
                    },
                    fallbacks=[
                        CommandHandler("stop", stop_nested),
                    ],
                    map_to_parent={
                        OVERVIEW: OVERVIEW,
                        END: SELECTING_ACTION,
                        STOPPING: END,
                    },
                ),
                # update
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(
                            update_tickets, pattern="^" + str(UPDATE_TICKET) + "$"
                        )
                    ],
                    states={
                        SELECTING_FEATURE: [
                            CallbackQueryHandler(
                                update_ticket,
                                pattern="^TICKET_\d+$",
                            ),
                            CallbackQueryHandler(
                                ask_for_input,
                                pattern="^NEW_COMMENT_\d+$",
                            ),
                            CallbackQueryHandler(
                                end_second_level, pattern="^" + str(END) + "$"
                            ),
                        ],
                        TYPING: [
                            MessageHandler(filters.TEXT & ~filters.COMMAND, save_input),
                        ],
                    },
                    fallbacks=[
                        CommandHandler("stop", stop_nested),
                    ],
                    map_to_parent={
                        OVERVIEW: OVERVIEW,
                        END: SELECTING_ACTION,
                        STOPPING: END,
                    },
                ),
                # check
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(
                            check_tickets, pattern="^" + str(CHECK_TICKET) + "$"
                        )
                    ],
                    states={
                        SELECTING_FEATURE: [
                            CallbackQueryHandler(
                                show_ticket,
                                pattern="^TICKET_\d+$",
                            ),
                            CallbackQueryHandler(
                                end_second_level, pattern="^" + str(END) + "$"
                            ),
                        ]
                    },
                    fallbacks=[
                        CommandHandler("stop", stop_nested),
                    ],
                    map_to_parent={
                        OVERVIEW: OVERVIEW,
                        END: SELECTING_ACTION,
                        STOPPING: END,
                    },
                ),
                # new
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(new_ticket, pattern="^" + str(NEW_TICKET) + "$")
                    ],
                    states={
                        SELECTING_FEATURE: [
                            CallbackQueryHandler(
                                ask_for_input_old,
                                pattern="^(?:"
                                + str(SUBJECT)
                                + "|^"
                                + str(BODY)
                                + "|"
                                + str(ATTACHMENT)
                                + ")$",
                            ),
                            CallbackQueryHandler(show_data, pattern="^" + str(OVERVIEW) + "$"),
                            CallbackQueryHandler(new_ticket, pattern="^" + str(NEW_TICKET) + "$"),
                            CallbackQueryHandler(create_ticket, pattern="^" + str(CREATE) + "$"),
                        ],
                        TYPING: [
                            MessageHandler(filters.TEXT & ~filters.COMMAND, save_input_old),
                        ],
                    },
                    fallbacks=[
                        CallbackQueryHandler(show_data, pattern="^" + str(OVERVIEW) + "$"),
                        CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
                        CommandHandler("stop", stop_nested),
                    ],
                    map_to_parent={
                        # After showing data return to top level menu
                        OVERVIEW: OVERVIEW,
                        # Return to top level menu
                        END: SELECTING_ACTION,
                        # End conversation altogether
                        STOPPING: END,
                    },
                )
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
        ],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()

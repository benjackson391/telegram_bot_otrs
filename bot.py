#!/usr/bin/env python


import argparse, click, concurrent.futures, json, html, http, logging, traceback, random, re, redis, bot_utils
from rich_argparse import RichHelpFormatter
from typing import Any, Dict, Tuple

from tgbot import create, error

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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, File
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

END = ConversationHandler.END

(
    # states
    USER_IS_AUTHORIZED,  # 10
    AUTHORISATION,  # 11
    NEW_TICKET,  # 12
    CHECK_TICKET,  # 13
    UPDATE_TICKET,  # 14
    START_OVER,  # 15
    SELECTING_ACTION,  # 16
    CURRENT_STEP,  # 17
    TYPING,  # 18
    AUTHORISATION_PROCESS,  # 19
    AUTH_PROCESS,  # 20
    CONFIRMATION_CODE,  # 21
    CONFIRMATION_CODE_STATUS,  # 22
    START_OVER,  # 23
    CUSTOMER_USER_LOGIN,  # 24
    SELECTING_FEATURE,  # 25
    OVERVIEW,  # 26
    STOPPING,  # 27
    TICKETS,  # 28
    TICKET_ID,  # 29
    NEW_COMMENT,  # 30
    # new_ticket
    # attributes
    EMAIL,  # 31
    # errors
    EMAIL_NOT_FOUND,  # 32
    UPLOAD_ATTACHMENT,  # 33
    # ) = map(chr, range(0, 10))
) = range(11, 35)


args = {}

r = redis.Redis(host="localhost", port=6379, db=0)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def start")

    if not context.user_data.get(USER_IS_AUTHORIZED):
        context.user_data[USER_IS_AUTHORIZED] = False
        context.user_data[CONFIRMATION_CODE_STATUS] = 0
        context.user_data[CUSTOMER_USER_LOGIN] = ""

        auth = bot_utils._otrs_request(
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
    logging.info("def authorisation")

    context.user_data[CONFIRMATION_CODE] = random.randint(100000, 999999)
    confirm_account = bot_utils._otrs_request(
        "confirm_account",
        {
            "Email": context.user_data[EMAIL],
            "Code": context.user_data[CONFIRMATION_CODE],
        },
    )

    logging.info(confirm_account)

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

        confirm_account = bot_utils._otrs_request(
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
    logging.info("def save_input")
    logging.info(context.user_data)

    input_text = update.message.text

    if context.user_data[CURRENT_STEP] == str(AUTHORISATION):
        logging.info("AUTHORISATION")
        context.user_data[EMAIL] = input_text
        return await authorisation(update, context)
    elif context.user_data[CURRENT_STEP] == str(CONFIRMATION_CODE):
        logging.info(f"CONFIRMATION_CODE")
        context.user_data[CONFIRMATION_CODE_STATUS] = (
            2 if int(context.user_data[CONFIRMATION_CODE]) == int(input_text) else 1
        )
        return await ask_for_input(update, context, str(CONFIRMATION_CODE))
    elif context.user_data[CURRENT_STEP] == str(UPDATE_TICKET):
        logging.info(f"CONFIRMATION_CODE")
        ticket_update = bot_utils._otrs_request(
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
    logging.info("def end_second_level")
    context.user_data[START_OVER] = True
    await start(update, context)

    return END


async def show_open_tickets(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text
) -> str:
    context.user_data[TICKETS] = collect_tickets(context.user_data[CUSTOMER_USER_LOGIN])

    buttons = build_ticket_buttons(context.user_data[TICKETS])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_FEATURE


async def update_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def update_tickets")

    context.user_data[CURRENT_STEP] = str(UPDATE_TICKET)
    return await show_open_tickets(
        update, context, "Выберите заявку, которую необходимо обновить"
    )


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

    context.user_data[CURRENT_STEP] = str(CHECK_TICKET)
    return await show_open_tickets(update, context, "Открытые заявки")


async def show_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def show_ticket")

    context.user_data[TICKET_ID] = update.callback_query.data.split("_")[-1]
    context.user_data[TICKETS] = collect_tickets(context.user_data[CUSTOMER_USER_LOGIN])

    ticket = context.user_data[TICKETS][context.user_data[TICKET_ID]]

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

    text = f"Тема: {new_ticket.get(str(create.SUBJECT))}\nOписание: {new_ticket.get(str(create.BODY))}"

    buttons = [[InlineKeyboardButton(text="Назад", callback_data=str(NEW_TICKET))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[START_OVER] = True

    return SELECTING_FEATURE


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


def parse_args():
    parser = argparse.ArgumentParser(
        description="OTRS Telegram Bot", formatter_class=RichHelpFormatter
    )

    parser.add_argument(
        "--debug",
        dest="debug",
        required=False,
        default=False,
        action="store_true",
        help="enable Debug mode",
    )
    parser.add_argument(
        "--path-to-log",
        dest="log_path",
        required=False,
        type=str,
        help="path to write log",
    )

    return parser.parse_args()


def init_logging():
    handlers = [RichHandler(rich_tracebacks=True, tracebacks_suppress=[click])]
    if args.log_path:
        handlers.append(logging.FileHandler(args.log_path))
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]",
        handlers=handlers,
    )
    logging.getLogger("rich").setLevel("DEBUG")
    bot_utils._set_logging(logging, args)


def collect_ticket(ticket_id, collected_tickets):
    collected_tickets[ticket_id] = bot_utils._otrs_request(f"ticket/{ticket_id}", {})[
        "Ticket"
    ][0]


def collect_tickets(user_login=""):
    logging.info("def collect_tickets")

    if r.exists(user_login):
        return json.loads(r.get(user_login))

    collected_tickets = {}
    tickets = bot_utils._otrs_request(
        "search",
        {
            "CustomerUserLogin": user_login,
            "StateType": ["open", "new", "pending reminder"],
        },
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for ticket_id in tickets.get("TicketID"):
            executor.submit(collect_ticket, ticket_id, collected_tickets)

    r.set(user_login, json.dumps(collected_tickets))
    r.expire(user_login, 60)
    return collected_tickets


def build_ticket_buttons(tickets):
    buttons = []
    for ticket_id in tickets:
        ticket = tickets[ticket_id]
        logging.info(ticket_id)
        logging.info(ticket)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"#{ticket['TicketNumber']}: {ticket['Title']}",
                    callback_data=f"TICKET_{ticket['TicketID']}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="Назад", callback_data=str(END))])
    return buttons


def main() -> None:
    init_logging()

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
                        CallbackQueryHandler(
                            create.new_ticket,
                            pattern="^" + str(NEW_TICKET) + "$",
                        )
                    ],
                    states={
                        create.SUBJECT: [
                            MessageHandler(filters.TEXT, create.subject_handler),
                            CallbackQueryHandler(
                                end_second_level, pattern="^" + str(END) + "$"
                            ),
                        ],
                        create.BODY: [
                            MessageHandler(filters.TEXT, create.body_handler),
                        ],
                        create.ATTACHMENT: [
                            CallbackQueryHandler(
                                create.attachment_handler,
                                pattern="^" + str(create.UPLOAD) + "$",
                            ),
                            CallbackQueryHandler(
                                create.create, pattern="^" + str(create.CREATE) + "$"
                            ),
                            CallbackQueryHandler(
                                end_second_level, pattern="^" + str(END) + "$"
                            ),
                        ],
                        create.CREATE_WITH_ATTACHMENT: [
                            MessageHandler(filters.ALL, create.create),
                        ],
                    },
                    fallbacks=[],
                    map_to_parent={},
                ),
            ]
        },
        fallbacks=[
            CommandHandler("stop", stop),
        ],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error.error_handler)
    application.run_polling()


if __name__ == "__main__":
    args = parse_args()
    main()

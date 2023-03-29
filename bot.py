#!/usr/bin/env python


import argparse, click, concurrent.futures, json, html, http, logging, traceback, random, re
from rich_argparse import RichHelpFormatter
from typing import Any, Dict, Tuple

from tgbot import common, constants, create, check, error, helper, update

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

args = {}


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


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("До встречи.")

    return constants.END


async def show_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.debug("def show_data")

    new_ticket = context.user_data.get(constants.NEW_TICKET)

    text = f"Тема: {new_ticket.get(str(constants.SUBJECT))}\nOписание: {new_ticket.get(str(constants.BODY))}"

    buttons = [
        [InlineKeyboardButton(text="Назад", callback_data=str(constants.NEW_TICKET))]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[constants.START_OVER] = True

    return constants.SELECTING_FEATURE


async def ask_for_input_old(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.debug("def ask_for_input")

    context.user_data[constants.CURRENT_STEP] = update.callback_query.data
    text = f"Введите текст"

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)

    return constants.TYPING


async def save_input_old(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Save input for feature and return to feature selection."""
    user_data = context.user_data
    user_data[constants.NEW_TICKET][
        context.user_data[constants.CURRENT_STEP]
    ] = update.message.text

    user_data[constants.START_OVER] = True

    return await create.new_ticket(update, context)


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


def main() -> None:
    init_logging()

    application = (
        Application.builder()
        .token("5803013436:AAFvFrnlyr5P-RdGjU0Yn2dMKh6uiCNUrA8")
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", common.start)],
        states={
            constants.SELECTING_ACTION: [
                # auth
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(
                            ask_for_input,
                            pattern="^" + str(constants.AUTHORISATION) + "$",
                        )
                    ],
                    states={
                        constants.TYPING: [
                            MessageHandler(filters.TEXT & ~filters.COMMAND, save_input),
                        ],
                    },
                    fallbacks=[
                        CommandHandler("stop", stop),
                    ],
                    map_to_parent={
                        # OVERVIEW: OVERVIEW,
                        # END: SELECTING_ACTION,
                        # STOPPING: END,
                    },
                ),
                # update
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(
                            update.update_tickets,
                            pattern="^" + str(constants.UPDATE_TICKET) + "$",
                        )
                    ],
                    states={
                        constants.SHOW_TICKETS: [
                            CallbackQueryHandler(
                                update.update_ticket,
                                pattern="^TICKET_\d+$",
                            ),
                            CallbackQueryHandler(
                                common.end_second_level,
                                pattern="^" + str(constants.END) + "$",
                            ),
                        ],
                        constants.UPDATE_TICKET: [
                            CallbackQueryHandler(
                                update.add_comment,
                                pattern="^" + str(constants.COMMENT) + "$",
                            ),
                            CallbackQueryHandler(
                                common.end_second_level,
                                pattern="^" + str(constants.END) + "$",
                            ),
                        ],
                        constants.ATTACHMENT: [
                            MessageHandler(filters.TEXT, update.comment_handler),
                            CallbackQueryHandler(
                                update.update, pattern="^" + str(constants.CREATE) + "$"
                            ),
                            CallbackQueryHandler(
                                update.attachment_handler,
                                pattern="^" + str(constants.UPLOAD) + "$",
                            ),
                            CallbackQueryHandler(
                                common.end_second_level,
                                pattern="^" + str(constants.END) + "$",
                            ),
                        ],
                        constants.CREATE_WITH_ATTACHMENT: [
                            MessageHandler(filters.ALL, update.update),
                        ]
                        # constants.SELECTING_FEATURE: [
                        #     CallbackQueryHandler(
                        #         update.add_comment,
                        #         pattern="^" + str(constants.COMMENT) + "$",
                        #     ),
                        #     CallbackQueryHandler(
                        #         common.end_second_level,
                        #         pattern="^" + str(constants.END) + "$",
                        #     ),
                        # ],
                        # constants.COMMENT: [
                        #     MessageHandler(
                        #         filters.TEXT & ~filters.COMMAND, update.comment_handler
                        #     ),
                        # ],
                    },
                    fallbacks=[
                        CommandHandler("stop", stop),
                    ],
                    map_to_parent={
                        # OVERVIEW: OVERVIEW,
                        # END: SELECTING_ACTION,
                        # STOPPING: END,
                    },
                ),
                # check
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(
                            check.check_tickets,
                            pattern="^" + str(constants.CHECK_TICKET) + "$",
                        )
                    ],
                    states={
                        constants.SELECTING_FEATURE: [
                            CallbackQueryHandler(
                                check.show_ticket,
                                pattern="^TICKET_\d+$",
                            ),
                            CallbackQueryHandler(
                                common.end_second_level,
                                pattern="^" + str(constants.END) + "$",
                            ),
                        ]
                    },
                    fallbacks=[
                        CommandHandler("stop", stop),
                    ],
                    map_to_parent={},
                ),
                # create
                ConversationHandler(
                    entry_points=[
                        CallbackQueryHandler(
                            create.new_ticket,
                            pattern="^" + str(constants.NEW_TICKET) + "$",
                        )
                    ],
                    states={
                        constants.SUBJECT: [
                            MessageHandler(filters.TEXT, create.subject_handler),
                            CallbackQueryHandler(
                                common.end_second_level,
                                pattern="^" + str(constants.END) + "$",
                            ),
                        ],
                        constants.BODY: [
                            MessageHandler(filters.TEXT, create.body_handler),
                        ],
                        constants.ATTACHMENT: [
                            CallbackQueryHandler(
                                create.attachment_handler,
                                pattern="^" + str(constants.UPLOAD) + "$",
                            ),
                            CallbackQueryHandler(
                                create.create, pattern="^" + str(constants.CREATE) + "$"
                            ),
                            CallbackQueryHandler(
                                common.end_second_level,
                                pattern="^" + str(constants.END) + "$",
                            ),
                        ],
                        constants.CREATE_WITH_ATTACHMENT: [
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

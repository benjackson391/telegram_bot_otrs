#!/usr/bin/env python


import argparse, click, logging, multiprocessing
from decouple import config
from rich_argparse import RichHelpFormatter

from tgbot import auth, common, constants, create, check, error, update

from telegram import Update
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

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    PicklePersistence,
)

from rich.traceback import install
from rich.logging import RichHandler

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

install(show_locals=True)

args = {}


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

    persistence = PicklePersistence(filepath="arbitrarycallbackdatabot")

    application = (
        Application.builder()
        .token(config("DEBUG_TOKEN") if config("DEBUG") == 1 else config("TOKEN"))
        .persistence(persistence)
        .arbitrary_callback_data(True)
        .concurrent_updates(True)
        .build()
    )

    fallbacks = [
        CallbackQueryHandler(
            common.end_second_level, pattern="^" + str(constants.END) + "$"
        ),
        CommandHandler("stop", common.stop),
    ]

    map_to_parent = {constants.SELECTING_ACTION: constants.END}

    auth_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                auth.entry,
                pattern="^" + str(constants.AUTHORISATION) + "$",
            )
        ],
        states={
            constants.EMAIL: [
                MessageHandler(filters.TEXT, auth.email_handler),
            ],
            constants.CONFIRMATION_CODE: [
                MessageHandler(filters.TEXT, auth.code_handler),
            ],
        },
        fallbacks=fallbacks,
        map_to_parent=map_to_parent,
    )

    update_conv = ConversationHandler(
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
            ],
        },
        fallbacks=fallbacks,
    )

    check_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                check.check_tickets,
                pattern="^" + str(constants.CHECK_TICKET) + "$",
            )
        ],
        states={
            constants.SELECTING_FEATURE: [
                CallbackQueryHandler(
                    check.show_open_tickets,
                    pattern="^TICKET_STATUS_OPEN$",
                ),
                CallbackQueryHandler(
                    check.show_pending_tickets,
                    pattern="^TICKET_STATUS_PENDING$",
                ),
                CallbackQueryHandler(
                    check.show_ticket,
                    pattern="^TICKET_\d+$",
                ),
                CallbackQueryHandler(
                    check.show_ticket_and_vote,
                    pattern="^TICKET_AND_VOTE_\d+$",
                ),
                CallbackQueryHandler(
                    check.vote,
                    pattern="^TICKET_AND_VOTE_SEND_\d+_\d$",
                ),
                CallbackQueryHandler(
                    check.rework,
                    pattern="^TICKET_AND_VOTE_SEND_\d+$",
                ),
                CallbackQueryHandler(
                    common.end_second_level,
                    pattern="^" + str(constants.END) + "$",
                ),
                MessageHandler(filters.TEXT, check.rework_comment_handler),
            ]
        },
        fallbacks=fallbacks,
        map_to_parent=map_to_parent,
    )

    create_conv = ConversationHandler(
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
                CallbackQueryHandler(
                    create.create, pattern="^" + str(constants.CREATE) + "$"
                ),
                MessageHandler(filters.ALL, create.create),
            ],
        },
        fallbacks=fallbacks,
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", common.start)],
        states={
            constants.SELECTING_ACTION: [
                auth_conv,
                update_conv,
                check_conv,
                create_conv,
            ]
        },
        fallbacks=fallbacks,
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error.error_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    args = parse_args()
    main()

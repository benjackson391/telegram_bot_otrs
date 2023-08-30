import logging
import re
import time

from tgbot import common, helper, constants
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler


log = logging.getLogger(__name__)


async def check_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def check.check_tickets")

    context.user_data[constants.TICKETS] = helper.collect_tickets(context.user_data)

    buttons, ticket_status_check = helper.build_ticket_buttons(
        context.user_data[constants.TICKETS]
    )
    context.user_data[constants.TICKET_STATUS] = ticket_status_check

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text='Выберите',
        reply_markup=keyboard,
    )

    return constants.SELECTING_FEATURE


def _get_keyboard(context: ContextTypes.DEFAULT_TYPE, type: str) -> list:
    ticket_ids = context.user_data[constants.TICKET_STATUS][type]
    tickets = context.user_data[constants.TICKETS]

    callback_prefix = 'TICKET_' if type == 'open' else 'TICKET_AND_VOTE_'

    buttons = []
    for ticket_id in ticket_ids:
        ticket = tickets[ticket_id]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"#{ticket['TicketNumber']}: {ticket['Title']}",
                    callback_data=f"{callback_prefix}{ticket['TicketID']}",
                )
            ]
        )
    buttons.append(
        helper.get_return_button()
    )

    return InlineKeyboardMarkup(buttons)


async def show_open_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def check.show_open_tickets")

    keyboard = _get_keyboard(context, 'open')

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Открытые заявки",
        reply_markup=keyboard,
    )

    return constants.SELECTING_FEATURE


async def show_pending_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def check.show_pending_tickets")

    keyboard=_get_keyboard(context, 'pending')

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Заявки на оценку",
        reply_markup=keyboard,
    )

    return constants.SELECTING_FEATURE


async def show_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def check.show_ticket")

    context.user_data[constants.TICKET_ID] = update.callback_query.data.split("_")[-1]
    context.user_data[constants.TICKETS] = helper.collect_tickets(context.user_data)

    ticket = context.user_data[constants.TICKETS][
        context.user_data[constants.TICKET_ID]
    ]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["ExtendedOwner"]["UserFirstname"]} {ticket["ExtendedOwner"]["UserLastname"]}
        Статус: {constants.TRANSLATION.get(ticket["State"])}
        Предельное время решения: {'SolutionTimeDestinationDate' in ticket and ticket["SolutionTimeDestinationDate"] or None}

        Описание: {ticket['Article'][0]['Body']}
    """

    buttons = [
        [InlineKeyboardButton(text="Назад", callback_data=str(ConversationHandler.END))]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[constants.START_OVER] = True

    return constants.SELECTING_FEATURE


async def show_ticket_and_vote(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    common.debug("def check.show_ticket_and_vote")

    context.user_data[constants.TICKET_ID] = update.callback_query.data.split("_")[-1]
    context.user_data[constants.TICKETS] = helper.collect_tickets(context.user_data)

    ticket = context.user_data[constants.TICKETS][
        context.user_data[constants.TICKET_ID]
    ]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["ExtendedOwner"]["UserFirstname"]} {ticket["ExtendedOwner"]["UserLastname"]}
        Статус: {constants.TRANSLATION.get(ticket["State"])}
        Предельное время решения: {'SolutionTimeDestinationDate' in ticket and ticket["SolutionTimeDestinationDate"] or None}

        Описание: {ticket['Article'][0]['Body']}
    """

    buttons = [
        [
            InlineKeyboardButton(
                text="5", callback_data=f'TICKET_AND_VOTE_SEND_{ticket["TicketID"]}_5'
            )
        ],
        [
            InlineKeyboardButton(
                text="4", callback_data=f'TICKET_AND_VOTE_SEND_{ticket["TicketID"]}_4'
            )
        ],
        [
            InlineKeyboardButton(
                text="3", callback_data=f'TICKET_AND_VOTE_SEND_{ticket["TicketID"]}_3'
            )
        ],
        [
            InlineKeyboardButton(
                text="2", callback_data=f'TICKET_AND_VOTE_SEND_{ticket["TicketID"]}_2'
            )
        ],
        [
            InlineKeyboardButton(
                text="Вернуть на доработку", callback_data=f'TICKET_AND_VOTE_SEND_{ticket["TicketID"]}'
            )
        ],
        [
            InlineKeyboardButton(
                text="Назад", callback_data=str(ConversationHandler.END)
            )
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[constants.START_OVER] = True

    return constants.SELECTING_FEATURE


async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    common.debug("def check.vote")
    query_data = update.callback_query.data

    matches = re.search(r"TICKET_AND_VOTE_SEND_(\d+)_(\d)", query_data)

    json = {
        "TicketID": matches.group(1),
        "DynamicField": {"Name": "TicketVote", "Value": matches.group(2)},
        "Ticket": {
            "StateID": 2 # closed successful
        }
    }

    ticket_update = helper._otrs_request("update", json)

    keyboard = InlineKeyboardMarkup([helper.get_return_button()])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Ваша обращение оценено!", reply_markup=keyboard)

    return constants.SELECTING_FEATURE


async def rework(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    common.debug("def check.rework")
    context.user_data[constants.TICKET_ID] = update.callback_query.data.split("_")[-1]

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Введите комментарий")

    return constants.SELECTING_FEATURE

async def rework_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    customer_user = context.user_data.get(constants.CUSTOMER_USER_LOGIN)

    json = {
        "TicketID": context.user_data[constants.TICKET_ID],
        "Article": {
            "CommunicationChannel": "Internal",
            "SenderType": "customer",
            "Charset": "utf-8",
            "MimeType": "text/plain",
            "From": customer_user,
            "Subject": "Telegram message",
            "Body": text,
        },
        "Ticket": {
            "StateID": 4 # open 
        }
    }

    ticket_update = helper._otrs_request("update", json)

    text = f"Ваша обращение #{ticket_update['TicketNumber']} отправлено на доработку!"

    keyboard = InlineKeyboardMarkup([helper.get_return_button()])

    await update.message.reply_text(
        text=text,
        reply_markup=keyboard,
    )

    # return common.start(update, context)
    return constants.SELECTING_FEATURE
import logging

from tgbot import helper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

CHECK_TICKET = 14
START_OVER = 16
CURRENT_STEP = 18
CUSTOMER_USER_LOGIN = 25
SELECTING_FEATURE = 26
TICKETS = 29
TICKET_ID = 30

log = logging.getLogger(__name__)


async def check_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def check.check_tickets")

    context.user_data[CURRENT_STEP] = str(CHECK_TICKET)
    return await show_open_tickets(update, context, "Открытые заявки")


async def show_open_tickets(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text
) -> str:
    logging.info("def check.show_open_tickets")

    log.info(context.user_data)
    context.user_data[TICKETS] = helper.collect_tickets(
        context.user_data[CUSTOMER_USER_LOGIN]
    )

    buttons = helper.build_ticket_buttons(context.user_data[TICKETS])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_FEATURE


async def show_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def show_ticket")

    context.user_data[TICKET_ID] = update.callback_query.data.split("_")[-1]
    context.user_data[TICKETS] = helper.collect_tickets(
        context.user_data[CUSTOMER_USER_LOGIN]
    )

    ticket = context.user_data[TICKETS][context.user_data[TICKET_ID]]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["Owner"]}
        Статус: {ticket["State"]}
        Предельное время решения: {'SolutionTimeDestinationDate' in ticket and ticket["SolutionTimeDestinationDate"] or None}
    """

    buttons = [[InlineKeyboardButton(text="Назад", callback_data=str(ConversationHandler.END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[START_OVER] = True

    return SELECTING_FEATURE

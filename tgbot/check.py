import logging

from tgbot import helper, constants
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler


log = logging.getLogger(__name__)


async def check_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def check.check_tickets")

    context.user_data[constants.CURRENT_STEP] = str(constants.CHECK_TICKET)
    return await show_open_tickets(update, context, "Открытые заявки")


async def show_open_tickets(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text
) -> str:
    logging.info("def check.show_open_tickets")

    log.info(context.user_data)
    context.user_data[constants.TICKETS] = helper.collect_tickets(
        context.user_data[constants.CUSTOMER_USER_LOGIN]
    )

    buttons = helper.build_ticket_buttons(context.user_data[constants.TICKETS])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return constants.SELECTING_FEATURE


async def show_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    logging.info("def show_ticket")

    context.user_data[constants.TICKET_ID] = update.callback_query.data.split("_")[-1]
    context.user_data[constants.TICKETS] = helper.collect_tickets(
        context.user_data[constants.CUSTOMER_USER_LOGIN]
    )

    ticket = context.user_data[constants.TICKETS][
        context.user_data[constants.TICKET_ID]
    ]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["Owner"]}
        Статус: {ticket["State"]}
        Предельное время решения: {'SolutionTimeDestinationDate' in ticket and ticket["SolutionTimeDestinationDate"] or None}
    """

    buttons = [
        [InlineKeyboardButton(text="Назад", callback_data=str(ConversationHandler.END))]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[constants.START_OVER] = True

    return constants.SELECTING_FEATURE

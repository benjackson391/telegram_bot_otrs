import logging

from tgbot import common, helper, constants
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler


log = logging.getLogger(__name__)


async def check_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def check.check_tickets")

    context.user_data[constants.CURRENT_STEP] = str(constants.CHECK_TICKET)
    return await show_open_tickets(update, context, "Открытые заявки")


async def show_open_tickets(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text
) -> str:
    common.debug("def check.show_open_tickets")

    context.user_data[constants.TICKETS] = helper.collect_tickets(context.user_data)

    buttons = helper.build_ticket_buttons(context.user_data[constants.TICKETS])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=f"{text} ({len(context.user_data[constants.TICKETS].keys())})",
        reply_markup=keyboard,
    )

    return constants.SELECTING_FEATURE


async def show_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    common.debug("def check.show_ticket")

    context.user_data[constants.TICKET_ID] = update.callback_query.data.split("_")[-1]
    context.user_data[constants.TICKETS] = helper.collect_tickets(context)

    ticket = context.user_data[constants.TICKETS][
        context.user_data[constants.TICKET_ID]
    ]

    text = f"""
        Номер заявки: #{ticket["TicketNumber"]}
        Тип: {ticket["Type"]}
        Исполнитель: {ticket["ExtendedOwner"]["UserFirstname"]} {ticket["ExtendedOwner"]["UserLastname"]}
        Статус: {constants.TRANSLATION.get(ticket["State"])}
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

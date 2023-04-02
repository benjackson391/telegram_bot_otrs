import json, logging, requests, redis, concurrent.futures

from decouple import config
from typing import Any
from telegram import InlineKeyboardButton
from tgbot import constants, common

log = logging.getLogger(__name__)
r = redis.Redis(host=config("REDIS"), port=6379, db=0)


def get_return_button(end=constants.END):
    return [InlineKeyboardButton(text="Назад", callback_data=str(end))]


def _otrs_request(path: str, json: str) -> Any:
    common.debug("def helper._otrs_request")
    common.debug(f"path: {path} request: {json}")

    json["UserLogin"] = config("OTRS_USER")
    json["Password"] = config("OTRS_PASSWORD")

    response = requests.post(f'{config("URL")}/{path}', json=json)
    response_json = response.json()
    common.debug(f"code: {response.status_code} raw: {response_json}")

    return response_json


def collect_ticket(ticket_id, collected_tickets):
    logging.info("def helper.collect_ticket")
    collected_tickets[ticket_id] = _otrs_request(f"ticket/{ticket_id}", {})["Ticket"][0]


def collect_tickets(user_login=""):
    logging.info("def helper.collect_tickets")

    if user_login and r.exists(user_login):
        return json.loads(r.get(user_login))

    collected_tickets = {}
    tickets = _otrs_request(
        "search",
        {
            "CustomerUserLogin": user_login,
            "StateType": ["open", "new", "pending reminder"],
        },
    )

    if not tickets:
        return collected_tickets

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for ticket_id in tickets.get("TicketID"):
            executor.submit(collect_ticket, ticket_id, collected_tickets)

    r.set(user_login, json.dumps(collected_tickets))
    r.expire(user_login, constants.EXPIRATION)

    return collected_tickets


def build_ticket_buttons(tickets=[]):
    logging.info("def helper.build_ticket_buttons")

    buttons = []
    for ticket_id in tickets:
        ticket = tickets[ticket_id]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"#{ticket['TicketNumber']}: {ticket['Title']}",
                    callback_data=f"TICKET_{ticket['TicketID']}",
                )
            ]
        )

    buttons.append(get_return_button())
    return buttons

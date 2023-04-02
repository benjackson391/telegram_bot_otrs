import json, logging, requests, redis, concurrent.futures, random

from decouple import config
from typing import Any
from telegram import InlineKeyboardButton
from tgbot import constants, common

log = logging.getLogger(__name__)
r = redis.Redis(host=config("REDIS"), port=6379, db=0)


def _otrs_request(path: str, json: str) -> Any:
    common.debug("def helper._otrs_request")
    common.debug(f"path: {path} request: {json}")

    json["UserLogin"] = config("OTRS_USER")
    json["Password"] = config("OTRS_PASSWORD")

    response = requests.post(f'{config("URL")}/{path}', json=json)
    response_json = response.json()
    common.debug(f"code: {response.status_code} raw: {response_json}")

    return response_json


def _get_redis(key):
    raw = r.get(key)
    return json.loads(raw)


def _set_redis(key, value):
    r.set(key, json.dumps(value))
    r.expire(key, constants.EXPIRATION)


def _redis_update(key, value):
    current_value = _get_redis(key)
    result = current_value + value
    _set_redis(key, result)


def get_return_button(end=constants.END):
    return [InlineKeyboardButton(text="Назад", callback_data=str(end))]


def collect_ticket(ticket_id, collected_tickets):
    ticket = {}
    if r.exists(ticket_id):
        ticket = _get_redis(ticket_id)
    else:
        ticket = _otrs_request(f"ticket/{ticket_id}", {})["Ticket"][0]
        _set_redis(ticket_id, ticket)

    collected_tickets[ticket_id] = ticket


def collect_tickets(user_data={}):
    common.debug("def helper.collect_tickets")
    common.debug(user_data)
    user_login = ""

    collected_tickets = {}
    tickets = {}
    if random.randint(0, 1) > 0 and r.exists(user_login):
        tickets = _get_redis(user_login)
    else:
        res = _otrs_request(
            "search",
            {
                "CustomerUserLogin": user_login,
                "StateType": ["open", "new", "pending reminder"],
            },
        )
        tickets = res.get("TicketID") if res else {}

        _set_redis(user_login, tickets)

    if tickets:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            for ticket_id in tickets:
                executor.submit(collect_ticket, ticket_id, collected_tickets)

    return collected_tickets


def build_ticket_buttons(tickets=[]):
    common.debug("def helper.build_ticket_buttons")

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

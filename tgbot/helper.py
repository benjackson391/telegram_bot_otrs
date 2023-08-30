import json, logging, requests, redis, concurrent.futures, random

from decouple import config
from typing import Any
from telegram import InlineKeyboardButton
from tgbot import constants, common

log = logging.getLogger(__name__)
redis_host = 'localhost' if config("DEBUG") else 'redis'
r = redis.Redis(host=redis_host, port=6379, db=0)


def _otrs_request(path: str, json: str) -> Any:
    common.debug("def helper._otrs_request")

    json["UserLogin"] = config("OTRS_USER")
    json["Password"] = config("OTRS_PASSWORD")

    response = requests.post(f'{config("URL")}/{path}', json=json, verify=False)
    response_json = response.json()
    # common.debug(f"code: {response.status_code} raw: {response_json}")

    return response_json


def _get_redis(key):
    if r.exists(key):
        return json.loads(r.get(key))

    return None


def _set_redis(key, value):
    r.set(key, json.dumps(value))
    r.expire(key, constants.EXPIRATION)


def _redis_update(key, value):
    current_value = _get_redis(key)
    if not current_value:
        return None

    result = current_value + value
    _set_redis(key, result)


def get_return_button(end=constants.END):
    return [InlineKeyboardButton(text="Назад", callback_data=str(end))]


def collect_ticket(ticket_id, collected_tickets):
    ticket = {}
    if r.exists(ticket_id):
        ticket = _get_redis(ticket_id)
    else:
        ticket = _otrs_request(
            f"ticket/{ticket_id}",
            {
                "DynamicFields": 1,
                "AllArticles": True,
                "ArticleLimit": 1,
                "Extended": True,
                "ArticleOrder": "ASC",
            },
        )["Ticket"][0]
        _set_redis(ticket_id, ticket)

    collected_tickets[ticket_id] = ticket


def collect_tickets(user_data={}):
    common.debug("def helper.collect_tickets")
    user_login = user_data.get(constants.CUSTOMER_USER_LOGIN)

    collected_tickets = {}
    tickets = {}
    if random.randint(0, 1) > 0 and r.exists(user_login):
        tickets = _get_redis(user_login)
    else:
        res = _otrs_request(
            "search",
            {
                "CustomerUserLogin": user_login,
                "StateType": ["open", "new", "pending reminder", "pending auto"],
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

    ticket_status_check = {
        "open": [],
        "pending": [],
        "open_count": 0,
        "pending_count": 0,
    }

    buttons = []
    for ticket_id in tickets:
        ticket = tickets[ticket_id]
        if ticket["StateType"] == "pending auto":
            ticket_status_check["pending"].append(ticket_id)
        else:
            ticket_status_check["open"].append(ticket_id)

    ticket_status_check["open_count"] = len(ticket_status_check["open"])
    ticket_status_check["pending_count"] = len(ticket_status_check["pending"])

    if ticket_status_check["open_count"] > 0:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"Открытые заявки ({ticket_status_check['open_count']})",
                    callback_data="TICKET_STATUS_OPEN",
                )
            ]
        )

    if ticket_status_check["pending_count"] > 0:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"Заявки на оценку ({ticket_status_check['pending_count']})",
                    callback_data="TICKET_STATUS_PENDING",
                )
            ]
        )

    buttons.append(get_return_button())
    return buttons, ticket_status_check

from typing import Any, Dict, Tuple
import json, logging, requests

log = logging.getLogger(__name__)

otrs_url = "https://otrs.efsol.ru/otrs/nph-genericinterface.pl/Webservice/bot"
otrs_user = "telegram_bot"
otrs_password = "GBYudLWmfGQV"


def _set_logging(log_object, args):
    logging = log_object
    return True


def _otrs_request(path: str, json: str) -> Any:
    logging.debug("def _otrs_request")

    logging.info(f"path: {path} request: {json}")

    json["UserLogin"] = otrs_user
    json["Password"] = otrs_password

    response = requests.post(f"{otrs_url}/{path}", json=json)
    response_json = response.json()
    logging.info(f"code: {response.status_code} raw: {response_json}")

    return response_json

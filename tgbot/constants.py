from telegram.ext import ConversationHandler

END = ConversationHandler.END

ADMIN_IDS = [175214250]
EXPIRATION = 600  # 6000

TRANSLATION = {
    "new": "новая",
    "open": "открыта",
    "pending reminder": "ожидает напоминания",
    "pending auto": "ожидает автозакрытия",
}

(
    # 0
    ATTACHMENT,
    # 1
    AUTHORISATION,
    # 2
    BODY,
    # 3
    CHECK_TICKET,
    # 4
    COMMENT,
    # 5
    CONFIRMATION_CODE,
    # 6
    CREATE,
    # 7
    CREATE_WITH_ATTACHMENT,
    # 8
    CUSTOMER_USER_LOGIN,
    # 9
    EMAIL,
    # 10
    NEW_TICKET,
    # 11
    SELECTING_ACTION,
    # 12
    SELECTING_FEATURE,
    # 13
    SHOW_TICKETS,
    # 14
    START_OVER,
    # 15
    SUBJECT,
    # 16
    TICKETS,
    # 17
    TICKET_ID,
    # 18
    UPDATE_TICKET,
    # 19
    UPLOAD,
    # 20
    USER_IS_AUTHORIZED,
) = map(int, range(0, 21))

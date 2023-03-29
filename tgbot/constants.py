from telegram.ext import ConversationHandler

END = ConversationHandler.END

ADMIN_IDS = [175214250]
EXPIRATION = 60  # 6000

TRANSLATION = {
    "new": "новая",
    "open": "открыта",
    "pending reminder": "ожидает напоминания",
    "pending auto": "ожидает автозакрытия",
}

# auth
# update
COMMENT = 0
# check
# create
(
    NEW_TICKET,  # 0
    SUBJECT,  # 1
    BODY,  # 2
    ATTACHMENT,  # 3
    UPLOAD,  # 4
    FINISH,  # 5
    CREATE,  # 6
    CREATE_WITH_ATTACHMENT,  # 7
    FILE_PATH,  # 8
    FILE_NAME,  # 9
    FILE_TYPE,  # 10
) = range(1, 12)

(
    # states
    USER_IS_AUTHORIZED,  # 12
    AUTHORISATION,  # 13
    NEW_TICKET,  # 14
    CHECK_TICKET,  # 15
    UPDATE_TICKET,  # 16
    START_OVER,  # 17
    SELECTING_ACTION,  # 18
    CURRENT_STEP,  # 19
    TYPING,  # 20
    AUTHORISATION_PROCESS,  # 21
    AUTH_PROCESS,  # 22
    CONFIRMATION_CODE,  # 23
    CONFIRMATION_CODE_STATUS,  # 24
    START_OVER,  # 25
    CUSTOMER_USER_LOGIN,  # 26
    SELECTING_FEATURE,  # 27
    OVERVIEW,  # 28
    STOPPING,  # 29
    TICKETS,  # 30
    TICKET_ID,  # 31
    # new_ticket
    # attributes
    EMAIL,  # 32
    # errors
    EMAIL_NOT_FOUND,  # 33
    UPLOAD_ATTACHMENT,  # 34
    SHOW_TICKETS,
) = map(int, range(12, 36))

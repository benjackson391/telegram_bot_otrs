from telegram.ext import ConversationHandler

END = ConversationHandler.END

ADMIN_IDS = [175214250]

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
) = range(0, 11)

(
    # states
    USER_IS_AUTHORIZED,  # 11
    AUTHORISATION,  # 12
    NEW_TICKET,  # 13
    CHECK_TICKET,  # 14
    UPDATE_TICKET,  # 15
    START_OVER,  # 16
    SELECTING_ACTION,  # 17
    CURRENT_STEP,  # 18
    TYPING,  # 19
    AUTHORISATION_PROCESS,  # 20
    AUTH_PROCESS,  # 21
    CONFIRMATION_CODE,  # 22
    CONFIRMATION_CODE_STATUS,  # 23
    START_OVER,  # 24
    CUSTOMER_USER_LOGIN,  # 25
    SELECTING_FEATURE,  # 26
    OVERVIEW,  # 27
    STOPPING,  # 28
    TICKETS,  # 29
    TICKET_ID,  # 30
    NEW_COMMENT,  # 31
    # new_ticket
    # attributes
    EMAIL,  # 32
    # errors
    EMAIL_NOT_FOUND,  # 33
    UPLOAD_ATTACHMENT,  # 34
    # ) = map(chr, range(0, 10))
) = range(11, 35)

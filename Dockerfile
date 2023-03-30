
FROM python:3.10-slim AS bot

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100

# Env vars
ENV TELEGRAM_TOKEN ${TELEGRAM_TOKEN}

RUN apt-get update
RUN apt-get install -y python3 python3-pip python-dev build-essential python3-venv

RUN mkdir -p /opt/efsl_bot
COPY . /opt/efsl_bot
WORKDIR /opt/efsl_bot

RUN pip3 install -r requirements.txt
RUN chmod a+x /opt/efsl_bot/bot.py

CMD python3 /opt/efsl_bot/bot.py;

FROM efsol_bot_base:latest

COPY . /opt/efsl_bot
WORKDIR /opt/efsl_bot

RUN pip3 install -r requirements.txt

RUN chmod a+x /opt/efsl_bot/bot.py
CMD python3 /opt/efsl_bot/bot.py;
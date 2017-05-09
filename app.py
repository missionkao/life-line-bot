import os
from bs4 import BeautifulSoup
from urllib.request import urlopen
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
YOUR_CHANNEL_SECRET = os.environ.get("SECRET")

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

USER_ID = "U7fc6670c8ae890fcaf33f99a9796fcfc"

dataid = "F-C0032-009"
authorizationkey = "CWB-BE234F8A-9F14-4069-A9F5-8795A3C20BC3"
url = "http://opendata.cwb.gov.tw/opendataapi?\
dataid={}&authorizationkey={}".format(dataid, authorizationkey)


@app.route("/")
def hello():
    return "hello"


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK', 200


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == "天氣":
        print("start parsing")
        content = parse_weather()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    else:
        print("user_id:", event.source.user_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text))


def parse_weather():
    print(url)
    data = urlopen(url).read()
    print("Downloaded")
    soup = BeautifulSoup(data, "xml")

    weather = soup.find("parameterSet")
    parameters = weather.find_all("parameterValue")
    results = ""
    for parameter in parameters:
        result = parameter.text
        result_text = result.replace(" ", "").replace("\n", "")
        results = results + result_text + "\n"
    return results


if __name__ == "__main__":
    app.run()

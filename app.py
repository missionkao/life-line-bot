import os
from flask import Flask, request, abort
import requests

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

URL = "http://data.taipei/opendata/datalist/apiAccess"

payload_base = {"scope": "resourceAquire",
                "q": "大安區",
                }
temperature_rid = "1f1aaba5-616a-4a33-867d-878142cac5c4"
rain_rid = "00fcb626-9296-4ae1-9c87-f019871755c8"


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
        payload_base["rid"] = temperature_rid
        temperature_min, temperature_max = parse_weather(payload_base)
        temperature = "氣溫{} ~ {}度".format(temperature_min, temperature_max)
        print(temperature)

        payload_base["rid"] = rain_rid
        rain_min, rain_max = parse_weather(payload_base)
        rain = "降雨機率{} ~ {}%".format(rain_min, rain_max)
        print(rain)

        content = temperature + "\n" + rain

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
    else:
        print("user_id:", event.source.user_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text))


def parse_weather(payload):
    r = requests.get(URL, params=payload)
    data = r.json()
    weathers = data["result"]["results"]
    values = [w["value"] for w in weathers]
    max_value = max(values)
    min_value = 0 if min(values) is "" else min(values)
    return min_value, max_value


if __name__ == "__main__":
    app.run()

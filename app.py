import os
from flask import Flask, request, abort
import requests
from urllib.parse import quote

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage,
    ButtonsTemplate, PostbackTemplateAction, LocationMessage,
    CarouselTemplate, CarouselColumn, URITemplateAction
)

app = Flask(__name__)
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
YOUR_CHANNEL_SECRET = os.environ.get("SECRET")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

USER_ID = "U7fc6670c8ae890fcaf33f99a9796fcfc"

URL = "http://data.taipei/opendata/datalist/apiAccess"
GOOGLE_URI = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

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
    print("user_id:", event.source.user_id)
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
        image_url = get_image_url(int(rain_max))
        template_message = TemplateSendMessage(
            alt_text="天氣預報",
            template=ButtonsTemplate(
                thumbnail_image_url=image_url,
                text=content,
                actions=[
                    PostbackTemplateAction(
                        label="天氣預報",
                        data=" "
                    )]
            )
        )

        line_bot_api.reply_message(
            event.reply_token,
            template_message)
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text))


@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    print("user_id:", event.source.user_id)
    print("latitude: ", event.message.latitude)
    print("longitude: ", event.message.longitude)
    location = "{},{}".format(event.message.latitude, event.message.longitude)
    columns = get_restaurants_carousel(location)
    carousel_template = CarouselTemplate(columns=columns)
    template_message = TemplateSendMessage(
        alt_text="餐廳小幫手",
        template=carousel_template
    )
    line_bot_api.reply_message(
        event.reply_token, template_message)


def parse_weather(payload):
    r = requests.get(URL, params=payload)
    data = r.json()
    weathers = data["result"]["results"]
    values = [w["value"] for w in weathers]
    max_value = max(values)
    min_value = 0 if min(values) is "" else min(values)
    return min_value, max_value


def get_image_url(max_rain):
    if max_rain >= 50:
        return "https://i.imgur.com/a34ds01.jpg"
    elif max_rain >= 20:
        return "https://i.imgur.com/66aSMf1.jpg"
    else:
        return "https://imgur.com/JQ7S8zM.jpg"


def get_restaurants_carousel(location):
    payload = {
        "location": location,
        "radius": 500,
        "type": "restaurant",
        "key": GOOGLE_API_KEY,
        "language": "zh-TW"
    }
    r = requests.get(GOOGLE_URI, params=payload)
    r_json = r.json()
    json_results = r_json["results"]
    json_results = sorted(json_results,
                          key=lambda k: k.get("rating", 0), reverse=True)
    results = []
    for r in json_results[0:5]:
        title = r["name"]
        rating = "Rating: " + str(r["rating"])
        address = r["vicinity"]
        title_uri = "https://www.google.com.tw/search?q=" + quote(title)
        address_uri = "https://www.google.com.tw/maps/place/" + quote(title)
        carousel = CarouselColumn(title=title, text=rating, actions=[
            URITemplateAction(
                label=title, uri=title_uri),
            URITemplateAction(
                label=address, uri=address_uri),
        ])
        results.append(carousel)
    return results


if __name__ == "__main__":
    app.run()

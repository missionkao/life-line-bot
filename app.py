import os
from flask import Flask, request, abort
import requests
from urllib.parse import quote
import apiai
import json

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TemplateSendMessage,
    ButtonsTemplate, PostbackTemplateAction, LocationMessage,
    CarouselTemplate, CarouselColumn, URITemplateAction,
    ImageSendMessage
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

API_ACCESS_TOKEN = os.environ.get("API_ACCESS_TOKEN")
ai = apiai.ApiAI(API_ACCESS_TOKEN)
metro_location = {
    "中山站": "25.0494808,121.5305508",
    "古亭站": "25.0287819,121.5293875",
    "松江南京站": "25.0404992,121.5248012",
    "南京復興站": "25.0500368,121.5414228",
    "公館站": "25.0059467,121.5328129",
    "西門站": "25.0406857,121.5097222",
    "東門站": "25.0308339,121.5290304",
    "忠孝新生站": "25.0383673,121.5347948",
    "忠孝復興站": "25.0383673,121.5347948",
    "忠孝敦化站": "25.0383673,121.5347948",
    "市政府站": "25.0377011,121.5460339",
    "亞東醫院站": "24.9937778,121.4544763",
}

blank_image = "https://imgur.com/u4N3wpJ.jpg"


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
        location = get_response_from_api_ai(event.message.text)
        print("get location from api: ", location)
        if location is "empty":
            image_message = ImageSendMessage(
                original_content_url=blank_image,
                preview_image_url=blank_image
            )
            line_bot_api.reply_message(
                event.reply_token, image_message)
        columns = get_restaurants_carousel(location)
        carousel_template = CarouselTemplate(columns=columns)
        template_message = TemplateSendMessage(
            alt_text="餐廳小幫手",
            template=carousel_template
        )
        line_bot_api.reply_message(
            event.reply_token, template_message)


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
        print(title, rating, address, title_uri, address_uri)
        carousel = CarouselColumn(title=title, text=rating, actions=[
            # the max label text size is 20, take 15 for safety
            URITemplateAction(
                label=title[0:15], uri=title_uri),
            URITemplateAction(
                label=address[0:15], uri=address_uri),
        ])
        results.append(carousel)
    return results


def get_response_from_api_ai(text):
    request = ai.text_request()
    request.lang = "zh-tw"  # optional, default value equal 'en'
    request.session_id = "demo-session"
    request.query = text
    response = json.loads(request.getresponse().read())

    result = response["result"]
    parameters = result.get("parameters", "empty")
    taipei_metro = parameters.get("taipei_metro", "empty")
    location = metro_location.get(taipei_metro, "empty")
    return location


if __name__ == "__main__":
    app.run()

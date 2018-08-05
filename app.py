import requests
import re
import random
import configparser
import os
import os.path
from urllib.request import urlopen
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from imgurpython import ImgurClient

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)
config = configparser.ConfigParser()
config.read("config.ini")

line_bot_api = LineBotApi(os.environ.get("ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("SECRET"))
client_id = config['imgur_api']['Client_ID']
client_secret = config['imgur_api']['Client_Secret']
album_id = config['imgur_api']['Album_ID']
API_Get_Image = config['other_api']['API_Get_Image']


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # print("body:",body)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        app.logger.error(e)
        abort(400)

    return 'ok'


def create_attendee_list():
    attend_dict = {}
    target_url = "https://raw.githubusercontent.com/chengjia-su/curtis_line_bot/master/list.dat"
    # with open("list.dat", "r") as file:
    with urlopen(target_url) as file:
        for line in file:
            data = line.decode('utf-8').split(";")
            new_rec = {data[0]: {"loc": data[1],
                                 "num_att": data[2],
                                 "food": data[3],
                                 "chair": data[4]}
                      }
            attend_dict.update(new_rec)
    return attend_dict

def query_attendee(name):
    reply_msg = ""
    attend_dict = create_attendee_list()
    for key, val in attend_dict.items():
        if name in key:
            res = attend_dict[key]
            reply_msg = ("名字: {name}\n"
                         "場次: {loc}\n"
                         "出席人數: {num}\n"
                         "葷素: {food}\n"
                         "嬰兒座椅需求: {ch}").format(name=key,
                                                     loc=res["loc"],
                                                     num=res["num_att"],
                                                     food=res["food"],
                                                     ch=res["chair"])
            break
    if reply_msg == "":
        reply_msg = "無法找到您的報名資訊, 請與新郎政嘉聯繫.\n若您剛完成報名, 請通知新郎更新報名資訊."
    return reply_msg


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)


    if os.path.exists(event.source.user_id):
        msg = query_attendee(event.message.text)
        text_reply = TextSendMessage(text=msg)
        line_bot_api.reply_message(event.reply_token, text_reply)
        os.remove(event.source.user_id)
        return 0

    if event.message.text == "彰化-結婚宴地點":
        loc = LocationSendMessage(title='結婚婚宴會場', address='花壇全國麗園大飯店',
                                  latitude=24.023089, longitude=120.555030)
        line_bot_api.reply_message(
            event.reply_token,
            loc)
        return 0

    if event.message.text == "宜蘭-訂婚宴地點":
        loc = LocationSendMessage(title='訂婚婚宴會場', address='羅東金門餐廳',
                                  latitude=24.678694, longitude=121.763427)
        line_bot_api.reply_message(
            event.reply_token,
            loc)
        return 0

    if event.message.text == "彰化-結婚宴時間":
        reply_msg = TextSendMessage(text="2018/11/25 (日) 開桌時間未定")
        line_bot_api.reply_message(
            event.reply_token,
            reply_msg)
        return 0

    if event.message.text == "宜蘭-訂婚宴時間":
        reply_msg = TextSendMessage(text="2018/10/10 (日) 開桌時間未定")
        line_bot_api.reply_message(
            event.reply_token,
            reply_msg)
        return 0

    if event.message.text == "查詢報名結果":
        reply_msg = TextSendMessage(text="請輸入您的名字查詢")
        line_bot_api.reply_message(
            event.reply_token,
            reply_msg)
        with open(event.source.user_id, 'a') as file:
            pass
        return 0

    if event.message.text == "來張 imgur 正妹圖片":
        client = ImgurClient(client_id, client_secret)
        images = client.get_album_images(album_id)
        index = random.randint(0, len(images) - 1)
        url = images[index].link
        image_message = ImageSendMessage(
            original_content_url=url,
            preview_image_url=url
        )
        line_bot_api.reply_message(
            event.reply_token, image_message)
        return 0

    if event.message.text == "隨便來張正妹圖片":
        image = requests.get(API_Get_Image)
        url = image.json().get('Url')
        image_message = ImageSendMessage(
            original_content_url=url,
            preview_image_url=url
        )
        line_bot_api.reply_message(
            event.reply_token, image_message)
        return 0


    if "地點" in event.message.text:
        confirm_template = TemplateSendMessage(
            alt_text='婚宴地點 template',
            template=ConfirmTemplate(
                title='選擇場次',
                text='請選擇',
                actions=[
                    MessageTemplateAction(
                        label='宜蘭-訂婚宴地點',
                        text='宜蘭-訂婚宴地點'
                    ),
                    MessageTemplateAction(
                        label='彰化-結婚宴地點',
                        text='彰化-結婚宴地點'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, confirm_template)
        return 0

    if "日期" in event.message.text or "時間" in event.message.text:
        confirm_template = TemplateSendMessage(
            alt_text='婚宴時間 template',
            template=ConfirmTemplate(
                title='選擇場次',
                text='請選擇',
                actions=[
                    MessageTemplateAction(
                        label='宜蘭-訂婚宴時間',
                        text='宜蘭-訂婚宴時間'
                    ),
                    MessageTemplateAction(
                        label='彰化-結婚宴時間',
                        text='彰化-結婚宴時間'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, confirm_template)
        return 0

    buttons_template = TemplateSendMessage(
        alt_text='目錄 template',
        template=ButtonsTemplate(
            title='選擇服務',
            text='請選擇',
            thumbnail_image_url='https://i.imgur.com/CVVtdN0.jpg',
            actions=[
                MessageTemplateAction(
                    label='婚宴地點',
                    text='婚宴地點'
                ),
                MessageTemplateAction(
                    label='婚宴日期時間',
                    text='婚宴日期時間'
                ),
                MessageTemplateAction(
                    label='查詢報名結果',
                    text='查詢報名結果'
                ),
                URITemplateAction(
                    label='報名',
                    uri='https://goo.gl/forms/wBVMcLs93DnOh6W13'
                )
            ]
        )
    )
    line_bot_api.reply_message(event.reply_token, buttons_template)


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    print("package_id:", event.message.package_id)
    print("sticker_id:", event.message.sticker_id)
    # ref. https://developers.line.me/media/messaging-api/sticker_list.pdf
    sticker_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21, 100, 101, 102, 103, 104, 105, 106,
                   107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125,
                   126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 401, 402]
    index_id = random.randint(0, len(sticker_ids) - 1)
    sticker_id = str(sticker_ids[index_id])
    print(index_id)
    sticker_message = StickerSendMessage(
        package_id='1',
        sticker_id=sticker_id
    )
    line_bot_api.reply_message(
        event.reply_token,
        sticker_message)


if __name__ == '__main__':
    app.run()

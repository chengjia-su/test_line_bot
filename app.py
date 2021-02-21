import requests
import re
import random
import configparser
import os
import os.path
import psycopg2
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
    
def query_car(number):
    ret = []
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url, sslmode='require')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM mzd_car WHERE lice = '{}'".format(number))
    all_data = cursor.fetchall()
    for data in all_data:
        ret.append(data[0])
    conn.close()

    return ret

def register_car(number, name):
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url, sslmode='require')
    cursor = conn.cursor()
    create_table = '''CREATE TABLE IF NOT EXISTS mzd_car(
        id serial PRIMARY KEY,
        lice INT NOT NULL,
        name VARCHAR (255)
    );'''
    cursor.execute(create_table)
    conn.commit()

    cursor.execute("SELECT name FROM mzd_car WHERE lice = '{}';".format(number))
    all_data = cursor.fetchall()
    ret = True
    for data in all_data:
        if name == data[0]:
            ret = False
            break
    if ret:
        insert_dat = "INSERT INTO mzd_car (lice, name) VALUES ({}, '{}');".format(number, name)
        cursor.execute(insert_dat)
        conn.commit()
        
    cursor.close()
    conn.close()

    return ret

def unregister_car(number, name):
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url, sslmode='require')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM mzd_car WHERE lice = '{}';".format(number))
    all_data = cursor.fetchall()
    ret = False
    for data in all_data:
        if name == data[0]:
            ret = True
            break
    if ret:
        insert_dat = "DELETE FROM mzd_car WHERE lice = '{}' AND name = '{}';".format(number, name)
        cursor.execute(insert_dat)
        conn.commit()
        
    cursor.close()
    conn.close()

    return ret    

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)

    req_msg = str(event.message.text)
        
    if req_msg.startswith("++") and req_msg[2:6].isnumeric():
        number = req_msg[2:6]
        name = req_msg.split(":")[-1]
        ret = register_car(number, name)
        if ret:
            reply_msg = TextSendMessage(text="車牌【{}】註冊成功, 車主:{}".format(number, name))
        else:
            reply_msg = TextSendMessage(text="車牌【{}】註冊失敗, 車主{}已存在".format(number, name))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith("??") and req_msg[2:6].isnumeric():
        number = req_msg[2:6]
        ret = query_car(number)
        if len(ret) > 0:
            names = "\n".join(ret)
            reply_msg = TextSendMessage(text="查詢車牌【{}】:\n{}".format(number, names))
        else:
            reply_msg = TextSendMessage(text="查詢車牌【{}】:\n尚無車主註冊".format(number))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith("--") and req_msg[2:6].isnumeric():
        number = req_msg[2:6]
        name = req_msg.split(":")[-1]
        ret = unregister_car(number, name)
        if ret:
            reply_msg = TextSendMessage(text="車牌【{}: {}】刪除成功".format(number, name))
        else:
            reply_msg = TextSendMessage(text="車牌【{}: {}】刪除失敗, 找不到註冊資料".format(number, name))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0
        
"""
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
"""

if __name__ == '__main__':
    app.run()

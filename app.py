import requests
import re
import random
import configparser
import os
import os.path
import psycopg2
from urllib.request import urlopen
from bs4 import BeautifulSoup
from flask import Flask, request, abort, render_template, url_for, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
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
app.secret_key = config['flask']['secret_key']

line_bot_api = LineBotApi(os.environ.get("ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("SECRET"))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = 'login'

users = {'curtis': {'password': 'Mazda!cx30@6576'}}

class User(UserMixin):
    pass

@login_manager.user_loader
def user_loader(test_user):
    if test_user not in users:
        return

    user = User()
    user.id = test_user
    return user

@login_manager.request_loader
def request_loader(request):
    test_user = request.form.get('user_id')
    if test_user not in users:
        return

    user = User()
    user.id = test_user

    # DO NOT ever store passwords in plaintext and always compare password
    # hashes using constant-time comparison!
    user.is_authenticated = request.form['password'] == users[test_user]['password']

    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    
    test_user = request.form['user_id']
    if (test_user in users) and (request.form['password'] == users[test_user]['password']):
        user = User()
        user.id = test_user
        login_user(user)
        return redirect(url_for('home'))

    flash('帳號或密碼錯誤!非版主請勿嘗試登入!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    test_user = current_user.get_id()
    logout_user()
    return render_template('login.html')

@app.route("/")
@login_required
def home():
    return render_template("home.html")

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

def query_color_number(color):
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url, sslmode='require')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM mzd_car WHERE color = '{}'".format(color))
    color_num = cursor.fetchone()[0]
    conn.close()

    return color_num

def query_car(number):
    ret = []
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url, sslmode='require')
    cursor = conn.cursor()
    cursor.execute("SELECT name, color FROM mzd_car WHERE lice = '{}'".format(number))
    all_data = cursor.fetchall()
    for data in all_data:
        if data[1] is None:
            ret.append("{} / {}".format(data[0], "未登記車色"))
        else:
            ret.append("{} / {}".format(data[0], data[1]))
    conn.close()

    return ret

def get_color_fullname(color):
    if "雪" in color and "白" in color:
        return "躍雪白"
    elif "極" in color and "白" in color:
        return "極粹白"
    elif "極" in color and "灰" in color:
        return "極境灰"
    elif "鋼" in color and "灰" in color:
        return "鋼鐵灰"
    elif "黑" in color:
        return "御鉄黑"
    elif "紅" in color:
        return "晶艷魂動紅"
    elif "藍" in color:
        return "星燦藍"
    elif "銀" in color:
        return "飛梭銀"
    elif "棕" in color:
        return "鈦金棕"
    elif "琉光" in color or "光金" in color:
        return "琉光金"
    else:
        return None

def register_car(number, name, color):
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url, sslmode='require')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM mzd_car WHERE lice = '{}';".format(number))
    all_data = cursor.fetchall()
    ret = True
    for data in all_data:
        if name == data[0]:
            ret = False
            break
    if ret:
        insert_dat = "INSERT INTO mzd_car (lice, name, color) VALUES ({}, '{}', '{}');".format(number, name, color)
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

    req_msg = str(event.message.text).strip()
        
    if req_msg.startswith("++") and req_msg[2:6].isnumeric():
        if ":" not in req_msg or "/" not in req_msg:
            reply_msg = TextSendMessage(text="註冊車牌格式錯誤. 格式應為:\n++[車號數字四位數]:[車主名]/[車色]\n例如 ++1234:彰化金城武/躍雪白")
        else:
            number = req_msg[2:6]
            pre_msg = req_msg.split("/")[0]
            color_in = req_msg.split("/")[-1].strip()
            name = pre_msg.split(":")[-1].strip()
            color = get_color_fullname(color_in)
            if color is None:
                reply_msg = TextSendMessage(text="車牌【{}】註冊失敗, 車色 {} 無法辨識".format(number, color_in))
                line_bot_api.reply_message(event.reply_token, reply_msg)
                return 0

            ret = register_car(number, name, color)
            if ret:
                reply_msg = TextSendMessage(text="車牌【{}】註冊成功, 車主:{} 車色:{}".format(number, name, color))
            else:
                reply_msg = TextSendMessage(text="車牌【{}】註冊失敗, 車主{}已存在".format(number, name))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith(("C", "c")) and req_msg[1:5].isnumeric():
        number = req_msg[1:5]
        ret = query_car(number)
        if len(ret) > 0:
            names = "\n".join(ret)
            reply_msg = TextSendMessage(text="查詢車牌【{}】:\n{}".format(number, names))
        else:
            reply_msg = TextSendMessage(text="查詢車牌【{}】:\n尚無車主註冊".format(number))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith("--") and req_msg[2:6].isnumeric():
        if ":" not in req_msg:
            reply_msg = TextSendMessage(text="刪除車牌格式錯誤. 格式應為:\n--[車號數字四位數]:[車主名]\n例如 --1234:彰化金城武")
        else:
            number = req_msg[2:6]
            name = req_msg.split(":")[-1].strip()
            ret = unregister_car(number, name)
            if ret:
                reply_msg = TextSendMessage(text="車牌【{}: {}】刪除成功".format(number, name))
            else:
                reply_msg = TextSendMessage(text="車牌【{}: {}】刪除失敗, 找不到註冊資料".format(number, name))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith("!!total"):
        ret_text = "【已註冊車色統計資料】\n躍雪白:{}\n極粹白:{}\n極境灰:{}\n鋼鐵灰:{}\n御鉄黑:{}\n晶艷魂動紅:{}\n星燦藍:{}\n飛梭銀:{}\n鈦金棕:{}\n琉光金:{}".format(query_color_number("躍雪白"),
                                                                                                                                                   query_color_number("極粹白"),
                                                                                                                                                   query_color_number("極境灰"),
                                                                                                                                                   query_color_number("鋼鐵灰"),
                                                                                                                                                   query_color_number("御鉄黑"),
                                                                                                                                                   query_color_number("晶艷魂動紅"),
                                                                                                                                                   query_color_number("星燦藍"),
                                                                                                                                                   query_color_number("飛梭銀"),
                                                                                                                                                   query_color_number("鈦金棕"),
                                                                                                                                                   query_color_number("琉光金"))
        reply_msg = TextSendMessage(text=ret_text)
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

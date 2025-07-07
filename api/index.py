import os
import tempfile
import re
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, MessagingApiBlob,
    ReplyMessageRequest, TextMessage, PushMessageRequest
)
from linebot.v3.webhooks import (
    MessageEvent, ImageMessageContent, TextMessageContent
)
import sys
import os

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_sheets_handler import append_row_to_sheet, get_sheet_service, refresh_sold_items_formatting
from chatgpt_handler import ChatGPTHandler

app = Flask(__name__)
load_dotenv()

LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN:
    raise ValueError("LINE APIトークンが設定されていません")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

chatgpt_handler = ChatGPTHandler()

temp_image_paths: List[str] = []
temp_image_urls: List[str] = []
temp_features: str = ""

def is_management_number(text: str) -> bool:
    """6桁の数字（管理番号）かどうかを判定する"""
    text = text.strip()
    return bool(re.match(r'^\d{6}$', text))

def modify_product_title_with_number(title: str, management_number: str) -> str:
    """商品名の最後6文字を管理番号に置き換える"""
    if len(title) <= 6:
        # 商品名が6文字以下の場合は、管理番号をそのまま使用
        return management_number
    
    # 商品名の最後6文字を管理番号に置き換え
    base_title = title[:-6]
    modified_title = base_title + management_number
    
    # 40文字以内に制限
    if len(modified_title) > 40:
        # 40文字を超える場合は、管理番号を除いた部分を短縮
        max_base_length = 40 - 6
        modified_title = base_title[:max_base_length] + management_number
    
    return modified_title

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    global temp_features
    user_text = event.message.text

    # 売れた商品の色を更新するコマンド
    if user_text == "#更新":
        try:
            sheet = get_sheet_service()
            # すべてのシートを取得
            spreadsheet = sheet.get(spreadsheetId='1r9gAZZlWw40bURXOE2-BJB9OAZPEoPuN8-GZ7iD0yBA').execute()
            total_updated = 0
            
            for worksheet in spreadsheet['sheets']:
                sheet_name = worksheet['properties']['title']
                updated_count = refresh_sold_items_formatting(sheet, sheet_name)
                total_updated += updated_count
            
            reply_text(event.reply_token, f"✅ 売れた商品の色を更新しました。\n更新件数: {total_updated}件")
        except Exception as e:
            reply_text(event.reply_token, f"❌ 更新に失敗しました: {str(e)}")
        return

    if is_management_number(user_text):
        if not temp_image_paths:
            reply_text(event.reply_token, "❌ 先に商品の画像を送信してください。")
            return

        try:
            # テキスト特徴がある場合は従来の処理、ない場合は画像のみの処理
            if temp_features:
                # ChatGPTのVision APIを使用して商品情報を生成（テキスト特徴あり）
                product_info = chatgpt_handler.generate_product_info(temp_image_paths, temp_features)
            else:
                # 画像のみから商品情報を生成
                product_info = chatgpt_handler.generate_product_info_from_images_only(temp_image_paths)
            
            if not product_info:
                reply_text(event.reply_token, "❌ 商品情報の生成に失敗しました。")
                return

            # 商品名の最後6文字を管理番号に置き換え
            original_title = product_info['title']
            modified_title = modify_product_title_with_number(original_title, user_text)
            product_info['title'] = modified_title

            sheet = get_sheet_service()
            success = append_row_to_sheet(sheet, temp_image_paths, product_info, user_text)

            if success:
                # 商品名、商品説明テンプレート、価格を1つのメッセージにまとめる
                combined_message = f"{product_info['title']}\n\n{product_info['template']}\n\n{product_info['start_price']}円"
                
                # LINE Messaging APIの制限（5,000文字）をチェック
                if len(combined_message) <= 5000:
                    # 1つのメッセージとして送信
                    reply_text(event.reply_token, combined_message)
                else:
                    # 制限を超える場合は分割して送信
                    reply_text(event.reply_token, product_info['title'])
                    push_text(event.source.user_id, product_info['template'])
                    push_text(event.source.user_id, f"{product_info['start_price']}円")
            else:
                reply_text(event.reply_token, "❌ スプレッドシートへの保存に失敗しました。")

        finally:
            for path in temp_image_paths:
                try:
                    os.unlink(path)
                except:
                    pass
            temp_image_paths.clear()
            temp_image_urls.clear()
            temp_features = ""
    else:
        temp_features = user_text
        # 返信メッセージを削除して、LINE画面をすっきりさせる

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    global temp_image_paths, temp_image_urls
    with ApiClient(configuration) as api_client:
        blob_api = MessagingApiBlob(api_client)
        content = blob_api.get_message_content(event.message.id)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(content)
            path = f.name
            temp_image_paths.append(path)
        
        # LINEの画像URLを取得（実際のURLは取得できないため、メッセージIDを保存）
        image_url = f"https://api-data.line.me/v2/bot/message/{event.message.id}/content"
        temp_image_urls.append(image_url)

        # 返信メッセージを削除して、LINE画面をすっきりさせる

def reply_text(token: str, message: str):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=token,
                messages=[TextMessage(text=message)]
            )
        )

def push_text(user_id: str, message: str):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).push_message_with_http_info(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=message)]
            )
        )

# Vercel用のエクスポート
if __name__ == "__main__":
    app.run(debug=True)

# Vercel用のエクスポート
app.debug = True 
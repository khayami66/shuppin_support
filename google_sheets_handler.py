import os
import base64
from datetime import datetime
from typing import List, Dict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from supabase_client import upload_image_to_supabase

# スプレッドシートの設定
SPREADSHEET_ID = '1r9gAZZlWw40bURXOE2-BJB9OAZPEoPuN8-GZ7iD0yBA'  # あなたのスプレッドシートID

# Google Sheets APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def get_credentials() -> Credentials:
    """Google Sheets APIのサービスアカウント認証情報を取得"""
    # 環境変数から認証情報を取得（Vercel用）
    google_credentials = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    
    if google_credentials:
        # 環境変数から認証情報を読み込み
        import json
        creds_dict = json.loads(google_credentials)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # ローカル開発用：ファイルから読み込み
        creds = Credentials.from_service_account_file(
            'service_account.json', scopes=SCOPES
        )
    return creds

def get_sheet_service():
    """Google Sheets APIの service.spreadsheets() を返す"""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()

def get_drive_service():
    """Google Drive APIの service を返す"""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_image_to_drive(image_path: str, filename: str) -> str:
    """
    画像をSupabase StorageにアップロードしてパブリックURLを返す
    """
    return upload_image_to_supabase(image_path, filename)

def insert_image_to_sheet(sheet, sheet_name: str, row_number: int, image_url: str):
    """
    スプレッドシートに画像を挿入（IMAGE関数を使用・正方形セル用）
    """
    try:
        # IMAGE関数を使用して画像を表示（アスペクト比保持・セル内中央）
        image_formula = f'=IMAGE("{image_url}", 1)'
        body = {'values': [[image_formula]]}
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A{row_number}',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        print(f"行 {row_number} に画像を挿入しました")
        return True
    except Exception as e:
        print(f"画像挿入エラー: {e}")
        return False

def get_or_create_sheet(sheet, management_number: str) -> str:
    """管理番号の先頭4桁をシート名として取得し、存在しない場合は作成"""
    sheet_name = management_number[:4]  # 先頭4桁を取得
    
    try:
        # 既存のシート一覧を取得
        spreadsheet = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = [worksheet['properties']['title'] for worksheet in spreadsheet['sheets']]
        
        # シートが存在しない場合は作成
        if sheet_name not in existing_sheets:
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            
            body = {'requests': [request]}
            sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
            print(f"新しいシート '{sheet_name}' を作成しました")
            
            # 少し待機してからヘッダー行を追加（シート作成の完了を待つ）
            import time
            time.sleep(1)
            
            # ヘッダー行を追加（エラーが発生しても継続）
            try:
                setup_sheet_headers(sheet, sheet_name)
            except Exception as header_error:
                print(f"ヘッダー設定エラー: {header_error}")
                print("ヘッダー設定に失敗しましたが、シート作成は完了しました")
        else:
            # 既存のシートの場合は、ヘッダーが存在するかチェック
            try:
                check_and_setup_headers(sheet, sheet_name)
            except Exception as check_error:
                print(f"既存シートの設定チェックエラー: {check_error}")
                print("既存シートの設定チェックに失敗しましたが、処理を継続します")
        
        return sheet_name
    except Exception as e:
        print(f"シート取得/作成エラー: {e}")
        print(f"シート '{sheet_name}' の作成に失敗しましたが、処理を継続します")
        return sheet_name

def check_and_setup_headers(sheet, sheet_name: str):
    """既存のシートにヘッダーが存在するかチェックし、なければ設定"""
    try:
        # 1行目を取得してヘッダーが存在するかチェック
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A1:F1'
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values[0]) < 6:
            # ヘッダーが存在しない場合は設定
            setup_sheet_headers(sheet, sheet_name)
        else:
            # ヘッダーが存在する場合は、フォーマット設定と売れた商品の色設定を実行
            # 利益計算式は新規商品追加時にのみ設定するため、ここではスキップ
            setup_sheet_formatting(sheet, sheet_name)
            setup_on_edit_trigger(sheet, sheet_name)
    except Exception as e:
        print(f"ヘッダーチェックエラー: {e}")

def setup_profit_formulas_for_existing_sheet(sheet, sheet_name: str):
    """既存のシートの利益計算式を設定（必要な行のみ）"""
    try:
        # データ行を取得
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A:F'
        ).execute()

        values = result.get('values', [])
        if len(values) > 1:  # ヘッダー行以外にデータがある場合
            setup_count = 0
            for i in range(1, len(values)):
                row_number = i + 1
                # F列（利益列）の値をチェック
                profit_value = values[i][5] if len(values[i]) > 5 else ""
                
                # 数式でない場合のみ設定（空文字、数値、文字列は数式でない）
                is_formula = (profit_value and 
                            (profit_value.startswith('=') or 
                             profit_value.startswith('IF(') or
                             'E' + str(row_number) in profit_value))
                
                # デバッグ情報（最初の数行のみ表示）
                if i <= 3:
                    print(f"行 {row_number}: F列の値 = '{profit_value}', 数式判定 = {is_formula}")
                
                if not is_formula:
                    setup_profit_formula(sheet, sheet_name, row_number)
                    setup_count += 1
            
            if setup_count > 0:
                print(f"シート '{sheet_name}' で {setup_count} 行の利益計算式を設定しました")
            else:
                print(f"シート '{sheet_name}' の利益計算式は既に設定済みです")
            
            # 既存データをチェックして売れた商品に色を設定
            setup_on_edit_trigger(sheet, sheet_name)
    except Exception as e:
        print(f"既存シートの利益計算式設定エラー: {e}")

def setup_sheet_headers(sheet, sheet_name: str):
    """シートのヘッダー行を設定"""
    try:
        headers = ['画像', '商品名', '登録日', '販売日', '販売価格', '利益']
        body = {'values': [headers]}
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A1:F1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        # ヘッダー設定後に少し待機
        import time
        time.sleep(0.5)
        
        # フォーマットを設定
        setup_sheet_formatting(sheet, sheet_name)
        
        print(f"シート '{sheet_name}' のヘッダーを設定しました")
    except Exception as e:
        print(f"ヘッダー設定エラー: {e}")

def setup_sheet_formatting(sheet, sheet_name: str):
    """シートのフォーマットを設定（ヘッダーの太字化・中央揃え・正方形セルなど）"""
    try:
        sheet_id = get_sheet_id(sheet, sheet_name)
        if sheet_id == 0:
            print(f"シート '{sheet_name}' のシートIDが取得できませんでした")
            return
            
        # ヘッダー行を太字にする、A列幅、B列幅、中央揃え、A列正方形化など
        requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 6
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold'
                }
            },
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {
                            'frozenRowCount': 1
                        }
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            },
            {
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 1,  # B列（0ベース）
                        'endIndex': 2
                    }
                }
            },
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,  # A列（0ベース）
                        'endIndex': 1
                    },
                    'properties': {
                        'pixelSize': 250  # A列の幅を250ピクセルに設定
                    },
                    'fields': 'pixelSize'
                }
            },
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': 1,  # 2行目以降
                        'endIndex': 1000  # 仮に1000行目まで
                    },
                    'properties': {
                        'pixelSize': 250  # 行の高さを250ピクセルに設定
                    },
                    'fields': 'pixelSize'
                }
            },
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'startColumnIndex': 1,  # B列（0ベース）
                        'endColumnIndex': 6     # F列まで
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE'
                        }
                    },
                    'fields': 'userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment'
                }
            }
        ]
        
        body = {'requests': requests}
        sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        
        print(f"シート '{sheet_name}' の基本フォーマットを設定しました")
        
        # フォーマット設定後に少し待機
        import time
        time.sleep(0.5)
        
        # 販売日列（D列）にデータ検証を設定
        try:
            setup_date_validation(sheet, sheet_name)
        except Exception as date_error:
            print(f"日付検証設定エラー: {date_error}")
        
        # 販売価格列（E列）に数値検証を設定
        try:
            setup_sale_price_validation(sheet, sheet_name)
        except Exception as price_error:
            print(f"販売価格検証設定エラー: {price_error}")
        
        print(f"シート '{sheet_name}' のフォーマットを設定しました")
    except Exception as e:
        print(f"フォーマット設定エラー: {e}")

def setup_date_validation(sheet, sheet_name: str):
    """販売日列に日付選択のデータ検証を設定"""
    try:
        # シートIDを取得する前に少し待機
        import time
        time.sleep(0.5)
        
        sheet_id = get_sheet_id(sheet, sheet_name)
        if sheet_id == 0:
            print(f"シート '{sheet_name}' のシートIDが取得できませんでした")
            # 再試行
            time.sleep(1)
            sheet_id = get_sheet_id(sheet, sheet_name)
            if sheet_id == 0:
                print(f"シート '{sheet_name}' のシートID取得に失敗しました")
                return
            
        # 販売日列（D列）全体に日付検証を設定
        request = {
            'setDataValidation': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,  # ヘッダー行を除く
                    'startColumnIndex': 3,  # D列（0ベース）
                    'endColumnIndex': 4
                },
                'rule': {
                    'condition': {
                        'type': 'DATE_IS_VALID'
                    },
                    'showCustomUi': True,
                    'strict': True
                }
            }
        }
        
        body = {'requests': [request]}
        sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        
        print(f"シート '{sheet_name}' の販売日列にカレンダー設定を追加しました")
    except Exception as e:
        print(f"日付検証設定エラー: {e}")
        print("日付検証設定に失敗しましたが、システムは継続して動作します")

def setup_sale_price_validation(sheet, sheet_name: str):
    """販売価格列に数値検証を設定"""
    try:
        sheet_id = get_sheet_id(sheet, sheet_name)
        if sheet_id == 0:
            print(f"シート '{sheet_name}' のシートIDが取得できませんでした")
            return
            
        # 販売価格列（E列）全体に数値検証を設定
        request = {
            'setDataValidation': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,  # ヘッダー行を除く
                    'startColumnIndex': 4,  # E列（0ベース）
                    'endColumnIndex': 5
                },
                'rule': {
                    'condition': {
                        'type': 'NUMBER_GREATER_THAN_EQ',
                        'values': [{'userEnteredValue': '0'}]
                    },
                    'showCustomUi': True,
                    'strict': False  # strictをFalseに変更してより柔軟に
                }
            }
        }
        
        body = {'requests': [request]}
        sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        
        print(f"シート '{sheet_name}' の販売価格列に数値検証を追加しました")
    except Exception as e:
        print(f"販売価格検証設定エラー: {e}")
        print("データ検証設定に失敗しましたが、システムは継続して動作します")

def setup_on_edit_trigger(sheet, sheet_name: str):
    """販売日と販売価格が入力された時に自動的に色を変更するトリガーを設定"""
    try:
        # 既存のデータをチェックして、売れた商品に色を設定
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A:F'
        ).execute()
        
        values = result.get('values', [])
        if len(values) > 1:  # ヘッダー行以外にデータがある場合
            updated_count = 0
            for i in range(1, len(values)):
                row_number = i + 1
                if check_and_format_sold_item(sheet, sheet_name, row_number):
                    updated_count += 1
            
            if updated_count > 0:
                print(f"シート '{sheet_name}' で {updated_count} 件の売れた商品に色を設定しました")
            else:
                print(f"シート '{sheet_name}' の売れた商品の色設定は完了済みです")
    except Exception as e:
        print(f"トリガー設定エラー: {e}")

def refresh_sold_items_formatting(sheet, sheet_name: str):
    """シート全体の売れた商品の色を更新（手動実行用）"""
    try:
        # シート全体のデータを取得
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A:F'
        ).execute()
        
        values = result.get('values', [])
        updated_count = 0
        
        if len(values) > 1:  # ヘッダー行以外にデータがある場合
            for i in range(1, len(values)):
                row_number = i + 1
                if check_and_format_sold_item(sheet, sheet_name, row_number):
                    updated_count += 1
        
        print(f"シート '{sheet_name}' で {updated_count} 件の売れた商品の色を更新しました")
        return updated_count
    except Exception as e:
        print(f"売れた商品の色更新エラー: {e}")
        return 0

def setup_profit_formula(sheet, sheet_name: str, row_number: int):
    """利益の自動計算式を設定"""
    try:
        # 利益 = 販売価格 - 500 - (販売価格 * 0.1)
        # つまり: 販売価格 * 0.9 - 500
        # 販売価格が入力されている場合のみ計算し、空の場合は空文字を表示
        formula = f'=IF(AND(E{row_number}<>"",ISNUMBER(E{row_number})),E{row_number}*0.9-500,"")'
        
        body = {'values': [[formula]]}
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!F{row_number}',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        print(f"行 {row_number} の利益計算式を設定しました")
    except Exception as e:
        print(f"利益計算式設定エラー: {e}")

def setup_sold_item_formatting(sheet, sheet_name: str, row_number: int):
    """商品が売れた場合のセル色を変更（B列からF列まで）"""
    try:
        sheet_id = get_sheet_id(sheet, sheet_name)
        if sheet_id == 0:
            print("シートIDが取得できませんでした")
            return
            
        # 薄い緑色で背景を設定（文字が見やすい色）
        requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': row_number - 1,  # 0ベース
                        'endRowIndex': row_number,
                        'startColumnIndex': 1,  # B列（0ベース）
                        'endColumnIndex': 6     # F列まで（0ベース）
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 1.0,
                                'blue': 0.9
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor'
                }
            }
        ]
        
        body = {'requests': requests}
        sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        
        print(f"行 {row_number} の商品が売れたことを示す色を設定しました")
    except Exception as e:
        print(f"売却商品の色設定エラー: {e}")

def check_and_format_sold_item(sheet, sheet_name: str, row_number: int):
    """商品の項目がすべて入力されているかチェックし、売れた場合は色を変更"""
    try:
        # 指定行のデータを取得
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!B{row_number}:F{row_number}'
        ).execute()
        
        values = result.get('values', [[]])
        if values and len(values[0]) >= 5:
            # B列（商品名）、C列（登録日）、D列（販売日）、E列（販売価格）、F列（利益）がすべて入力されているかチェック
            product_name = values[0][0] if len(values[0]) > 0 else ""
            registration_date = values[0][1] if len(values[0]) > 1 else ""
            sale_date = values[0][2] if len(values[0]) > 2 else ""
            sale_price = values[0][3] if len(values[0]) > 3 else ""
            profit = values[0][4] if len(values[0]) > 4 else ""
            
            # すべての項目が入力されている場合のみ色をつける
            if product_name and registration_date and sale_date and sale_price and profit:
                setup_sold_item_formatting(sheet, sheet_name, row_number)
                return True
        
        return False
    except Exception as e:
        print(f"売却商品チェックエラー: {e}")
        return False

def get_sheet_id(sheet, sheet_name: str) -> int:
    """シート名からシートIDを取得"""
    try:
        spreadsheet = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
        for worksheet in spreadsheet['sheets']:
            if worksheet['properties']['title'] == sheet_name:
                return worksheet['properties']['sheetId']
        return 0
    except Exception as e:
        print(f"シートID取得エラー: {e}")
        return 0

def append_row_to_sheet(sheet, image_paths: List[str], product_info: Dict[str, str], management_number: str) -> bool:
    """
    スプレッドシートに1行を追加（新しい列構成）
    """
    try:
        # 管理番号の先頭4桁をシート名として取得/作成
        sheet_name = get_or_create_sheet(sheet, management_number)
        
        # 登録日を取得（販売日と同じ形式で統一）
        registration_date = datetime.now().strftime('%Y/%m/%d')
        
        # 1枚目の画像をSupabase Storageにアップロード
        image_url = ""
        if image_paths:
            try:
                filename = f"product_{management_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                image_url = upload_image_to_drive(image_paths[0], filename)
            except Exception as img_error:
                print(f"画像アップロードエラー: {img_error}")
                print("画像アップロードに失敗しましたが、商品データの保存は継続します")
        
        # 新しい列構成でデータを準備（画像列は空にする）
        row_data = [
            '',  # A列：画像（後で挿入）
            product_info.get('title', ''),  # B列：商品名
            registration_date,  # C列：登録日
            '',  # D列：販売日（手動入力）
            '',  # E列：販売価格（手動入力）
            ''   # F列：利益（自動計算）
        ]

        # データを追加
        body = {'values': [row_data]}
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A:F',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        # 追加された行番号を取得して利益計算式を設定
        updated_range = result.get('updates', {}).get('updatedRange', '')
        row_number = 2  # デフォルト値
        if updated_range:
            # 範囲から行番号を抽出（例：'0627!A2:F2' から 2 を取得）
            row_match = updated_range.split('!')[1].split(':')[0]
            if row_match and row_match[0].isalpha():
                row_number = int(''.join(filter(str.isdigit, row_match)))
        
        # 利益の自動計算式を設定（エラーが発生しても継続）
        try:
            setup_profit_formula(sheet, sheet_name, row_number)
        except Exception as formula_error:
            print(f"利益計算式設定エラー: {formula_error}")
            print("利益計算式の設定に失敗しましたが、商品データの保存は完了しました")
        
        # 画像を挿入（エラーが発生しても継続）
        if image_url:
            try:
                insert_image_to_sheet(sheet, sheet_name, row_number, image_url)
            except Exception as insert_error:
                print(f"画像挿入エラー: {insert_error}")
                print("画像挿入に失敗しましたが、商品データの保存は完了しました")

        # 新しく追加された商品が売れた商品かチェック（エラーが発生しても継続）
        try:
            check_and_format_sold_item(sheet, sheet_name, row_number)
        except Exception as check_error:
            print(f"売却商品チェックエラー: {check_error}")

        print(f"データをシート '{sheet_name}' に保存しました")
        return True
    except Exception as e:
        print(f"データ追加エラー: {e}")
        print("商品データの保存に失敗しました")
        return False

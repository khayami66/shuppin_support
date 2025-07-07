import os
import json
import base64
from typing import Optional, List
import openai
from dotenv import load_dotenv

class ChatGPTHandler:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        openai.api_key = api_key

    def _encode_image_to_base64(self, image_path: str) -> str:
        """画像をbase64エンコードする"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"画像エンコードエラー ({image_path}): {str(e)}")
            return ""

    def _determine_product_type(self, image_paths: List[str]) -> str:
        """画像から商品の種類（トップスかパンツかスカートか）を判定する"""
        try:
            # 画像をbase64エンコード
            encoded_images = []
            for image_path in image_paths:
                encoded_image = self._encode_image_to_base64(image_path)
                if encoded_image:
                    encoded_images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    })

            if not encoded_images:
                return "tops"  # デフォルトはトップス

            prompt = """
この画像は古着の商品です。以下の3つのカテゴリーのうち、どれに該当するか判定してください：

1. tops（トップス）: Tシャツ、シャツ、ジャケット、セーター、カーディガンなど、上半身に着る服
2. pants（パンツ）: ジーンズ、スラックス、ショートパンツ、トレーナーなど、下半身に着る服
3. skirt（スカート）: ミニスカート、ロングスカート、プリーツスカート、タイトスカートなど、女性用の下半身に着る服

画像を詳しく分析して、最も適切なカテゴリーを選択してください。
必ず「tops」「pants」「skirt」のいずれかで回答してください。
"""

            messages = [
                {
                    "role": "system", 
                    "content": "あなたは古着の商品分類の専門AIです。画像から商品の種類を正確に判定してください。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ] + encoded_images
                }
            ]

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=50,
                temperature=0.1
            )

            content = response.choices[0].message.content.strip().lower()
            
            if "skirt" in content or "スカート" in content:
                return "skirt"
            elif "pants" in content or "パンツ" in content or "ジーンズ" in content or "スラックス" in content:
                return "pants"
            else:
                return "tops"

        except Exception as e:
            print(f"商品種類判定エラー: {e}")
            return "tops"  # エラーの場合はデフォルトでトップス

    def _generate_template(self, result: dict, product_type: str) -> str:
        """商品種類に応じてテンプレートを生成する"""
        if product_type == "skirt":
            # スカート用テンプレート
            template = f"""【商品について】
{result.get('description', '商品の説明が生成されませんでした')}

【実寸】
ウエスト：cm
総丈：cm
※採寸は素人寸法なので、ご理解の程よろしくお願い致します（2〜4センチ誤差がある場合があります）。

【状態について】
特に目立った傷や汚れのないお品物です。古着故、多少の使用感はございますが、普段古着を着られる方でしたら、気にならずお使い頂ける一枚かと思います。
※商品名に書いている年代とは違う場合もあります、ご理解の上ご購入ください。
※多少の汚れ・破れがあっても、目立っていなければ、目立った傷汚れなしとして、販売します。目立った傷汚れ等なしと選択していても、古着ですので価値観によっては「傷・汚れ」と思われてしまう場合がございます。
気になるところがある際は、具体的にコメントをお願いいたします。
また、写真写りやシワ等も写真の撮り方で実物と少々違う場合がありますので、ご了承ください。

★上記、ご理解の上でご購入よろしくお願いいたします★

{result.get('hashtags', '')}

#古着屋883　←他の商品もご覧くださいね‼️

最後までお読みいただきありがとうございました！
気持ちの良いお取引をどうぞよろしくお願い致します。"""
        elif product_type == "pants":
            # パンツ用テンプレート
            template = f"""【商品について】
{result.get('description', '商品の説明が生成されませんでした')}

【実寸】
ウエスト：cm
股下：cm
裾幅：cm
股上：cm
※採寸は素人寸法なので、ご理解の程よろしくお願い致します（2〜4センチ誤差がある場合があります）。

【状態について】
特に目立った傷や汚れのないお品物です。古着故、多少の使用感はございますが、普段古着を着られる方でしたら、気にならずお使い頂ける一枚かと思います。
※商品名に書いている年代とは違う場合もあります、ご理解の上ご購入ください。
※多少の汚れ・破れがあっても、目立っていなければ、目立った傷汚れなしとして、販売します。目立った傷汚れ等なしと選択していても、古着ですので価値観によっては「傷・汚れ」と思われてしまう場合がございます。
気になるところがある際は、具体的にコメントをお願いいたします。
また、写真写りやシワ等も写真の撮り方で実物と少々違う場合がありますので、ご了承ください。

★上記、ご理解の上でご購入よろしくお願いいたします★

{result.get('hashtags', '')}

#古着屋883　←他の商品もご覧くださいね‼️

最後までお読みいただきありがとうございました！
気持ちの良いお取引をどうぞよろしくお願い致します。"""
        else:
            # トップス用テンプレート
            template = f"""【商品について】
{result.get('description', '商品の説明が生成されませんでした')}

【実寸】
着丈：cm
身幅：cm
肩幅：cm
袖丈：cm
※採寸は素人寸法なので、ご理解の程よろしくお願い致します（2〜4センチ誤差がある場合があります）。

【状態について】
特に目立った傷や汚れのないお品物です。古着故、多少の使用感はございますが、普段古着を着られる方でしたら、気にならずお使い頂ける一枚かと思います。
※商品名に書いている年代とは違う場合もあります、ご理解の上ご購入ください。
※多少の汚れ・破れがあっても、目立っていなければ、目立った傷汚れなしとして、販売します。目立った傷汚れ等なしと選択していても、古着ですので価値観によっては「傷・汚れ」と思われてしまう場合がございます。
気になるところがある際は、具体的にコメントをお願いいたします。
また、写真写りやシワ等も写真の撮り方で実物と少々違う場合がありますので、ご了承ください。

★上記、ご理解の上でご購入よろしくお願いいたします★

{result.get('hashtags', '')}

#古着屋883　←他の商品もご覧くださいね‼️

最後までお読みいただきありがとうございました！
気持ちの良いお取引をどうぞよろしくお願い致します。"""
        
        return template

    def generate_product_info(self, image_paths: List[str], user_features_text: str) -> Optional[dict]:
        try:
            if not image_paths or not user_features_text:
                raise ValueError("画像とユーザー特徴の両方が必要です。")

            # 商品種類を判定
            product_type = self._determine_product_type(image_paths)

            # 画像をbase64エンコード
            encoded_images = []
            for image_path in image_paths:
                encoded_image = self._encode_image_to_base64(image_path)
                if encoded_image:
                    encoded_images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    })

            if not encoded_images:
                raise ValueError("画像のエンコードに失敗しました。")

            prompt = f"""
あなたは古着販売の専門AIです。

このシステムでは、単品出品のみを対象としています。
「まとめ売り」や「上下セット」などの複数アイテム販売はこのシステムでは一切行いません。
ユーザーが「#まとめ売り」や「#セット」と入力することもありません。
そのような販売は、他の仕組みで処理します。

以下のルールを必ず厳守してください：

【画像とテキストの特徴】
- 入力された画像とテキストに含まれない要素（色、構成アイテム、素材、使用状態など）を想像で補完しない。
- 画像に映っていない「Tシャツ」「ジャケット」「パンツ」などを勝手に加えない。
- 色（例：レッド、ベージュ、ネイビー）や状態（新品、美品など）を画像で確認できない場合は一切記載しない。
- レーヨンなど素材情報は、タグ画像で明確に読み取れる場合のみ出力。

【重要：商品名の形式】
商品名は必ず以下の形式で作成してください：
「ブランド　アイテム名　色　生地　柄　サイズ　見た目」

・色は「レッド」「グリーン」「ネイビー」「ブラック」「ホワイト」のようにカタカナ表記
・生地が複数ある場合は、その中から1つ表示（できるだけ高価な生地を選択）
・サイズは「L」「XL」「34」「36」のようにシンプルに表記
・見た目は商品の特徴に応じて適切なワードを選択してください

【重要：見た目の表現バリエーション】
商品の見た目を表現する際は、以下のカテゴリーから商品の特徴に最も適したワードを選択してください：

【スタイル・ジャンル】
・ストリート：ストリートファッション、ヒップホップ風
・アメカジ：アメリカンカジュアル、リラックス感
・ミリタリー：軍服風、カモフラージュ柄
・Y2K：2000年代風、ミレニアル感
・カジュアル：普段着感、リラックス感
・フォーマル：ビジネス風、上品感
・スポーツ：アスリート風、動きやすさ

【デザイン・柄】
・和柄：日本の伝統的な柄、着物風
・総柄：全体に柄が入っている
・チェック柄：格子模様
・ストライプ：縞模様
・無地：シンプル、柄なし
・グラフィック：イラストやロゴ入り
・パッチワーク：複数の布を組み合わせ

【地域・文化】
・イタリア風：イタリアンファッション、エレガント
・フレンチ：フランス風、洗練された
・レトロ：古い時代のデザイン（本当にレトロな場合のみ）
・ヴィンテージ：古い時代の雰囲気（本当にヴィンテージな場合のみ）
・モダン：現代的、シンプル
・クラシック：伝統的、上品

【素材・質感】
・デニム風：デニムのような質感
・レザー風：革のような質感
・シルク風：絹のような質感
・コットン風：綿のような自然な質感

【重要：見た目の選択基準】
1. 商品の実際の特徴をよく観察してください
2. 「レトロ感」や「ヴィンテージ」は本当に古い時代のデザインの場合のみ使用
3. 現代的な商品には「モダン」「カジュアル」「ストリート」などを使用
4. 柄やデザインの特徴に応じて「和柄」「総柄」「チェック柄」などを使用
5. 地域性がある場合は「イタリア風」「フレンチ」などを使用

【重要：商品名の文字数制限】
商品名は必ず34文字以内で作成してください。これは絶対的な制限です。
（管理番号6文字が後で追加されるため、34文字以内で作成してください）
文字数を超える場合は、以下の優先順位に従って要素を省略してください：
1. アイテム名（必須）
2. ブランド（分かる場合のみ）
3. 色（必須）
4. サイズ（分かる場合のみ）
5. 柄（可能な限り含める）
6. 素材（可能な限り含める）
7. 見た目（余裕があれば含める）

【重要：ブランド・サイズが不明な場合】
ブランド名やサイズが画像から明確に分からない場合は、それらを除いて商品名を作成してください。

例：
- ブランド・サイズが分かる場合：「NIKE　半袖Tシャツ　グリーン　綿　迷彩柄　L　ストリート」
- ブランド・サイズが分からない場合：「半袖Tシャツ　グリーン　綿100　迷彩柄　ミリタリー」

文字数が厳しい場合は、優先順位の低い要素から順に省略してください。
必ず34文字以内に収めてください。

商品名例（34文字以内）：
「NIKE　半袖Tシャツ　グリーン　綿　迷彩柄　L　ストリート」
「半袖Tシャツ　グリーン　綿100　迷彩柄　ミリタリー」

【重要：出力形式】
必ず以下のJSON形式のみで出力してください。説明文や注釈は一切含めないでください。

{{
  "title": "商品名（34文字以内、上記の形式で作成）",
  "description": "商品の特徴が伝わる自然な日本語（敬体）で1〜2文にまとめてください。",
  "hashtags": "#タグ1 #タグ2 #タグ3 #タグ4 #タグ5 #タグ6 #タグ7 #タグ8 #タグ9 #タグ10",
  "start_price": 数値のみ（円マークなし、以下の価格帯から最も適正な価格を選択：1980, 2980, 3980, 4980, 5980, 6980, 7980, 8980, 9980...）
}}

【その他の制約】
- ハッシュタグは必ず10個、#を含み、スペース区切りで出力してください。
- タイトルは34文字以内、誇張表現（レア、超人気、美品など）は使用禁止。
- descriptionは敬体で、煽りなし・魅力的かつ正確に。
- 出力は必ず **有効なJSON形式** のみ。JSON以外の文言や注釈は禁止。
- すべての商品は**単品出品**であると仮定してください。複数商品を含めるような説明は禁止。

【入力情報】
ユーザーが入力した特徴: {user_features_text}

以上の条件を守り、画像と特徴に忠実な、魅力的な単品商品情報を生成してください。
必ずJSON形式のみで出力してください。
"""

            messages = [
                {
                    "role": "system", 
                    "content": "あなたは古着販売の専門AIです。単品出品のみを対象とし、画像とテキストの特徴のみに基づいて、推測や補完を一切行わず、正確な商品情報を生成してください。必ず敬体の日本語で、魅力的かつ正確な説明を作成してください。商品名は必ず34文字以内で作成してください。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ] + encoded_images
                }
            ]

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000,
                temperature=0.2
            )

            content = response.choices[0].message.content
            
            # 応答からJSON部分を抽出
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # JSONの解析を試行
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON解析エラー: {e}")
                print(f"応答内容: {content}")
                # 応答がJSONでない場合、再試行を促す
                raise ValueError("ChatGPTの応答が正しいJSON形式ではありませんでした。再試行してください。")

            if not isinstance(result.get("start_price"), (int, float)):
                raise ValueError("start_price must be a number")
            
            # 商品名の文字数チェックと自動短縮
            title = result.get("title", "")
            if len(title) > 34:
                print(f"タイトル文字数オーバー: '{title}' ({len(title)}文字)")
                # 自動短縮処理
                shortened_title = self._shorten_title(title)
                if len(shortened_title) <= 34:
                    print(f"自動短縮: '{shortened_title}' ({len(shortened_title)}文字)")
                    result['title'] = shortened_title
                else:
                    print(f"短縮後も文字数オーバー: '{shortened_title}' ({len(shortened_title)}文字) - 手動調整が必要")
                    # エラーを発生させずに、短縮版を使用（手動調整のため）
                    result['title'] = shortened_title
            
            if result.get("hashtags", "").count("#") != 10:
                raise ValueError("Exactly 10 hashtags required")

            # 商品種類に応じたテンプレートを生成
            template = self._generate_template(result, product_type)
            result['template'] = template

            return result

        except Exception as e:
            print(f"[ChatGPT Error] {e}")
            return None

    def generate_product_info_from_images_only(self, image_paths: List[str]) -> Optional[dict]:
        """画像のみから商品情報を生成する"""
        try:
            if not image_paths:
                raise ValueError("画像が必要です。")

            # 商品種類を判定
            product_type = self._determine_product_type(image_paths)

            # 画像をbase64エンコード
            encoded_images = []
            for image_path in image_paths:
                encoded_image = self._encode_image_to_base64(image_path)
                if encoded_image:
                    encoded_images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    })

            if not encoded_images:
                raise ValueError("画像のエンコードに失敗しました。")

            prompt = f"""
あなたは古着販売の専門AIです。

このシステムでは、単品出品のみを対象としています。
「まとめ売り」や「上下セット」などの複数アイテム販売はこのシステムでは一切行いません。
そのような販売は、他の仕組みで処理します。

以下のルールを必ず厳守してください：

【画像のみからの分析】
- 入力された画像に含まれない要素（色、構成アイテム、素材、使用状態など）を想像で補完しない。
- 画像に映っていない「Tシャツ」「ジャケット」「パンツ」などを勝手に加えない。
- 色（例：レッド、ベージュ、ネイビー）や状態（新品、美品など）を画像で確認できない場合は一切記載しない。
- レーヨンなど素材情報は、タグ画像で明確に読み取れる場合のみ出力。
- 画像から確認できる商品の特徴のみを基に商品情報を生成してください。

【重要：商品名の形式】
商品名は必ず以下の形式で作成してください：
「ブランド　アイテム名　色　生地　柄　サイズ　見た目」

・色は「レッド」「グリーン」「ネイビー」「ブラック」「ホワイト」のようにカタカナ表記
・生地が複数ある場合は、その中から1つ表示（できるだけ高価な生地を選択）
・サイズは「L」「XL」「34」「36」のようにシンプルに表記
・見た目は商品の特徴に応じて適切なワードを選択してください

【重要：見た目の表現バリエーション】
商品の見た目を表現する際は、以下のカテゴリーから商品の特徴に最も適したワードを選択してください：

【スタイル・ジャンル】
・ストリート：ストリートファッション、ヒップホップ風
・アメカジ：アメリカンカジュアル、リラックス感
・ミリタリー：軍服風、カモフラージュ柄
・Y2K：2000年代風、ミレニアル感
・カジュアル：普段着感、リラックス感
・フォーマル：ビジネス風、上品感
・スポーツ：アスリート風、動きやすさ

【デザイン・柄】
・和柄：日本の伝統的な柄、着物風
・総柄：全体に柄が入っている
・チェック柄：格子模様
・ストライプ：縞模様
・無地：シンプル、柄なし
・グラフィック：イラストやロゴ入り
・パッチワーク：複数の布を組み合わせ

【地域・文化】
・イタリア風：イタリアンファッション、エレガント
・フレンチ：フランス風、洗練された
・レトロ：古い時代のデザイン（本当にレトロな場合のみ）
・ヴィンテージ：古い時代の雰囲気（本当にヴィンテージな場合のみ）
・モダン：現代的、シンプル
・クラシック：伝統的、上品

【素材・質感】
・デニム風：デニムのような質感
・レザー風：革のような質感
・シルク風：絹のような質感
・コットン風：綿のような自然な質感

【重要：見た目の選択基準】
1. 商品の実際の特徴をよく観察してください
2. 「レトロ感」や「ヴィンテージ」は本当に古い時代のデザインの場合のみ使用
3. 現代的な商品には「モダン」「カジュアル」「ストリート」などを使用
4. 柄やデザインの特徴に応じて「和柄」「総柄」「チェック柄」などを使用
5. 地域性がある場合は「イタリア風」「フレンチ」などを使用

【重要：商品名の文字数制限】
商品名は必ず34文字以内で作成してください。これは絶対的な制限です。
文字数を超える場合は、以下の優先順位に従って要素を省略してください：
1. アイテム名（必須）
2. ブランド（分かる場合のみ）
3. 色（必須）
4. サイズ（分かる場合のみ）
5. 柄（可能な限り含める）
6. 素材（可能な限り含める）
7. 見た目（余裕があれば含める）

【重要：ブランド・サイズが不明な場合】
ブランド名やサイズが画像から明確に分からない場合は、それらを除いて商品名を作成してください。

例：
- ブランド・サイズが分かる場合：「NIKE　半袖Tシャツ　グリーン　綿　迷彩柄　L　ストリート」
- ブランド・サイズが分からない場合：「半袖Tシャツ　グリーン　綿100　迷彩柄　ミリタリー」

文字数が厳しい場合は、優先順位の低い要素から順に省略してください。
必ず34文字以内に収めてください。

商品名例（34文字以内）：
「NIKE　半袖Tシャツ　グリーン　綿　迷彩柄　L　ストリート」
「半袖Tシャツ　グリーン　綿100　迷彩柄　ミリタリー」

【重要：出力形式】
必ず以下のJSON形式のみで出力してください。説明文や注釈は一切含めないでください。

{{
  "title": "商品名（34文字以内、上記の形式で作成）",
  "description": "商品の特徴が伝わる自然な日本語（敬体）で1〜2文にまとめてください。",
  "hashtags": "#タグ1 #タグ2 #タグ3 #タグ4 #タグ5 #タグ6 #タグ7 #タグ8 #タグ9 #タグ10",
  "start_price": 数値のみ（円マークなし、以下の価格帯から最も適正な価格を選択：1980, 2980, 3980, 4980, 5980, 6980, 7980, 8980, 9980...）
}}

【その他の制約】
- ハッシュタグは必ず10個、#を含み、スペース区切りで出力してください。
- タイトルは34文字以内、誇張表現（レア、超人気、美品など）は使用禁止。
- descriptionは敬体で、煽りなし・魅力的かつ正確に。
- 出力は必ず **有効なJSON形式** のみ。JSON以外の文言や注釈は禁止。
- すべての商品は**単品出品**であると仮定してください。複数商品を含めるような説明は禁止。

以上の条件を守り、画像のみに忠実な、魅力的な単品商品情報を生成してください。
必ずJSON形式のみで出力してください。
"""

            messages = [
                {
                    "role": "system", 
                    "content": "あなたは古着販売の専門AIです。単品出品のみを対象とし、画像のみに基づいて、推測や補完を一切行わず、正確な商品情報を生成してください。必ず敬体の日本語で、魅力的かつ正確な説明を作成してください。商品名は必ず34文字以内で作成してください。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ] + encoded_images
                }
            ]

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000,
                temperature=0.2
            )

            content = response.choices[0].message.content
            
            # 応答からJSON部分を抽出
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # JSONの解析を試行
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON解析エラー: {e}")
                print(f"応答内容: {content}")
                # 応答がJSONでない場合、再試行を促す
                raise ValueError("ChatGPTの応答が正しいJSON形式ではありませんでした。再試行してください。")

            if not isinstance(result.get("start_price"), (int, float)):
                raise ValueError("start_price must be a number")
            
            # 商品名の文字数チェックと自動短縮
            title = result.get("title", "")
            if len(title) > 34:
                print(f"タイトル文字数オーバー: '{title}' ({len(title)}文字)")
                # 自動短縮処理
                shortened_title = self._shorten_title(title)
                if len(shortened_title) <= 34:
                    print(f"自動短縮: '{shortened_title}' ({len(shortened_title)}文字)")
                    result['title'] = shortened_title
                else:
                    print(f"短縮後も文字数オーバー: '{shortened_title}' ({len(shortened_title)}文字) - 手動調整が必要")
                    # エラーを発生させずに、短縮版を使用（手動調整のため）
                    result['title'] = shortened_title
            
            if result.get("hashtags", "").count("#") != 10:
                raise ValueError("Exactly 10 hashtags required")

            # 商品種類に応じたテンプレートを生成
            template = self._generate_template(result, product_type)
            result['template'] = template

            return result

        except Exception as e:
            print(f"[ChatGPT Error] {e}")
            return None

    def _shorten_title(self, title: str) -> str:
        """商品名を34文字以内に自動短縮する"""
        if len(title) <= 34:
            return title
        
        # 商品名を要素に分解
        elements = title.split('　')
        
        # 優先順位に従って削除する要素を決定
        # 1. アイテム名（必須）- 削除しない
        # 2. ブランド（分かる場合のみ）- 削除可能
        # 3. 色（必須）- 削除しない
        # 4. サイズ（分かる場合のみ）- 削除可能
        # 5. 柄（可能な限り含める）- 削除可能
        # 6. 素材（可能な限り含める）- 削除可能
        # 7. 見た目（余裕があれば含める）- 削除可能
        
        # 削除候補の要素を特定
        removable_elements = []
        
        for i, element in enumerate(elements):
            # サイズの判定（L, XL, M, S, 数字など）
            if element in ['L', 'XL', 'M', 'S', 'LL', 'XS', 'XXL'] or element.isdigit():
                removable_elements.append((i, element, 'size'))
            # 見た目の判定（多様な表現に対応）
            elif (element.endswith('感') or element.endswith('風') or 'スタイル' in element or
                  element in ['ストリート', 'アメカジ', 'ミリタリー', 'Y2K', 'カジュアル', 'フォーマル', 'スポーツ',
                             '和柄', '総柄', 'チェック柄', 'ストライプ', '無地', 'グラフィック', 'パッチワーク',
                             'イタリア風', 'フレンチ', 'レトロ', 'ヴィンテージ', 'モダン', 'クラシック',
                             'デニム風', 'レザー風', 'シルク風', 'コットン風']):
                removable_elements.append((i, element, 'style'))
            # 柄の判定（ストライプ、チェック、無地など）
            elif element in ['ストライプ', 'チェック', '無地', '迷彩柄', 'ドット']:
                removable_elements.append((i, element, 'pattern'))
            # 素材の判定（綿、デニム、レーヨンなど）
            elif element in ['綿', 'デニム', 'レーヨン', 'ポリエステル', 'ウール']:
                removable_elements.append((i, element, 'material'))
        
        # 優先順位の低い要素から削除
        removable_elements.sort(key=lambda x: {
            'style': 1,      # 見た目（最優先で削除）
            'pattern': 2,    # 柄
            'material': 3,   # 素材
            'size': 4        # サイズ（最後に削除）
        }[x[2]])
        
        # 要素を削除して34文字以内に収める
        elements_to_remove = []
        for index, element, element_type in removable_elements:
            elements_to_remove.append(index)
        
        # インデックスを逆順で削除
        for index in sorted(elements_to_remove, reverse=True):
            del elements[index]
            
            # 削除後の文字数をチェック
            shortened = '　'.join(elements)
            if len(shortened) <= 34:
                return shortened
        
        # それでも34文字を超える場合は、ブランド名を削除
        if len(elements) > 1:
            # 最初の要素（ブランド名）を削除
            elements = elements[1:]
            shortened = '　'.join(elements)
            if len(shortened) <= 34:
                return shortened
        
        # さらに削除が必要な場合、見た目要素を削除
        for i, element in enumerate(elements):
            if (element.endswith('感') or element.endswith('風') or 'スタイル' in element or
                element in ['ストリート', 'アメカジ', 'ミリタリー', 'Y2K', 'カジュアル', 'フォーマル', 'スポーツ',
                           '和柄', '総柄', 'チェック柄', 'ストライプ', '無地', 'グラフィック', 'パッチワーク',
                           'イタリア風', 'フレンチ', 'レトロ', 'ヴィンテージ', 'モダン', 'クラシック',
                           'デニム風', 'レザー風', 'シルク風', 'コットン風']):
                del elements[i]
                shortened = '　'.join(elements)
                if len(shortened) <= 34:
                    return shortened
                break
        
        # 最後の手段：アイテム名と色のみ残す
        if len(elements) >= 2:
            return f"{elements[0]}　{elements[1]}"
        else:
            return elements[0] if elements else title[:34]


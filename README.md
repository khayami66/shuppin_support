# 出品サポートGPT4o システム

LINE Botを使用した商品出品支援システムです。画像とテキスト特徴から商品情報を自動生成し、Google Sheetsに保存します。

## 機能

- 📸 画像から商品情報を自動生成
- 📝 テキスト特徴の追加対応
- 📊 Google Sheetsへの自動保存
- 🎨 売れた商品の色自動更新
- 🔢 管理番号による商品名自動修正

## セットアップ

### 必要な環境変数

`.env`ファイルを作成し、以下の環境変数を設定してください：

```env
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
OPENAI_API_KEY=your_openai_api_key
GOOGLE_SHEETS_CREDENTIALS=your_google_service_account_json
```

### ローカル開発

1. 依存関係のインストール：
```bash
pip install -r requirements.txt
```

2. アプリケーションの起動：
```bash
python main.py
```

## Vercelデプロイ

### 1. GitHubにプッシュ

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/shuppin_support.git
git push -u origin main
```

### 2. Vercelでデプロイ

1. [Vercel](https://vercel.com)にアクセス
2. GitHubリポジトリをインポート
3. 環境変数を設定：
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `OPENAI_API_KEY`
   - `GOOGLE_SHEETS_CREDENTIALS` (service_account.jsonの内容)

### 3. LINE Bot設定

1. LINE DevelopersコンソールでWebhook URLを設定：
   ```
   https://your-vercel-app.vercel.app/callback
   ```

## 使用方法

1. **画像のみで商品情報生成**：
   - 商品画像を送信
   - 6桁の管理番号を送信

2. **テキスト特徴付きで商品情報生成**：
   - 商品の特徴をテキストで送信
   - 商品画像を送信
   - 6桁の管理番号を送信

3. **売れた商品の色更新**：
   - `#更新` と送信

## ファイル構成

```
shuppin_support/
├── main.py                 # メインアプリケーション
├── chatgpt_handler.py      # ChatGPT API処理
├── google_sheets_handler.py # Google Sheets処理
├── api/
│   └── index.py           # Vercel用APIルート
├── requirements.txt       # Python依存関係
├── vercel.json           # Vercel設定
├── .gitignore           # Git除外設定
└── README.md            # このファイル
```

## 注意事項

- `service_account.json`は機密情報のため、Gitにコミットしないでください
- Vercelでは環境変数として設定してください
- LINE BotのWebhook URLはHTTPSである必要があります

## トラブルシューティング

### よくある問題

1. **環境変数が設定されていない**：
   - すべての必要な環境変数が設定されているか確認

2. **Google Sheetsアクセスエラー**：
   - サービスアカウントの権限設定を確認
   - スプレッドシートの共有設定を確認

3. **LINE Bot応答なし**：
   - Webhook URLが正しく設定されているか確認
   - Vercelのデプロイが成功しているか確認 
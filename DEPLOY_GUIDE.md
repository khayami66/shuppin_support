# Vercel × Supabase × LINE Bot デプロイ手順（初心者向け）

---

## 1. 概要

このドキュメントは、LINE BotをVercelとSupabaseを使ってデプロイし、Googleスプレッドシートに商品情報と画像を自動登録するシステムの構築手順を初心者向けにまとめたものです。

---

## 2. 必要なサービスとアカウント

- [Supabase](https://supabase.com/)（無料でOK）
- [Vercel](https://vercel.com/)（無料でOK）
- [GitHub](https://github.com/)（Vercelと連携用）
- [LINE Developers](https://developers.line.biz/ja/)（Bot用）
- Googleアカウント（Google Sheets用）

---

## 3. 作業手順

### 【A】Supabaseの準備

1. [Supabase公式サイト](https://supabase.com/)でアカウント作成
2. 新しいプロジェクトを作成
3. 「Storage」タブでバケット（例：images）を作成（**パブリック設定**にすること）
4. 「Project Settings」→「API」から`anon`キーとプロジェクトURLを控える

---

### 【B】Vercelの準備

1. [Vercel公式サイト](https://vercel.com/)でアカウント作成
2. GitHubアカウントと連携
3. このプロジェクト（shuppin_support）をGitHubにpush（まだなら）
4. Vercelで「New Project」→GitHubリポジトリを選択

---

### 【C】コードの修正（Supabase対応）

1. `requirements.txt`に`supabase-py`を追加
2. 画像アップロード部分をSupabase Storageに変更
3. 画像URLをGoogle Sheetsに記録するよう修正
4. 必要ならセッション管理もSupabaseに（最初は画像だけでもOK）

---

### 【D】環境変数の設定

1. Vercelの「Settings」→「Environment Variables」で以下を登録
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `OPENAI_API_KEY`
   - `GOOGLE_SHEETS_CREDENTIALS`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

---

### 【E】Vercelにデプロイ

1. GitHubにpush（mainブランチ推奨）
2. Vercelが自動でビルド・デプロイ
3. デプロイURL（例：https://your-app.vercel.app）を控える

---

### 【F】LINE Developers設定

1. LINE DevelopersコンソールでWebhook URLをVercelのURL＋`/api/index.py/callback`に設定
2. 「接続確認」で200 OKになるかテスト

---

### 【G】動作確認

1. LINEで画像→管理番号を送信し、スプレッドシートに画像が反映されるか確認
2. 問題があればエラーログを確認し、修正

---

## 4. 補足・勉強ポイント

- **Vercel**は「GitHubにpush→自動デプロイ」なので、基本はGitHubのmainブランチにコードを上げるだけでOKです。
- **Supabase Storage**は「画像のクラウド保存場所」として使います。Google Driveの代わりです。
- **環境変数**は「パスワードやAPIキー」などの秘密情報を安全に管理するためのものです。
- **Google SheetsのA列**には`=IMAGE("Supabaseの画像URL")`で画像を表示します。

---

## 5. よくある質問

- 分からないことがあれば、公式ドキュメントや「Supabase 使い方」「Vercel デプロイ」などで検索してみましょう。
- 何かエラーが出た場合は、エラーメッセージをよく読んで、どこで失敗しているかを確認しましょう。

---

## 6. 参考リンク

- [Supabase公式ドキュメント](https://supabase.com/docs)
- [Vercel公式ドキュメント](https://vercel.com/docs)
- [LINE Messaging API公式ドキュメント](https://developers.line.biz/ja/docs/messaging-api/overview/)
- [Google Sheets API公式ドキュメント](https://developers.google.com/sheets/api)

---

この手順通りに進めれば、初心者でもVercel×Supabase×LINE Botのデプロイができます！ 

---

## 追加: Supabase StorageのRLS（Row Level Security）ポリシー設定

Supabase Storageバケット（例：images）で画像アップロード時に「403 Unauthorized」や「new row violates row-level security policy」エラーが出る場合は、
**SQLエディタで下記のようにポリシーを追加してください。**

1. Supabaseダッシュボードで「SQLエディタ」を開く
2. 下記SQLを実行（バケット名がimagesの場合）

```sql
DROP POLICY IF EXISTS "Allow anon insert to images" ON storage.objects;

CREATE POLICY "Allow anon insert to images"
  ON storage.objects
  FOR INSERT
  TO anon
  WITH CHECK (bucket_id = 'images');
```

- INSERTにはWITH CHECK句を使う必要があります。
- バケット名が異なる場合は適宜書き換えてください。

--- 
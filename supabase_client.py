import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "images")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image_to_supabase(image_path: str, filename: str) -> str:
    """
    画像ファイルをSupabase Storageにアップロードし、パブリックURLを返す
    """
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        # upsert引数を削除
        supabase.storage.from_(BUCKET_NAME).upload(path=filename, file=data, file_options={"content-type": "image/jpeg"})
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        return public_url
    except Exception as e:
        print(f"Supabase画像アップロードエラー: {e}")
        return "" 
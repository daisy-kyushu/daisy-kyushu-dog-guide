import json
import random
import os
from datetime import datetime
import time

# X (Twitter) API用のライブラリをインポート（tweepyを想定）
try:
    import tweepy
except ImportError:
    print("tweepy is not installed. Please install it using 'pip install tweepy'")
    # モックとして動作させるためのダミークラス
    class tweepy:
        class Client:
            def __init__(self, *args, **kwargs): pass
            def create_tweet(self, text):
                print(f"[MOCK] Tweeted: {text}")
                return type('obj', (object,), {'data': {'id': '12345'}})

# 設定ファイルのパス
SPOTS_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'spots.json')

# X APIの認証情報（環境変数から取得）
# 実際の運用ではGitHub Secretsや環境変数に設定する
BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "your_bearer_token")
API_KEY = os.environ.get("X_API_KEY", "your_api_key")
API_SECRET = os.environ.get("X_API_SECRET", "your_api_secret")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "your_access_token")
ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "your_access_token_secret")

def load_spots():
    """spots.jsonからスポット情報を読み込む"""
    try:
        with open(SPOTS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading spots.json: {e}")
        return []

def generate_tweet_text(spot):
    """スポット情報からツイート本文を生成する"""
    # テンプレートのリスト（アフィリエイト成功者を模倣した、読者の興味を惹くスタイル）
    # ハッシュタグは除外する（ユーザー要求）
    templates = [
        "九州で犬連れお出かけするならここは外せない🐾\n\n【{name}】（{area}）\n\n{memo}\n\n大型犬も{large_dog}！\n週末のお出かけ候補に保存推奨です✨\n\n詳細はこちら👇\n{url}",
        "知ってた？{area}にある【{name}】、実は犬連れに最高なんです🐕\n\n{memo}\n\n愛犬との思い出作りにぴったり。\n詳細をブログでまとめました👇\n{url}",
        "🐶九州犬連れスポット紹介🐶\n\n📍{name} ({area})\n\n{memo}\n\n大型犬：{large_dog}\n\n行く前にチェックしておきたいポイントはこちら👇\n{url}"
    ]
    
    template = random.choice(templates)
    
    # データの整形
    name = spot.get('name', 'おすすめスポット')
    area = spot.get('area', '九州')
    memo = spot.get('memo', '') or spot.get('description', '') or spot.get('desc', '素敵な場所です。')
    
    # memoが長すぎる場合は切り詰める
    if len(memo) > 60:
        memo = memo[:57] + "..."
        
    large_dog = spot.get('large_dog', '') or spot.get('largeDog', '要確認')
    if 'OK' in large_dog.upper():
        large_dog = "OK🙆‍♀️"
    elif large_dog == '要確認':
        large_dog = "要確認⚠️"
        
    url = f"https://daisy-kyushu.github.io/daisy-kyushu-dog-guide/spot/{spot.get('id', '')}.html"
    
    text = template.format(
        name=name,
        area=area,
        memo=memo,
        large_dog=large_dog,
        url=url
    )
    
    return text

def post_tweet(text):
    """Xにツイートを投稿する"""
    try:
        # tweepy v2 Clientを使用
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        response = client.create_tweet(text=text)
        print(f"Successfully posted tweet ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return False

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting X auto-post script...")
    
    spots = load_spots()
    if not spots:
        print("No spots found. Exiting.")
        return
        
    # ランダムに1つのスポットを選ぶ
    spot = random.choice(spots)
    
    tweet_text = generate_tweet_text(spot)
    print(f"\nGenerated Tweet:\n{'-'*40}\n{tweet_text}\n{'-'*40}\n")
    
    # 環境変数が設定されている場合のみ実際に投稿を試みる
    if BEARER_TOKEN != "your_bearer_token":
        post_tweet(tweet_text)
    else:
        print("API credentials not set. Running in mock mode.")
        # モック投稿
        post_tweet(tweet_text)
        
    print("Done.")

if __name__ == "__main__":
    main()

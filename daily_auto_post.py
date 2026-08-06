"""
Daisy九州犬連れガイド - Instagram自動投稿スクリプト（実写Daisyベース版）

【コンセプト】
実写Daisyの写真が最強。毎日Daisyの実写写真を使って投稿する。
写真ストックフォルダ（/home/ubuntu/daisy_photos/）に写真を入れておくだけで
毎日自動的にDaisyの実写写真を使った投稿が生成される。

【写真ストックの使い方】
1. /home/ubuntu/daisy_photos/ フォルダに写真を入れる（JPG/PNG/HEIC）
2. ファイル名に場所や状況のメモを入れると自動でキャプションに活用される
   例: daisy_yufuin_onsen.jpg → 由布院温泉でのDaisy
       daisy_dogrun_happy.jpg → ドッグランで楽しむDaisy
3. 一度使った写真は used/ サブフォルダに移動（重複投稿防止）

【曜日別テーマ】
月: 🤖 AI活用術（Daisyの写真 + AIプロンプト紹介）
火: 🐾 犬連れスポット紹介（Daisyが行ったスポット or 九州のおすすめスポット）
水: ✨ Daisyの日常（Daisyの可愛い瞬間）
木: 🗺️ スポット特集（エリア別・テーマ別）
金: 📸 AIプロンプト集（Daisyの写真で試せるAI技）
土: 🌞 週末お出かけ（天気連動スポット提案）
日: 💕 Daisyの週末まとめ

毎朝8:00 JST に自動実行。
"""

import json
import os
import sys
import subprocess
import datetime
import hashlib
import random
import base64
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from openai import OpenAI

# ===== 設定 =====
SITE_URL = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide"
DATA_DIR = Path("/home/ubuntu/daisy-kyushu-dog-guide")
OUTPUT_DIR = Path("/home/ubuntu/daily_post_output")
PHOTO_DIR = Path("/home/ubuntu/daisy_photos")        # 実写写真ストックフォルダ
USED_DIR  = Path("/home/ubuntu/daisy_photos/used")   # 使用済み写真フォルダ
OUTPUT_DIR.mkdir(exist_ok=True)
PHOTO_DIR.mkdir(exist_ok=True)
USED_DIR.mkdir(exist_ok=True)

# 曜日別テーマ (0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日)
THEME_BY_WEEKDAY = {
    0: "ai_tips",       # 月: AI活用術
    1: "spot",          # 火: 犬連れスポット
    2: "daisy_daily",   # 水: Daisyの日常
    3: "spot_theme",    # 木: スポット特集
    4: "ai_prompt",     # 金: AIプロンプト集
    5: "spot_weekend",  # 土: 週末お出かけ
    6: "daisy_weekly",  # 日: Daisyの週末まとめ
}

THEME_LABELS = {
    "ai_tips":      "🤖 AI活用術",
    "spot":         "🐾 犬連れスポット紹介",
    "daisy_daily":  "✨ Daisyの日常",
    "spot_theme":   "🗺️ スポット特集",
    "ai_prompt":    "📸 AIプロンプト集",
    "spot_weekend": "🌞 週末お出かけ",
    "daisy_weekly": "💕 Daisyの週末まとめ",
    "event_urgent": "🚨 イベント直前告知",
}

# AI活用術テーマのローテーション（月曜日ごとに変わる）
AI_TIPS_TOPICS = [
    {
        "title": "ChatGPTで愛犬の写真をスマホから脱出させる方法",
        "hook": "📱 愛犬がスマホを突き破って飛び出す！",
        "step1_ja": "愛犬の写真をChatGPTに添付して「スマホの画面に表示されている画像を作って。縦向きスマホ、秋の背景」と送る",
        "step2_ja": "STEP1の画像を添付して「スマホ画面を突き破って飛び出す画像に変えて。ガラスの破片が飛び散っている」と送る",
        "prompt_ja": "スマホの画面に表示されている犬が、画面を突き破って飛び出す画像に変えて。ガラスの破片が飛び散っている。シネマティック、フォトリアリスティック。",
        "prompt_en": "The dog shown on the smartphone screen bursts through the screen and leaps out. Glass shards fly everywhere. Cinematic, photorealistic.",
        "cta": "うちの子でもやってみて！コメントで見せてね🐾",
    },
    {
        "title": "愛犬を子犬の群れに囲ませる魔法のプロンプト",
        "hook": "🐶 うちの子が子犬に囲まれた！世界でバズ中のAIトレンド",
        "step1_ja": "",
        "step2_ja": "",
        "prompt_ja": "添付の写真の犬の周りに、同じ犬種の子犬を6〜8匹追加して。子犬たちは地面に自然に座ったり立ったりしている。背景・照明・元の犬の見た目は一切変えないで。フォトリアリスティック。",
        "prompt_en": "Place 6–8 puppies of the same breed sitting and standing close around the adult dog in the attached photo. Keep the original dog's appearance, background, and lighting completely unchanged. Photorealistic.",
        "cta": "作れたらコメントで見せてね！保存して後で試してみて🐾",
    },
    {
        "title": "愛犬を王族に変える！ロイヤルポートレートの作り方",
        "hook": "👑 うちの子が貴族になった！印刷してプレゼントにもなるクオリティ",
        "step1_ja": "",
        "step2_ja": "",
        "prompt_ja": "添付の写真の犬を、王冠と深紅のベルベットのマントを着た貴族の犬として、クラシックな油絵風のポートレートに変換して。金色のフレーム装飾、暗い背景、ドラマチックな照明。",
        "prompt_en": "Transform the dog in the attached photo into a noble dog wearing a golden crown and deep crimson velvet cape. Classic oil painting portrait style, ornate gold frame, dark background, dramatic lighting.",
        "cta": "保存して愛犬の誕生日プレゼントにも使えるよ🎂",
    },
    {
        "title": "愛犬が人間だったら？人間化AIアートの作り方",
        "hook": "🧑 うちの子が人間になった！コメントが爆増するバズりネタ",
        "step1_ja": "",
        "step2_ja": "",
        "prompt_ja": "添付の写真の犬が人間だったら？という発想で、犬の毛色と同じ髪色の明るく笑顔の人物のポートレートを作って。犬の特徴（毛色・目の色）を人間の外見に反映させて。背景はソフトなボケ、ゴールデンアワーの光。シネマティックポートレート写真スタイル。",
        "prompt_en": "Imagine the dog in the attached photo as a human. Create a photorealistic portrait of a person with hair color matching the dog's fur, with a bright smile. Reflect the dog's features (fur color, eye color) in the human appearance. Background: soft bokeh, golden hour light. Cinematic portrait style.",
        "cta": "うちの子バージョン作ったらコメントで見せてね！",
    },
]

# AIプロンプト集テーマ（金曜日）
AI_PROMPT_TOPICS = [
    {
        "title": "愛犬をジブリ風アニメキャラにする方法",
        "hook": "🎬 愛犬がジブリの世界に入った！",
        "prompt_ja": "添付の写真の犬を、スタジオジブリ風のアニメーションキャラクターに変換して。温かみのある色彩、手描き風の線、森の中の自然な背景。犬の特徴（体型・毛色）はそのまま維持して。",
        "prompt_en": "Transform the dog in the attached photo into a Studio Ghibli-style animated character. Warm color palette, hand-drawn style lines, natural forest background. Keep the dog's features (body shape, fur color) intact.",
        "cta": "保存して週末に試してみて🐾",
    },
    {
        "title": "愛犬をピクサー映画のキャラにする方法",
        "hook": "🎥 愛犬がピクサー映画に登場！",
        "prompt_ja": "添付の写真の犬を、ピクサー映画スタイルの3Dアニメーションキャラクターに変換して。大きな目、丸みのある体型、鮮やかな色彩、映画のポスター風の構図。",
        "prompt_en": "Transform the dog in the attached photo into a Pixar movie-style 3D animated character. Large expressive eyes, rounded body shape, vibrant colors, movie poster composition.",
        "cta": "うちの子でもやってみて！コメントで見せてね🐾",
    },
    {
        "title": "愛犬を水彩画アートにする方法",
        "hook": "🎨 愛犬が美しい水彩画に！プレゼントにも最高",
        "prompt_ja": "添付の写真の犬を、繊細な水彩画スタイルのアート作品に変換して。淡い色彩、にじみのある筆跡、白い余白を活かした構図。額縁に入れて飾りたくなるような仕上がりで。",
        "prompt_en": "Transform the dog in the attached photo into a delicate watercolor artwork. Soft pastel colors, flowing brushstrokes with bleeding edges, composition with white space. Create a result worthy of framing.",
        "cta": "保存して誕生日プレゼントの参考にしてね🎁",
    },
    {
        "title": "愛犬を宇宙飛行士にする方法",
        "hook": "🚀 愛犬が宇宙へ旅立った！",
        "prompt_ja": "添付の写真の犬を、宇宙飛行士スーツを着た宇宙犬に変換して。宇宙船の窓から地球を見下ろしている構図。リアルな宇宙服の質感、宇宙の星空背景、シネマティックな照明。",
        "prompt_en": "Transform the dog in the attached photo into a space dog wearing an astronaut suit. Composition looking down at Earth from a spacecraft window. Realistic spacesuit texture, starry space background, cinematic lighting.",
        "cta": "うちの子宇宙飛行士バージョン作ったらコメントで！🚀",
    },
]


def load_data():
    with open(DATA_DIR / "spots.json", encoding="utf-8") as f:
        spots = json.load(f)
    try:
        with open(DATA_DIR / "products.json", encoding="utf-8") as f:
            products = json.load(f)
    except FileNotFoundError:
        products = []
    with open(DATA_DIR / "events.json", encoding="utf-8") as f:
        events = json.load(f)
    return spots, products, events


def get_today_seed():
    today = datetime.date.today().isoformat()
    return int(hashlib.md5(today.encode()).hexdigest(), 16) % (2**31)


def get_weather(area="福岡"):
    """Open-Meteo APIで今日の天気を取得（無料・APIキー不要）"""
    coords = {
        "福岡": (33.5904, 130.4017),
        "大分": (33.2382, 131.6126),
        "熊本": (32.7898, 130.7417),
        "長崎": (32.7503, 129.8777),
        "鹿児島": (31.5602, 130.5581),
        "宮崎": (31.9077, 131.4202),
        "佐賀": (33.2635, 130.3009),
    }
    lat, lon = coords.get(area, coords["福岡"])
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=weathercode,precipitation_sum"
        f"&timezone=Asia%2FTokyo&forecast_days=1"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DaisyKyushuBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            weather_code = data["daily"]["weathercode"][0]
            precipitation = data["daily"]["precipitation_sum"][0]
            if weather_code >= 51 or precipitation > 1.0:
                return "rain"
            elif weather_code <= 2:
                return "sunny"
            else:
                return "cloudy"
    except Exception as e:
        print(f"⚠️ 天気取得失敗: {e}")
        return "unknown"


def check_urgent_event(events):
    """3日以内に開催されるイベントを確認"""
    today = datetime.date.today()
    urgent = []
    for e in events:
        if e.get("status") == "past":
            continue
        date_str = e.get("date", "")
        try:
            start_str = date_str.split("〜")[0].strip() if "〜" in date_str else date_str
            if "-" in start_str:
                event_date = datetime.date.fromisoformat(start_str[:10])
                days_until = (event_date - today).days
                if 0 <= days_until <= 3:
                    urgent.append((days_until, e))
        except Exception:
            pass
    urgent.sort(key=lambda x: x[0])
    return urgent[0] if urgent else None


def pick_daisy_photo():
    """
    実写Daisyの写真をストックフォルダから選択する。
    使用済み写真は used/ に移動して重複投稿を防ぐ。
    ストックが空になったら used/ から復活させる。
    """
    extensions = [".jpg", ".jpeg", ".png", ".heic", ".HEIC", ".JPG", ".JPEG", ".PNG"]
    available = [
        f for f in PHOTO_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in [e.lower() for e in extensions]
    ]

    if not available:
        # ストックが空 → used/ から全部復活
        used_photos = [
            f for f in USED_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in [e.lower() for e in extensions]
        ]
        if used_photos:
            print("  📂 写真ストックが空になったため、使用済み写真を復活させます")
            for photo in used_photos:
                shutil.move(str(photo), str(PHOTO_DIR / photo.name))
            available = [
                f for f in PHOTO_DIR.iterdir()
                if f.is_file() and f.suffix.lower() in [e.lower() for e in extensions]
            ]
        else:
            print("  ⚠️ 写真ストックが空です。/home/ubuntu/daisy_photos/ に写真を追加してください")
            return None

    # 今日のシードでランダム選択（毎日違う写真が選ばれる）
    seed = get_today_seed()
    rng = random.Random(seed)
    selected = rng.choice(available)

    # 使用済みフォルダに移動
    dest = USED_DIR / selected.name
    # 同名ファイルがあればリネーム
    if dest.exists():
        stem = selected.stem
        suffix = selected.suffix
        dest = USED_DIR / f"{stem}_{datetime.date.today().isoformat()}{suffix}"
    shutil.move(str(selected), str(dest))

    print(f"  📸 選択した写真: {selected.name} → used/ に移動")
    return dest  # 移動先のパスを返す


def pick_spot(spots, weather="unknown", prefer_indoor=False):
    """天気に応じてスポットを選択"""
    seed = get_today_seed()
    rng = random.Random(seed)

    good_spots = [s for s in spots
                  if s.get("largeDog") in ["可", "OK", "○", "大型犬可"]
                  and s.get("status") not in ["閉業", "ペット同伴不可"]]
    if not good_spots:
        good_spots = [s for s in spots if s.get("status") not in ["閉業", "ペット同伴不可"]]

    if prefer_indoor or weather == "rain":
        indoor_keywords = ["カフェ", "レストラン", "ショッピング", "水族館", "博物館", "ホテル", "温泉", "室内"]
        indoor_spots = [s for s in good_spots
                        if any(k in (s.get("type", "") + s.get("memo", "")) for k in indoor_keywords)]
        if indoor_spots:
            return rng.choice(indoor_spots), "indoor"

    if weather == "sunny":
        outdoor_keywords = ["公園", "ドッグラン", "海岸", "山", "自然", "アウトドア", "キャンプ", "海"]
        outdoor_spots = [s for s in good_spots
                         if any(k in (s.get("type", "") + s.get("memo", "")) for k in outdoor_keywords)]
        if outdoor_spots:
            return rng.choice(outdoor_spots), "outdoor"

    return rng.choice(good_spots), "normal"


def pick_event(events):
    today = datetime.date.today()
    upcoming = []
    for e in events:
        if e.get("status") == "past":
            continue
        date_str = e.get("date", "")
        try:
            start_str = date_str.split("〜")[0].strip() if "〜" in date_str else date_str
            if "-" in start_str:
                event_date = datetime.date.fromisoformat(start_str[:10])
                if today <= event_date <= today + datetime.timedelta(days=60):
                    upcoming.append((event_date, e))
        except Exception:
            pass
    if not upcoming:
        return events[0] if events else None
    upcoming.sort(key=lambda x: x[0])
    return upcoming[0][1]


def infer_photo_context(photo_path):
    """写真のファイル名から場所・状況を推定する"""
    if not photo_path:
        return {}
    name = Path(photo_path).stem.lower()
    context = {}

    # 場所キーワード
    place_keywords = {
        "yufuin": "由布院", "beppu": "別府", "aso": "阿蘇", "kuju": "くじゅう",
        "fukuoka": "福岡", "nagasaki": "長崎", "kumamoto": "熊本",
        "kagoshima": "鹿児島", "miyazaki": "宮崎", "saga": "佐賀",
        "dogrun": "ドッグラン", "cafe": "カフェ", "beach": "海岸",
        "park": "公園", "mountain": "山", "onsen": "温泉",
        "ドッグラン": "ドッグラン", "カフェ": "カフェ", "海": "海岸",
        "公園": "公園", "山": "山", "温泉": "温泉",
    }
    for key, value in place_keywords.items():
        if key in name:
            context["place"] = value
            break

    # 状況キーワード
    situation_keywords = {
        "happy": "嬉しそう", "run": "走っている", "sleep": "寝ている",
        "play": "遊んでいる", "eat": "食べている", "swim": "泳いでいる",
        "walk": "散歩中", "birthday": "誕生日", "event": "イベント",
    }
    for key, value in situation_keywords.items():
        if key in name:
            context["situation"] = value
            break

    return context


def generate_caption(theme, item, client, photo_path=None, weather="unknown", urgent_days=None):
    """テーマと実写写真に応じたキャプションをGPTで生成"""
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"
    week_num = (today.day - 1) // 7
    photo_context = infer_photo_context(photo_path)
    place_hint = photo_context.get("place", "")
    situation_hint = photo_context.get("situation", "")

    # ===== AI活用術（月曜）=====
    if theme == "ai_tips":
        topic = AI_TIPS_TOPICS[week_num % len(AI_TIPS_TOPICS)]
        has_step2 = bool(topic.get("step1_ja"))
        step_text = ""
        if has_step2 and topic.get("step1_ja"):
            step_text = f"\n\n【STEP 1】愛犬の写真をChatGPTに添付して送る\n🇯🇵 {topic['step1_ja']}"
            if topic.get("step2_ja"):
                step_text += f"\n\n【STEP 2】STEP1の画像をChatGPTに添付して送る\n🇯🇵 {topic['step2_ja']}"
        else:
            step_text = f"\n\n【プロンプト（コピーOK）】\n🇯🇵 {topic['prompt_ja']}"

        caption = f"""{topic['hook']}

Daisyの写真で実際に試してみたよ✨{step_text}

🇺🇸 English prompt:
{topic['prompt_en']}

━━━━━━━━━━━
ChatGPT / Gemini に愛犬の写真を添付して送るだけ！

{topic['cta']}"""

        full_caption = f"""{caption}

九州の犬連れスポット情報はプロフのリンクから🐾"""

    # ===== 犬連れスポット紹介（火曜）=====
    elif theme == "spot":
        name = item.get('name', '')
        area = item.get('area', '')
        prefecture = item.get('prefecture', '九州')
        spot_type = item.get('type', '')
        memo = item.get('memo', '')[:100]
        large_dog = item.get('largeDog', '')

        place_intro = f"{place_hint}でのDaisyの写真と一緒に" if place_hint else ""

        prompt = f"""Daisyの実写写真に合わせた、{prefecture}の犬連れスポット紹介のInstagramキャプションを書いて。

スポット情報:
- 名前: {name}
- エリア: {area}
- タイプ: {spot_type}
- 大型犬: {large_dog}
- メモ: {memo}

条件:
- Daisyが一人称（「Daisyだよ！」「Daisyも行ってみたいな🐾」など）
- 絵文字を適度に使う
- 最初の1行でフォロワーの目を引く
- スポットの魅力を具体的に2〜3点
- 「詳しくはプロフのリンクから」で締める
- 200文字以内
- AIが書いたと分からないような自然な文体"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        caption = response.choices[0].message.content.strip()
        full_caption = caption

    # ===== Daisyの日常（水曜）=====
    elif theme == "daisy_daily":
        situation_text = f"（{situation_hint}）" if situation_hint else ""
        place_text = f"{place_hint}で" if place_hint else ""

        prompt = f"""Daisyの実写写真{situation_text}に合わせた、Instagramキャプションを書いて。

条件:
- Daisyが一人称（「今日はね〜」「Daisyだよ！」など）
- {place_text}の{season}の日常を感じさせる内容
- 絵文字を適度に使う
- 最初の1行でフォロワーの目を引く
- フォロワーが「いいね」を押したくなるような感情的な内容
- 最後にフォロワーへの問いかけ（「みんなの子はどう？」など）
- 150文字以内
- AIが書いたと分からないような自然な文体"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        caption = response.choices[0].message.content.strip()
        full_caption = caption

    # ===== スポット特集（木曜）=====
    elif theme == "spot_theme":
        week_of_year = today.isocalendar()[1]
        spot_themes_labels = [
            "福岡県の犬連れカフェ特集",
            "大分県の犬と泊まれる温泉旅館特集",
            "鹿児島県の大型犬OK公園特集",
            "熊本県のドッグラン特集",
            "長崎県の犬連れスポット特集",
            "佐賀県の犬連れスポット特集",
            "宮崎県の犬連れスポット特集",
        ]
        theme_title = spot_themes_labels[week_of_year % len(spot_themes_labels)]
        name = item.get('name', '') if item else ''
        area = item.get('area', '') if item else ''

        prompt = f"""Daisyの実写写真を使った「{theme_title}」の特集投稿のInstagramキャプションを書いて。

紹介スポット: {name}（{area}）

条件:
- Daisyが一人称で「{theme_title}を調べてみたよ！」という切り口
- スポットの魅力を具体的に
- 「保存して週末の参考にしてね」というCTA
- 「詳しくはプロフのリンクから」で締める
- 200文字以内
- AIが書いたと分からないような自然な文体"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        caption = response.choices[0].message.content.strip()
        full_caption = caption

    # ===== AIプロンプト集（金曜）=====
    elif theme == "ai_prompt":
        topic = AI_PROMPT_TOPICS[week_num % len(AI_PROMPT_TOPICS)]
        caption = f"""{topic['hook']}

Daisyの写真で試してみたよ✨

【プロンプト（コピーOK）】
🇯🇵 {topic['prompt_ja']}

🇺🇸 {topic['prompt_en']}

━━━━━━━━━━━
ChatGPT / Gemini に愛犬の写真を添付して送るだけ！

{topic['cta']}"""
        full_caption = caption

    # ===== 週末お出かけ（土曜）=====
    elif theme == "spot_weekend":
        name = item.get('name', '') if item else ''
        area = item.get('area', '') if item else ''
        prefecture = item.get('prefecture', '九州') if item else '九州'
        weather_text = {"rain": "雨の日でも", "sunny": "晴れた日に", "cloudy": "曇りでも"}.get(weather, "週末に")

        prompt = f"""Daisyの実写写真を使った、週末お出かけスポット提案のInstagramキャプションを書いて。

スポット: {name}（{area}、{prefecture}）
天気: {weather_text}

条件:
- Daisyが一人称で「今週末はここがおすすめ！」という切り口
- {weather_text}楽しめる魅力を具体的に
- 「保存して週末の参考にしてね🐾」というCTA
- 「詳しくはプロフのリンクから」で締める
- 180文字以内
- AIが書いたと分からないような自然な文体"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
        )
        caption = response.choices[0].message.content.strip()
        full_caption = caption

    # ===== Daisyの週末まとめ（日曜）=====
    elif theme == "daisy_weekly":
        place_text = f"{place_hint}での" if place_hint else "今週の"

        prompt = f"""Daisyの実写写真を使った、日曜日の週まとめInstagramキャプションを書いて。

条件:
- Daisyが一人称で「今週もありがとう！」という感謝の気持ち
- {place_text}思い出や{season}の季節感を入れる
- フォロワーへの感謝と来週への期待感
- 最後に「来週もよろしくね🐾」
- 150文字以内
- AIが書いたと分からないような自然な文体"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        caption = response.choices[0].message.content.strip()
        full_caption = caption

    # ===== 緊急イベント =====
    elif theme == "event_urgent":
        event_name = item.get('title') or item.get('name', '')
        area = item.get('area', '')
        date_str = item.get('date') or item.get('eventDate', '')
        days_text = f"あと{urgent_days}日！" if urgent_days is not None else "もうすぐ！"

        caption = f"""🚨 {days_text}

{event_name}

📍 {area}
📅 {date_str}

Daisyも行きたいな🐾
みんなは行く？

詳しくはプロフのリンクから👆"""
        full_caption = caption

    else:
        caption = f"Daisyだよ🐾 今日も九州の犬連れ情報をお届け！\n\n詳しくはプロフのリンクから👆"
        full_caption = caption

    return caption, full_caption


def upload_image(image_path):
    """manus-upload-fileで画像をS3にアップロード"""
    result = subprocess.run(
        ["manus-upload-file", str(image_path)],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise Exception(f"Upload failed: {result.stderr}")
    for line in result.stdout.split("\n"):
        if "CDN URL:" in line or "https://" in line:
            url = line.split("CDN URL:")[-1].strip() if "CDN URL:" in line else line.strip()
            if url.startswith("https://"):
                return url
    return str(image_path)


def get_hashtags(theme):
    """テーマ別ハッシュタグを返す"""
    base = "#犬のいる生活 #サモエド #サモエド部 #白い犬 #もふもふ犬 #大型犬のいる生活 #daisy_samoyed1217 #犬好きな人と繋がりたい"
    if theme in ["ai_tips", "ai_prompt"]:
        return f"#AI画像 #ChatGPT #AIアート #プロンプト #AI活用術 #AIトレンド {base}"
    elif theme in ["spot", "spot_weekend", "spot_theme"]:
        return f"#犬連れ旅行 #ペットと旅行 #九州旅行 #九州犬連れ #大型犬おでかけ #わんこ旅 #犬連れスポット #犬連れ九州 {base}"
    elif theme in ["daisy_daily", "daisy_weekly"]:
        return f"#サモエドのいる生活 #もふもふ #犬のいる暮らし #わんこ #ふわふわ #大型犬 {base}"
    elif theme == "event_urgent":
        return f"#犬イベント #ドッグイベント #九州 #犬連れ旅行 {base}"
    else:
        return base


def get_item_link(theme, item):
    if theme in ["spot", "spot_weekend", "spot_theme"]:
        spot_id = item.get('id', '') if item else ''
        return f"{SITE_URL}/spots.html#{spot_id}" if spot_id else f"{SITE_URL}/spots.html"
    elif theme in ["event", "event_urgent"]:
        return (item.get('officialUrl') if item else None) or f"{SITE_URL}/events.html"
    else:
        return SITE_URL


def main():
    print("=" * 60)
    print("🐾 Daisy Instagram - 本日の投稿案を生成中...")
    print("=" * 60)

    today = datetime.date.today()
    weekday = today.weekday()
    base_theme = THEME_BY_WEEKDAY[weekday]

    print(f"\n📅 {today.strftime('%Y年%m月%d日')} ({['月','火','水','木','金','土','日'][weekday]}曜日)")
    print(f"📌 本日のテーマ: {THEME_LABELS.get(base_theme, base_theme)}")

    spots, products, events = load_data()

    # 天気取得
    print("🌤️  天気を確認中...")
    weather = get_weather("福岡")
    weather_label = {"rain": "☔ 雨", "sunny": "☀️ 晴れ", "cloudy": "☁️ 曇り"}.get(weather, "不明")
    print(f"   今日の天気: {weather_label}")

    # 直前イベント確認
    urgent = check_urgent_event(events)
    urgent_days = urgent[0] if urgent else None
    urgent_event_data = urgent[1] if urgent else None
    if urgent_days is not None:
        print(f"🚨 直前イベント検出: {urgent_event_data.get('title') or urgent_event_data.get('name')} (あと{urgent_days}日)")

    # テーマ決定
    theme = base_theme
    item = None

    if urgent_days is not None and urgent_days <= 1:
        theme = "event_urgent"
        item = urgent_event_data
        print(f"\n⚠️  緊急イベントのため本日のテーマを変更: {THEME_LABELS['event_urgent']}")

    elif base_theme in ["spot", "spot_weekend"]:
        item, _ = pick_spot(spots, weather=weather, prefer_indoor=(weather == "rain"))
        print(f"   スポット: {item.get('name')} ({item.get('area')})")

    elif base_theme == "spot_theme":
        week_of_year = today.isocalendar()[1]
        spot_themes = [
            ("福岡県", "カフェ"),
            ("大分県", "温泉"),
            ("鹿児島県", "公園"),
            ("熊本県", "ドッグラン"),
            ("長崎県", None),
            ("佐賀県", None),
            ("宮崎県", None),
        ]
        pref, spot_type_filter = spot_themes[week_of_year % len(spot_themes)]
        filtered = [s for s in spots
                    if s.get("prefecture") == pref
                    and s.get("status") not in ["閉業", "ペット同伴不可"]]
        if spot_type_filter:
            typed = [s for s in filtered if spot_type_filter in s.get("type", "")]
            filtered = typed if typed else filtered
        seed = get_today_seed()
        rng = random.Random(seed)
        item = rng.choice(filtered) if filtered else rng.choice(spots)
        print(f"   特集スポット: {item.get('name')}")

    client = OpenAI()

    # ===== 実写Daisyの写真を選択 =====
    print("\n📸 Daisyの実写写真を選択中...")
    photo_path = pick_daisy_photo()

    if photo_path and Path(photo_path).exists():
        print(f"   ✅ 写真選択完了: {Path(photo_path).name}")
        # 写真をoutputディレクトリにコピー（投稿用）
        post_photo = OUTPUT_DIR / f"post_{today.isoformat()}.jpg"
        shutil.copy2(str(photo_path), str(post_photo))
        use_real_photo = True
    else:
        print("   ⚠️ 写真ストックが空です。フォールバック画像を使用します")
        post_photo = None
        use_real_photo = False

    # 投稿文生成
    print("\n📝 投稿文を生成中...")
    caption, full_caption = generate_caption(
        theme, item or {}, client,
        photo_path=str(photo_path) if photo_path else None,
        weather=weather,
        urgent_days=urgent_days
    )
    print("   ✅ 投稿文生成完了")

    # 画像アップロード
    image_cdn_url = None
    if post_photo and post_photo.exists():
        print("☁️  写真をアップロード中...")
        try:
            image_cdn_url = upload_image(post_photo)
            print(f"   ✅ アップロード完了: {image_cdn_url}")
        except Exception as e:
            print(f"   ⚠️ アップロード失敗: {e}")
    else:
        # フォールバック: サイトのOGP画像を使用
        image_cdn_url = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide/assets/og-image.png"
        print(f"   ⚠️ フォールバック画像を使用: {image_cdn_url}")

    # リンク・ハッシュタグ
    link = get_item_link(theme, item or {})
    hashtags = get_hashtags(theme)

    # キャプション（ハッシュタグ付き）
    caption_with_tags = f"{full_caption}\n\n{hashtags}"

    # 結果を保存
    item_name = ""
    if item:
        item_name = item.get('name') or item.get('productName') or item.get('title') or ''

    output = {
        "date": today.isoformat(),
        "weekday": ['月', '火', '水', '木', '金', '土', '日'][weekday],
        "theme": theme,
        "theme_label": THEME_LABELS.get(theme, theme),
        "weather": weather,
        "item_name": item_name,
        "caption": caption,
        "full_caption": full_caption,
        "caption_with_tags": caption_with_tags,
        "link": link,
        "photo_used": str(photo_path) if photo_path else "",
        "use_real_photo": use_real_photo,
        "image_cdn_url": image_cdn_url or "",
    }

    output_file = OUTPUT_DIR / f"post_{today.isoformat()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ===== Instagram自動投稿 =====
    print("\n📤 Instagramに自動投稿中...")

    payload = {
        "type": "post",
        "caption": caption_with_tags,
        "media": [
            {
                "type": "image",
                "media_url": image_cdn_url
            }
        ]
    }

    input_json = json.dumps(payload, ensure_ascii=False)
    cmd = [
        "manus-mcp-cli", "tool", "call", "create_instagram",
        "--server", "instagram",
        "--input", input_json
    ]

    try:
        result_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result_proc.returncode == 0:
            print("   ✅ Instagram投稿成功！")
            output["instagram_posted"] = True
            output["instagram_result"] = result_proc.stdout[:500]
        else:
            print(f"   ❌ Instagram投稿失敗")
            print(f"   stderr: {result_proc.stderr[:300]}")
            output["instagram_posted"] = False
            output["instagram_error"] = result_proc.stderr[:300]
    except Exception as e:
        print(f"   ❌ 投稿エラー: {e}")
        output["instagram_posted"] = False
        output["instagram_error"] = str(e)

    # 結果を更新保存
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("📱 本日のInstagram投稿完了")
    print("=" * 60)
    print(f"\n【テーマ】{THEME_LABELS.get(theme, theme)}：{item_name}")
    print(f"\n【実写写真使用】{'✅ ' + Path(photo_path).name if photo_path else '❌ フォールバック'}")
    print(f"\n【キャプション】\n{full_caption}")
    print(f"\n【画像URL】{image_cdn_url}")
    print(f"\n💾 保存先: {output_file}")

    return output


if __name__ == "__main__":
    result = main()
    print("\n✨ 本日の自動投稿が完了しました！")

    # インサイトログを更新
    try:
        import collect_insights
        collect_insights.main()
    except Exception as e:
        print(f"⚠️ インサイト収集エラー（投稿には影響なし）: {e}")

"""
Daisy九州犬連れガイド - Instagram自動投稿スクリプト（AI情報特化版）

【曜日別テーマ】
月: 🤖 AI活用術（保存必至！プロンプト・使い方Tips）
火: 🐾 犬連れスポット紹介（九州の大型犬OKスポット）
水: ✨ AI×ペット変身術（Daisyで試せるAI画像テクニック）
木: 🐾 犬連れスポット紹介②（エリア別・テーマ別特集）
金: 📸 AI画像プロンプト集（週末に試したくなるネタ）
土: 🗺️ 週末お出かけスポット（天気連動）
日: 📊 AI最新トレンドまとめ（今週のバズりAI情報）

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
import urllib.request
import urllib.error
from pathlib import Path
from openai import OpenAI

# ===== 設定 =====
SITE_URL = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide"
DATA_DIR = Path("/home/ubuntu/daisy-kyushu-dog-guide")
OUTPUT_DIR = Path("/home/ubuntu/daily_post_output")
OUTPUT_DIR.mkdir(exist_ok=True)

AI_DISCLAIMER = "※この投稿はAIが自動生成しています。情報は変更される場合があります。"

# 曜日別テーマ (0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日)
THEME_BY_WEEKDAY = {
    0: "ai_tips",       # 月: AI活用術
    1: "spot",          # 火: 犬連れスポット
    2: "ai_pet_art",    # 水: AI×ペット変身術
    3: "spot_theme",    # 木: スポット特集（エリア別・テーマ別）
    4: "ai_prompt",     # 金: AIプロンプト集
    5: "spot_weekend",  # 土: 週末スポット（天気連動）
    6: "ai_trend",      # 日: AI最新トレンドまとめ
}

THEME_LABELS = {
    "ai_tips":      "🤖 AI活用術",
    "spot":         "🐾 犬連れスポット紹介",
    "ai_pet_art":   "✨ AI×ペット変身術",
    "spot_theme":   "🗺️ スポット特集",
    "ai_prompt":    "📸 AIプロンプト集",
    "spot_weekend": "🗺️ 週末お出かけスポット",
    "ai_trend":     "📊 AI最新トレンドまとめ",
    "event_urgent": "🚨 イベント直前告知",
}

# AI活用術テーマのローテーション（月曜日ごとに変わる）
AI_TIPS_TOPICS = [
    {
        "title": "ChatGPTで愛犬の写真をスマホから脱出させる方法",
        "hook": "📱 愛犬がスマホを突き破って飛び出す！",
        "content": "2ステップで誰でもできるAI画像術",
        "step1": "愛犬の写真をChatGPTに添付して「スマホの画面に表示されている画像を作って。縦向きスマホ、秋の背景」と送る",
        "step2": "STEP1の画像を添付して「スマホ画面を突き破って飛び出す画像に変えて。ガラスの破片が飛び散っている」と送る",
        "prompt_ja": "スマホの画面に表示されている犬が、画面を突き破って飛び出す画像に変えて。ガラスの破片が飛び散っている。シネマティック、フォトリアリスティック。",
        "prompt_en": "The dog shown on the smartphone screen bursts through the screen and leaps out. Glass shards fly everywhere. Cinematic, photorealistic.",
        "cta": "うちの子でもやってみて！コメントで見せてね🐾",
        "hashtags": "#ChatGPT #AI画像 #犬のいる生活 #サモエド #AI活用術 #AIアート #犬好きな人と繋がりたい #プロンプト",
    },
    {
        "title": "愛犬を子犬の群れに囲ませる魔法のプロンプト",
        "hook": "🐶 うちの子が子犬に囲まれた！",
        "content": "世界でバズ中のAI画像トレンド",
        "step1": "愛犬の写真をChatGPTに添付して下記プロンプトを送るだけ！",
        "step2": "",
        "prompt_ja": "添付の写真の犬の周りに、同じ犬種の子犬を6〜8匹追加して。子犬たちは地面に自然に座ったり立ったりしている。背景・照明・元の犬の見た目は一切変えないで。フォトリアリスティック。",
        "prompt_en": "Place 6–8 puppies of the same breed sitting and standing close around the adult dog in the attached photo. Keep the original dog's appearance, background, and lighting completely unchanged. Photorealistic.",
        "cta": "作れたらコメントで見せてね！保存して後で試してみて🐾",
        "hashtags": "#ChatGPT #AI画像 #犬のいる生活 #サモエド #AI活用術 #子犬 #プロンプト #犬好きな人と繋がりたい",
    },
    {
        "title": "愛犬を王族に変える！ロイヤルポートレートの作り方",
        "hook": "👑 うちの子が貴族になった！",
        "content": "印刷してプレゼントにもなるクオリティ",
        "step1": "愛犬の写真をChatGPTに添付して下記プロンプトを送るだけ！",
        "step2": "",
        "prompt_ja": "添付の写真の犬を、王冠と深紅のベルベットのマントを着た貴族の犬として、クラシックな油絵風のポートレートに変換して。金色のフレーム装飾、暗い背景、ドラマチックな照明。",
        "prompt_en": "Transform the dog in the attached photo into a noble dog wearing a golden crown and deep crimson velvet cape. Classic oil painting portrait style, ornate gold frame, dark background, dramatic lighting.",
        "cta": "保存して愛犬の誕生日プレゼントにも使えるよ🎂",
        "hashtags": "#ChatGPT #AI画像 #犬のいる生活 #サモエド #AI活用術 #AIアート #プロンプト #犬好きな人と繋がりたい",
    },
    {
        "title": "愛犬が人間だったら？人間化AIアートの作り方",
        "hook": "🧑 うちの子が人間になった！",
        "content": "コメントが爆増するバズりネタ",
        "step1": "愛犬の写真をChatGPTに添付して下記プロンプトを送るだけ！",
        "step2": "",
        "prompt_ja": "添付の写真の犬が人間だったら？という発想で、犬の毛色と同じ髪色の明るく笑顔の人物のポートレートを作って。犬の特徴（毛色・目の色）を人間の外見に反映させて。背景はソフトなボケ、ゴールデンアワーの光。シネマティックポートレート写真スタイル。",
        "prompt_en": "Imagine the dog in the attached photo as a human. Create a photorealistic portrait of a person with hair color matching the dog's fur, with a bright smile. Reflect the dog's features (fur color, eye color) in the human appearance. Background: soft bokeh, golden hour light. Cinematic portrait style.",
        "cta": "うちの子バージョン作ったらコメントで見せてね！",
        "hashtags": "#ChatGPT #AI画像 #犬のいる生活 #サモエド #AI活用術 #AIアート #プロンプト #犬好きな人と繋がりたい",
    },
]

# AI×ペット変身術テーマ（水曜日）
AI_PET_ART_TOPICS = [
    {
        "title": "Daisyがスマホから飛び出した！",
        "hook": "📱 実際のDaisyの写真で作ってみた",
        "content": "ChatGPTの画像編集機能で誰でも作れる",
        "tips": [
            "愛犬の写真を1枚用意するだけでOK",
            "ChatGPT（GPT-4o）の画像添付機能を使う",
            "プロンプトは日本語でOK！",
        ],
        "hashtags": "#AI画像 #ChatGPT #サモエド #犬のいる生活 #AIアート #プロンプト #AI活用 #犬好きな人と繋がりたい",
    },
    {
        "title": "DaisyをAIで子犬の群れに囲ませてみた",
        "hook": "🐶 実際のDaisyの写真で試してみた結果",
        "content": "1プロンプトで完成！世界でバズ中のトレンド",
        "tips": [
            "愛犬の写真を添付するだけ",
            "背景・元の犬の見た目は変わらない",
            "子犬の数は自由に指定できる",
        ],
        "hashtags": "#AI画像 #ChatGPT #サモエド #犬のいる生活 #AIアート #子犬 #AI活用 #犬好きな人と繋がりたい",
    },
]

# AIトレンドまとめテーマ（日曜日）
AI_TREND_TOPICS = [
    {
        "title": "今週のAI×ペット画像トレンドまとめ",
        "trends": [
            "📱 スマホ突き破り系 → 世界中でバズ中",
            "🐶 子犬に囲まれる系 → 保存数が爆増",
            "👑 ロイヤルポートレート系 → 誕生日プレゼントに人気",
            "🧑 人間化系 → コメントが爆増するタイプ",
        ],
        "tool": "ChatGPT（GPT-4o）の画像添付機能を使うだけ！",
        "hashtags": "#AI画像 #ChatGPT #AIトレンド #犬のいる生活 #サモエド #AI活用術 #AIアート #プロンプト",
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


def pick_product(products):
    seed = get_today_seed() + 1
    rng = random.Random(seed)
    def safe_rating(p):
        try:
            return float(p.get("rating") or 0)
        except (ValueError, TypeError):
            return 0.0
    good = [p for p in products
            if safe_rating(p) >= 4.0
            and p.get("affiliateStatus") not in ["inactive", None, ""]]
    if not good:
        good = [p for p in products
                if p.get("affiliateStatus") in ["affiliate-active", "active"]]
    pool = good if good else products
    return rng.choice(pool) if pool else None


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


def generate_caption(theme, item, client, weather="unknown", urgent_days=None):
    """テーマに応じたキャプションをGPTで生成"""
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"
    week_num = (today.day - 1) // 7  # 月内の週番号 (0〜4)

    # ===== AI活用術（月曜）=====
    if theme == "ai_tips":
        topic = AI_TIPS_TOPICS[week_num % len(AI_TIPS_TOPICS)]
        has_step2 = bool(topic.get("step2"))
        step2_text = f"\n\n【STEP 2】STEP1の画像をChatGPTに添付して送る\n🇯🇵 {topic['prompt_ja']}\n🇺🇸 {topic['prompt_en']}" if has_step2 else ""
        caption = f"""{topic['hook']}

{topic['content']}

━━━━━━━━━━━
📋 魔法のプロンプト（コピーOK）
━━━━━━━━━━━

【STEP 1】愛犬の写真をChatGPTに添付して送る
🇯🇵 {topic['prompt_ja']}
🇺🇸 {topic['prompt_en']}{step2_text}

━━━━━━━━━━━
ChatGPT / Gemini に送るだけ！

{topic['cta']}"""
        return caption, f"{caption}\n\n{AI_DISCLAIMER}"

    # ===== AI×ペット変身術（水曜）=====
    elif theme == "ai_pet_art":
        topic = AI_PET_ART_TOPICS[week_num % len(AI_PET_ART_TOPICS)]
        tips_text = "\n".join([f"✅ {t}" for t in topic["tips"]])
        caption = f"""{topic['hook']}

{topic['content']}

{tips_text}

詳しい手順はプロフのリンクから🐾
うちの子でも試してみてね！"""
        return caption, f"{caption}\n\n{AI_DISCLAIMER}"

    # ===== AIプロンプト集（金曜）=====
    elif theme == "ai_prompt":
        topic = AI_TIPS_TOPICS[(week_num + 2) % len(AI_TIPS_TOPICS)]  # 月曜とずらす
        prompt = f"""あなたはAI画像生成のプロで、Instagramで「保存必至」と言われるプロンプト紹介投稿を作成する専門家です。

今週末に試したくなるAI画像プロンプトを1つ紹介するInstagram投稿文を作成してください。

テーマ: {topic['title']}
プロンプト（日本語）: {topic['prompt_ja']}
プロンプト（英語）: {topic['prompt_en']}

【ルール】
- 300文字以内（ハッシュタグ・注記除く）
- 最初の1行は短いキャッチコピー（絵文字あり、20文字以内）
- 「週末に試してみて！」という呼びかけを含める
- プロンプトをそのまま投稿文中に載せる（コピペしやすいように）
- ハッシュタグは含めない

投稿文のみ出力してください。"""
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600, temperature=0.7,
        )
        caption = response.choices[0].message.content.strip()
        return caption, f"{caption}\n\n{AI_DISCLAIMER}"

    # ===== AIトレンドまとめ（日曜）=====
    elif theme == "ai_trend":
        topic = AI_TREND_TOPICS[0]
        trends_text = "\n".join(topic["trends"])
        prompt = f"""あなたはAI情報を発信するInstagramアカウントの担当者です。

今週のAI×ペット画像トレンドをまとめた「保存必至」のInstagram投稿文を作成してください。

今週のトレンド:
{trends_text}

使えるツール: {topic['tool']}

【ルール】
- 400文字以内（ハッシュタグ・注記除く）
- 最初の1行は短いキャッチコピー（絵文字あり、20文字以内）
- 「保存して後で試してみて！」という呼びかけを含める
- 各トレンドを箇条書きで紹介
- ハッシュタグは含めない

投稿文のみ出力してください。"""
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600, temperature=0.7,
        )
        caption = response.choices[0].message.content.strip()
        return caption, f"{caption}\n\n{AI_DISCLAIMER}"

    # ===== スポット特集（木曜）: エリア別・テーマ別特集 =====
    elif theme == "spot_theme":
        # 週番号でテーマを変える
        week_of_year = today.isocalendar()[1]
        spot_themes = [
            ("福岡県", "カフェ", "福岡県の犬連れカフェ特集"),
            ("大分県", "温泉", "大分県の犬と泊まれる温泉旅館特集"),
            ("鹿児島県", "公園", "鹿児島県の大型犬OKな公園特集"),
            ("熊本県", "ドッグラン", "熊本県のドッグラン特集"),
            ("長崎県", None, "長崎県の犬連れスポット特集"),
            ("佐賀県", None, "佐賀県の犬連れスポット特集"),
            ("宮崎県", None, "宮崎県の犬連れスポット特集"),
        ]
        pref, spot_type_filter, theme_title = spot_themes[week_of_year % len(spot_themes)]

        # 指定エリア・タイプでフィルタ
        filtered = [s for s in spots
                    if s.get("prefecture") == pref
                    and s.get("status") not in ["閉業", "ペット同伴不可"]]
        if spot_type_filter:
            typed = [s for s in filtered if spot_type_filter in s.get("type", "")]
            filtered = typed if typed else filtered

        seed = get_today_seed()
        rng = random.Random(seed)
        item = rng.choice(filtered) if filtered else rng.choice(spots)

        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
今週の特集テーマ「{theme_title}」の投稿を作成してください。

スポット名: {item.get('name')}
エリア: {item.get('area')}
種別: {item.get('type')}
大型犬: {item.get('largeDog', '')}
メモ: {item.get('memo', '')}
営業時間: {item.get('hours', '')}
料金: {item.get('fee', '')}

【ルール】
- 300文字以内（ハッシュタグ・注記除く）
- 最初の1行は「今週の特集：{theme_title}」から始める
- Daisyが実際に訪れた感想風に書く
- 「要確認」「不明」「空欄」の情報は書かない
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない

キャプションのみ出力してください。"""
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500, temperature=0.7,
        )
        base_caption = response.choices[0].message.content.strip()
        return base_caption, f"{base_caption}\n\n{AI_DISCLAIMER}"

    # ===== 犬連れスポット（火曜・土曜）=====
    elif theme in ["spot", "spot_weekend"]:
        weekend_note = "週末のお出かけに！" if theme == "spot_weekend" else ""
        indoor_note = "（室内・雨の日OK）" if weather == "rain" else ""
        weather_intro = "今日は雨ですね☔ 雨の日でも愛犬と楽しめる室内スポットをご紹介！\n\n" if weather == "rain" else "今日はお出かけ日和🌞 愛犬と一緒に行きたいスポットをご紹介！\n\n" if weather == "sunny" else ""
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
サモエドのDaisyと一緒に九州を旅するコンセプトのアカウントです。

以下のスポット情報を元に、Instagramの投稿キャプションを作成してください。

スポット名: {item.get('name')}{indoor_note}
エリア: {item.get('area')}
種別: {item.get('type')}
大型犬: {item.get('largeDog', '')}
メモ: {item.get('memo', '')}
営業時間: {item.get('hours', '')}
料金: {item.get('fee', '')}

【ルール】
- 300文字以内（ハッシュタグ・注記除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- Daisyが実際に訪れた感想風に書く（一人称: Daisyが〜）
- {weekend_note}
- 「要確認」「不明」「空欄」の情報は書かない
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない

キャプションのみ出力してください。"""
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500, temperature=0.7,
        )
        base_caption = response.choices[0].message.content.strip()
        full_caption = f"{weather_intro}{base_caption}\n\n{AI_DISCLAIMER}"
        return base_caption, full_caption

    # ===== おすすめ犬グッズ（木曜）=====
    elif theme == "product":
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。

以下の商品情報を元に、Instagramの投稿キャプションを作成してください。

商品名: {item.get('productName', '')}
カテゴリ: {item.get('category', '')}
対象: {item.get('target', '')}
メモ: {item.get('memo', '')}
評価: {item.get('rating', '')}点（{item.get('reviewCount', '')}件）

【ルール】
- 300文字以内（ハッシュタグ・注記除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- 大型犬・サモエドとの旅行に役立つ観点で紹介
- 具体的なメリットを1〜2つ書く
- 「要確認」の情報は書かない
- 最後に「楽天で購入できます🛒 詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない

キャプションのみ出力してください。"""
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500, temperature=0.7,
        )
        base_caption = response.choices[0].message.content.strip()
        return base_caption, f"{base_caption}\n\n{AI_DISCLAIMER}"

    # ===== イベント直前告知 =====
    elif theme == "event_urgent":
        intro = ""
        if urgent_days == 0:
            intro = "🚨 今日開催！見逃せないドッグイベントです！\n\n"
        elif urgent_days == 1:
            intro = "⏰ 明日開催！まだ間に合います！\n\n"
        else:
            intro = f"📅 あと{urgent_days}日！直前告知です！\n\n"
        prompt = f"""以下のイベント情報を元に、Instagramの投稿キャプションを作成してください。

イベント名: {item.get('title') or item.get('name', '')}
エリア: {item.get('area', '')}
会場: {item.get('venue', '')}
開催日: {item.get('date') or item.get('eventDate', '')}
入場料: {item.get('fee', '')}
概要: {item.get('description', '')}

【ルール】
- 300文字以内（ハッシュタグ・注記除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- 開催日・場所は必ず明記する
- 「要確認」「不明」の情報は省く
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない

キャプションのみ出力してください。"""
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500, temperature=0.7,
        )
        base_caption = response.choices[0].message.content.strip()
        return base_caption, f"{intro}{base_caption}\n\n{AI_DISCLAIMER}"

    else:
        caption = "Daisyと一緒に九州を旅しよう🐾\n\n九州の犬連れスポット455件以上掲載中！\n詳しくはプロフのリンクから🐾"
        return caption, f"{caption}\n\n{AI_DISCLAIMER}"


def generate_ad_image(theme, item, client, output_path, weather="unknown"):
    """gpt-image-2で投稿画像を生成"""
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"
    week_num = (today.day - 1) // 7

    if theme == "ai_tips":
        topic = AI_TIPS_TOPICS[week_num % len(AI_TIPS_TOPICS)]
        image_prompt = f"""Professional Japanese Instagram post image for AI tips content.
Style: Clean modern dark background with neon blue/purple accent colors. Tech-savvy aesthetic.
Main visual: A smartphone screen showing a cute white Samoyed dog photo, with the dog dramatically bursting through the screen with glass shards flying.
Text overlay: '{topic['hook']}' in large bold Japanese text at top. '魔法のプロンプト公開中' badge. 'ChatGPT / Gemini で試せる！' at bottom.
Quality: High-resolution, Instagram-ready, 1:1 square format. Readable Japanese text."""

    elif theme == "ai_pet_art":
        topic = AI_PET_ART_TOPICS[week_num % len(AI_PET_ART_TOPICS)]
        image_prompt = f"""Professional Japanese Instagram post image for AI pet art content.
Style: Clean modern aesthetic with soft pastel colors and tech elements.
Main visual: A beautiful white fluffy Samoyed dog in a magical AI-transformed scene. {topic['hook']}
Text overlay: '{topic['hook']}' in large bold Japanese text. 'AI×ペット変身術' badge. 'ChatGPTで作れる！' label.
Quality: High-resolution, Instagram-ready, 1:1 square format. Readable Japanese text."""

    elif theme == "ai_prompt":
        topic = AI_TIPS_TOPICS[(week_num + 2) % len(AI_TIPS_TOPICS)]
        image_prompt = f"""Professional Japanese Instagram post image for AI prompt tips.
Style: Clean modern design with gradient background (purple to blue). Code/prompt aesthetic.
Main visual: A white Samoyed dog in a magical transformed AI art scene. Beautiful cinematic lighting.
Text overlay: '今週末試したいAIプロンプト' in large bold Japanese text. 'コピペOK' badge. 'ChatGPT / Gemini 対応' label.
Quality: High-resolution, Instagram-ready, 1:1 square format. Readable Japanese text."""

    elif theme == "ai_trend":
        image_prompt = f"""Professional Japanese Instagram post image for AI trend summary.
Style: Clean modern infographic style with dark background and colorful accent elements.
Main visual: Multiple small AI-transformed dog photos arranged in a grid/collage. White Samoyed featured prominently.
Text overlay: '今週のAI×ペット画像トレンド' in large bold Japanese text. '保存必至' badge. '4つのトレンドを解説' label.
Quality: High-resolution, Instagram-ready, 1:1 square format. Readable Japanese text."""

    elif theme in ["spot", "spot_weekend"]:
        name = item.get('name', '')
        area = item.get('area', '')
        spot_type = item.get('type', '')
        weather_desc = "rainy cozy atmosphere" if weather == "rain" else "sunny bright day" if weather == "sunny" else "pleasant day"
        image_prompt = f"""Professional Japanese Instagram flyer for a dog-friendly spot in Kyushu.
Main subject: Fluffy white Samoyed dog enjoying at '{name}' in {area} ({spot_type}), {weather_desc}, {season} season.
Style: Bright cheerful modern Japanese ad, clean typography, 1:1 square format.
Text overlay: Title '{name}', badge '{area}', '大型犬OK', '犬連れOK'.
Quality: Readable Japanese text, professional Instagram design."""

    elif theme == "spot_theme":
        week_of_year = datetime.date.today().isocalendar()[1]
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
        spot_type = item.get('type', '') if item else ''
        image_prompt = f"""Professional Japanese Instagram flyer for a dog-friendly spot special feature in Kyushu.
Theme: '{theme_title}'
Main subject: Fluffy white Samoyed dog enjoying at '{name}' in {area} ({spot_type}), {season} season.
Style: Bright cheerful modern Japanese ad, clean typography, special feature badge, 1:1 square format.
Text overlay: Special feature title '{theme_title}', spot name '{name}', badge '{area}', '大型犬OK', '犬連れOK'.
Quality: Readable Japanese text, professional Instagram design."""

    elif theme == "event_urgent":
        event_name = item.get('title') or item.get('name', '')
        area = item.get('area', '')
        date_str = item.get('date') or item.get('eventDate', '')
        image_prompt = f"""Professional Japanese Instagram event poster. URGENT event!
Main subject: Fluffy white Samoyed dog at a festive dog event in Kyushu.
Style: Bright energetic modern Japanese event poster, vibrant colors, 1:1 square format.
Text overlay: Title '{event_name}', date '{date_str}', location '{area}', 'イベント開催！'.
Quality: Readable Japanese text, professional Instagram design."""

    else:
        image_prompt = f"""Professional Japanese Instagram flyer for a dog travel guide website.
Main subject: Fluffy white Samoyed dog in front of beautiful Kyushu scenery.
Style: Bright cheerful modern Japanese ad, {season} colors, clean layout, 1:1 square format.
Text overlay: Title '九州犬連れガイド', '455スポット掲載', '大型犬OK情報満載'.
Quality: Readable Japanese text, professional Instagram design."""

    response = client.images.generate(
        model="gpt-image-2",
        prompt=image_prompt,
        size="1024x1024",
        n=1,
    )
    image_data = response.data[0].b64_json
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_data))
    return str(output_path)


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
    base = "#犬のいる生活 #サモエド #サモエド部 #白い犬 #もふもふ犬 #大型犬のいる生活 #daisy_samoyed1217"
    if theme in ["ai_tips", "ai_pet_art", "ai_prompt", "ai_trend"]:
        return f"#AI画像 #ChatGPT #AIアート #プロンプト #AI活用術 #AIトレンド {base}"
    elif theme in ["spot", "spot_weekend"]:
        return f"#犬連れ旅行 #ペットと旅行 #九州旅行 #九州犬連れ #大型犬おでかけ #わんこ旅 #犬連れスポット #犬連れ九州 {base}"
    elif theme == "product":
        return f"#犬グッズ #大型犬グッズ #犬用品 #わんこグッズ #楽天 {base}"
    elif theme == "event_urgent":
        return f"#犬イベント #ドッグイベント #九州 #犬連れ旅行 {base}"
    else:
        return base


def get_item_link(theme, item):
    if theme in ["spot", "spot_weekend"]:
        spot_id = item.get('id', '')
        return f"{SITE_URL}/spots.html#{spot_id}" if spot_id else f"{SITE_URL}/spots.html"
    elif theme == "product":
        return item.get('rakutenAffiliateUrl') or item.get('normalUrl') or SITE_URL
    elif theme in ["event", "event_urgent"]:
        return item.get('officialUrl') or f"{SITE_URL}/events.html"
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

    # 直前イベント確認（どの曜日でも緊急イベントがあれば優先）
    urgent = check_urgent_event(events)
    urgent_days = urgent[0] if urgent else None
    urgent_event_data = urgent[1] if urgent else None
    if urgent_days is not None:
        print(f"🚨 直前イベント検出: {urgent_event_data.get('title') or urgent_event_data.get('name')} (あと{urgent_days}日)")

    # テーマ決定（優先順位: 緊急イベント > 曜日テーマ）
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
        # 木曜: エリア別・テーマ別スポット特集
        week_of_year = today.isocalendar()[1]
        spot_themes = [
            ("福岡県", "カフェ", "福岡県の犬連れカフェ特集"),
            ("大分県", "温泉", "大分県の犬と泊まれる温泉旅館特集"),
            ("鹿児島県", "公園", "鹿児島県の大型犬OK公園特集"),
            ("熊本県", "ドッグラン", "熊本県のドッグラン特集"),
            ("長崎県", None, "長崎県の犬連れスポット特集"),
            ("佐賀県", None, "佐賀県の犬連れスポット特集"),
            ("宮崎県", None, "宮崎県の犬連れスポット特集"),
        ]
        pref, spot_type_filter, theme_title = spot_themes[week_of_year % len(spot_themes)]
        filtered = [s for s in spots
                    if s.get("prefecture") == pref
                    and s.get("status") not in ["閉業", "ペット同伴不可"]]
        if spot_type_filter:
            typed = [s for s in filtered if spot_type_filter in s.get("type", "")]
            filtered = typed if typed else filtered
        seed = get_today_seed()
        rng = random.Random(seed)
        item = rng.choice(filtered) if filtered else rng.choice(spots)
        print(f"   特集テーマ: {theme_title} / スポット: {item.get('name')}")

    client = OpenAI()

    # 投稿文生成
    print("\n📝 投稿文を生成中...")
    caption, full_caption = generate_caption(
        theme, item or {}, client,
        weather=weather,
        urgent_days=urgent_days
    )
    print("   ✅ 投稿文生成完了")

    # 画像生成
    print("🎨 投稿画像を生成中...")
    image_path = OUTPUT_DIR / f"post_{today.isoformat()}.png"
    try:
        generate_ad_image(theme, item or {}, client, image_path, weather=weather)
        print(f"   ✅ 画像生成完了: {image_path}")
    except Exception as e:
        print(f"   ⚠️ 画像生成失敗: {e}")
        image_path = None

    # 画像アップロード
    image_cdn_url = None
    if image_path and image_path.exists():
        print("☁️  画像をアップロード中...")
        try:
            image_cdn_url = upload_image(image_path)
            print(f"   ✅ アップロード完了: {image_cdn_url}")
        except Exception as e:
            print(f"   ⚠️ アップロード失敗: {e}")
            image_cdn_url = str(image_path)

    # リンク・ハッシュタグ
    link = get_item_link(theme, item or {})
    hashtags = get_hashtags(theme)

    # 投稿画像URL決定
    post_image_url = image_cdn_url
    if not post_image_url or not post_image_url.startswith("http"):
        post_image_url = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide/assets/og-image.png"

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
        "image_path": str(image_path) if image_path else "",
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
                "media_url": post_image_url
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
    print(f"\n【キャプション】\n{full_caption}")
    print(f"\n【画像URL】{post_image_url}")
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

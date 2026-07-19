#!/usr/bin/env python3
"""
Daisy九州犬連れガイド - 統合Instagram自動投稿スクリプト（メイン）

【組み合わせた4つの機能】
1. 曜日別テーマ投稿（月水金=スポット、火土=グッズ、木=イベント、日=サマリー）
2. 今日の一スポット（spots.jsonから毎日1件ずつ自動紹介、455件で1年以上ネタ継続）
3. イベント直前リマインド（3日以内のイベントを最優先で告知）
4. 天気連動（晴れ→屋外スポット優先、雨→室内スポット特集に自動切り替え）

【全投稿にAI注記を追加】
「※この投稿はAIが自動生成しています。情報は変更される場合があります。」

毎朝8:00に実行。投稿案を生成してManusがユーザーに確認を求める。
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

# AI注記（全投稿に追加）
AI_DISCLAIMER = "※この投稿はAIが自動生成しています。営業時間・料金・ペット可否等の情報は変更される場合があります。お出かけ前に必ず公式サイトや現地にご確認ください。"

# 曜日別テーマ (0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日)
THEME_BY_WEEKDAY = {
    0: "spot",      # 月: スポット紹介
    1: "product",   # 火: おすすめグッズ
    2: "spot",      # 水: スポット紹介
    3: "event",     # 木: イベント告知
    4: "spot",      # 金: 週末スポット
    5: "product",   # 土: 週末グッズ
    6: "summary",   # 日: サイト紹介・まとめ
}

THEME_LABELS = {
    "spot": "犬連れスポット紹介",
    "product": "おすすめ犬グッズ",
    "event": "イベント告知",
    "summary": "サイト紹介",
    "weather_indoor": "☔ 雨の日おすすめ室内スポット",
    "event_urgent": "🚨 イベント直前告知",
}


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
    good = [p for p in products if p.get("rating", 0) >= 4.0 and p.get("affiliateStatus") != "inactive"]
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
    """テーマ・天気・緊急度に応じたキャプションを生成"""
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"

    # イントロ文（天気・緊急告知）
    intro = ""
    if urgent_days is not None:
        if urgent_days == 0:
            intro = "🚨 今日開催！見逃せないドッグイベントです！\n\n"
        elif urgent_days == 1:
            intro = "⏰ 明日開催！まだ間に合います！\n\n"
        else:
            intro = f"📅 あと{urgent_days}日！直前告知です！\n\n"
    elif weather == "rain":
        intro = "今日は雨ですね☔ 雨の日でも愛犬と楽しめる室内スポットをご紹介！\n\n"
    elif weather == "sunny":
        intro = "今日はお出かけ日和🌞 愛犬と一緒に行きたいスポットをご紹介！\n\n"

    if theme in ["spot", "weather_indoor"]:
        indoor_note = "（室内・雨の日OK）" if theme == "weather_indoor" else ""
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
- 「要確認」「不明」「空欄」の情報は書かない
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない
- 改行を適切に使う

キャプションのみ出力してください。"""

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
- 改行を適切に使う

キャプションのみ出力してください。"""

    elif theme in ["event", "event_urgent"]:
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。

以下のイベント情報を元に、Instagramの投稿キャプションを作成してください。

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
- 改行を適切に使う

キャプションのみ出力してください。"""

    else:  # summary
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。

{season}の週末のお出かけを促す、サイト紹介のInstagramキャプションを作成してください。

サイト概要:
- 九州の犬連れスポット455件以上掲載
- 大型犬・サモエド向け情報に特化
- イベント情報・おすすめグッズも掲載
- 動物病院132件・アウトドア174件も掲載

【ルール】
- 300文字以内（ハッシュタグ・注記除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- 週末のお出かけを促す内容
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない
- 改行を適切に使う

キャプションのみ出力してください。"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.7,
    )
    base_caption = response.choices[0].message.content.strip()

    # イントロ + キャプション + AI注記
    full_caption = f"{intro}{base_caption}\n\n{AI_DISCLAIMER}"
    return base_caption, full_caption


def generate_ad_image(theme, item, client, output_path, weather="unknown"):
    """gpt-image-2で広告風チラシ画像を生成"""
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"
    weather_desc = "rainy cozy atmosphere" if weather == "rain" else "sunny bright day" if weather == "sunny" else "pleasant day"

    if theme in ["spot", "weather_indoor"]:
        name = item.get('name', '')
        area = item.get('area', '')
        spot_type = item.get('type', '')
        indoor_note = "cozy indoor" if theme == "weather_indoor" else "outdoor"
        image_prompt = f"""Professional Japanese Instagram flyer for a dog-friendly spot in Kyushu.
Main subject: Fluffy white Samoyed dog enjoying {indoor_note} at '{name}' in {area} ({spot_type}), {weather_desc}.
Style: Bright cheerful modern Japanese ad, {season} colors, clean typography, 1:1 square format.
Text overlay: Title '{name}', badge '{area}', '大型犬OK', '犬連れOK'.
Quality: Readable Japanese text, professional Instagram design."""

    elif theme == "product":
        product_name = item.get('productName', '')
        category = item.get('category', '')
        image_prompt = f"""Professional Japanese Instagram flyer for a dog product.
Main subject: Fluffy white Samoyed dog with '{product_name}' ({category}).
Style: Bright clean modern Japanese ad, warm colors, product photography feel, 1:1 square format.
Text overlay: Title '{product_name}', badge '{category}', '楽天で購入', '大型犬おすすめ'.
Quality: Readable Japanese text, professional Instagram design."""

    elif theme in ["event", "event_urgent"]:
        event_name = item.get('title') or item.get('name', '')
        area = item.get('area', '')
        date_str = item.get('date') or item.get('eventDate', '')
        urgency = "URGENT event happening soon! " if theme == "event_urgent" else ""
        image_prompt = f"""Professional Japanese Instagram event poster. {urgency}
Main subject: Fluffy white Samoyed dog at a festive dog event in Kyushu.
Style: Bright energetic modern Japanese event poster, vibrant colors, 1:1 square format.
Text overlay: Title '{event_name}', date '{date_str}', location '{area}', 'イベント開催！'.
Quality: Readable Japanese text, professional Instagram design."""

    else:  # summary
        image_prompt = f"""Professional Japanese Instagram flyer for a dog travel guide website.
Main subject: Fluffy white Samoyed dog in front of beautiful Kyushu scenery, {weather_desc}.
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
    # URLが見つからない場合はローカルパスを返す
    return str(image_path)


def get_item_link(theme, item):
    if theme in ["spot", "weather_indoor"]:
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
    print("🐾 Daisy九州犬連れガイド - 本日の投稿案を生成中...")
    print("=" * 60)

    today = datetime.date.today()
    weekday = today.weekday()
    base_theme = THEME_BY_WEEKDAY[weekday]

    print(f"\n📅 {today.strftime('%Y年%m月%d日')} ({['月','火','水','木','金','土','日'][weekday]}曜日)")

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

    # テーマ決定（優先順位: 緊急イベント > 天気連動 > 曜日テーマ）
    theme = base_theme
    item = None
    weather_note = ""

    if urgent_days is not None and urgent_days <= 1:
        theme = "event_urgent"
        item = urgent_event_data
        print(f"\n📌 テーマ: {THEME_LABELS['event_urgent']} → {item.get('title') or item.get('name')}")

    elif base_theme == "spot" and weather == "rain":
        theme = "weather_indoor"
        item, _ = pick_spot(spots, weather="rain", prefer_indoor=True)
        weather_note = "雨の日室内スポット"
        print(f"\n📌 テーマ: {THEME_LABELS['weather_indoor']} → {item.get('name')} ({item.get('area')})")

    elif base_theme == "spot":
        item, _ = pick_spot(spots, weather=weather)
        print(f"\n📌 テーマ: {THEME_LABELS['spot']} → {item.get('name')} ({item.get('area')})")

    elif base_theme == "product":
        item = pick_product(products)
        if not item:
            theme = "spot"
            item, _ = pick_spot(spots, weather)
            print(f"\n📌 テーマ: 商品データなし → スポット紹介に切り替え: {item.get('name')}")
        else:
            print(f"\n📌 テーマ: {THEME_LABELS['product']} → {item.get('productName', '')}")

    elif base_theme == "event":
        item = pick_event(events)
        if not item:
            theme = "spot"
            item, _ = pick_spot(spots, weather)
            print(f"\n📌 テーマ: イベントなし → スポット紹介に切り替え: {item.get('name')}")
        else:
            print(f"\n📌 テーマ: {THEME_LABELS['event']} → {item.get('title') or item.get('name')}")

    else:  # summary
        print(f"\n📌 テーマ: {THEME_LABELS['summary']}")

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
    print("🎨 広告風チラシ画像を生成中...")
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

    # リンク
    link = get_item_link(theme, item or {})

    # 楽天Room用投稿文（商品テーマのみ）
    rakuten_room_comment = None
    if theme == "product" and item:
        prompt = f"""楽天ROOMの投稿コメントを作成してください。
商品名: {item.get('productName', '')}
カテゴリ: {item.get('category', '')}
メモ: {item.get('memo', '')}
【ルール】100文字以内、大型犬・サモエドとの旅行に役立つ観点、絵文字1〜2個、自然な口コミ風
コメントのみ出力してください。"""
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200, temperature=0.7,
        )
        rakuten_room_comment = resp.choices[0].message.content.strip()

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
        "weather_note": weather_note,
        "urgent_event_days": urgent_days,
        "item_name": item_name,
        "caption": caption,
        "ai_disclaimer": AI_DISCLAIMER,
        "full_caption": full_caption,
        "link": link,
        "image_path": str(image_path) if image_path else "",
        "image_cdn_url": image_cdn_url or "",
        "rakuten_room_comment": rakuten_room_comment,
    }

    output_file = OUTPUT_DIR / f"post_{today.isoformat()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ===== Instagram自動投稿（確認なし）=====
    print("\n📤 Instagramに自動投稿中...")

    # 投稿に使う画像URLを決定
    post_image_url = image_cdn_url
    if not post_image_url or not post_image_url.startswith("http"):
        # フォールバック: OGP画像
        post_image_url = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide/assets/og-image.png"

    # ハッシュタグを追加
    hashtags = (
        "#犬のいる生活 #犬連れ旅行 #ペットと旅行 #サモエド "
        "#九州旅行 #九州犬連れ #大型犬おでかけ #わんこ旅 #犬連れスポット "
        "#サモエド部 #白い犬 #もふもふ犬 #大型犬のいる生活 #犬連れ九州 #daisy_samoyed1217"
    )
    caption_with_tags = f"{full_caption}\n\n{hashtags}"

    # MCP経由でInstagramに投稿
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
            print(result_proc.stdout[:500] if result_proc.stdout else "")
            output["instagram_posted"] = True
            output["instagram_result"] = result_proc.stdout[:500]
        else:
            print(f"   ❌ Instagram投稿失敗")
            print(f"   stdout: {result_proc.stdout[:300]}")
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
    if rakuten_room_comment:
        print(f"\n【楽天Roomコメント】{rakuten_room_comment}")
    print(f"\n💾 保存先: {output_file}")

    return output


if __name__ == "__main__":
    result = main()
    print("\n✨ 本日の自動投稿が完了しました！")

#!/usr/bin/env python3
"""
Daisy九州犬連れガイド - 統合自動投稿データ生成スクリプト

【組み合わせた機能】
1. 曜日別テーマ投稿（スポット・グッズ・イベント・サイト紹介）
2. 今日の一スポット（spots.jsonから毎日1件ずつ自動紹介）
3. イベント直前リマインド（3日以内のイベントを優先告知）
4. 天気連動（晴れ→屋外スポット、雨→室内スポット）
5. AI注記を全投稿に追加（情報誤りの免責）
"""

import json
import datetime
import hashlib
import random
import urllib.request
import urllib.error
from pathlib import Path
from openai import OpenAI

SITE_URL = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide"
DATA_DIR = Path("/home/ubuntu/daisy-kyushu-dog-guide")
OUTPUT_DIR = Path("/home/ubuntu/daily_post_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# AI注記（全投稿に追加）
AI_DISCLAIMER = "※この投稿はAIが自動生成しています。営業時間・料金・ペット可否等の情報は変更される場合があります。お出かけ前に必ず公式サイトや現地にご確認ください。"

# 曜日別テーマ
THEME_BY_WEEKDAY = {
    0: "spot",      # 月
    1: "product",   # 火
    2: "spot",      # 水
    3: "event",     # 木
    4: "spot",      # 金
    5: "product",   # 土
    6: "summary",   # 日
}

THEME_LABELS = {
    "spot": "犬連れスポット紹介",
    "product": "おすすめ犬グッズ",
    "event": "イベント告知",
    "summary": "サイト紹介",
    "weather_indoor": "雨の日おすすめスポット",
    "event_urgent": "イベント直前告知",
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
    """Open-Meteo APIで天気を取得（無料・APIキー不要）"""
    # 九州主要都市の座標
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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,precipitation_sum&timezone=Asia%2FTokyo&forecast_days=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DaisyKyushuBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            weather_code = data["daily"]["weathercode"][0]
            precipitation = data["daily"]["precipitation_sum"][0]
            # 天気コード: 0-2=晴れ、3=曇り、51-99=雨・雪
            if weather_code >= 51 or precipitation > 1.0:
                return "rain"
            elif weather_code <= 2:
                return "sunny"
            else:
                return "cloudy"
    except Exception as e:
        print(f"天気取得失敗: {e}")
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
            if "〜" in date_str:
                start_str = date_str.split("〜")[0].strip()
            else:
                start_str = date_str
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

    # 大型犬OKのスポットを優先
    good_spots = [s for s in spots
                  if s.get("largeDog") in ["可", "OK", "○", "大型犬可"]
                  and s.get("status") not in ["閉業", "ペット同伴不可"]]

    if not good_spots:
        good_spots = [s for s in spots if s.get("status") not in ["閉業", "ペット同伴不可"]]

    if prefer_indoor or weather == "rain":
        # 雨の日は室内スポットを優先
        indoor_types = ["カフェ", "レストラン", "ショッピング", "水族館", "博物館", "ホテル", "温泉"]
        indoor_spots = [s for s in good_spots
                        if any(t in (s.get("type", "") + s.get("memo", "")) for t in indoor_types)]
        if indoor_spots:
            return rng.choice(indoor_spots), "indoor"

    if weather == "sunny":
        # 晴れの日は屋外スポットを優先
        outdoor_types = ["公園", "ドッグラン", "海岸", "山", "自然", "アウトドア", "キャンプ"]
        outdoor_spots = [s for s in good_spots
                         if any(t in (s.get("type", "") + s.get("memo", "")) for t in outdoor_types)]
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
    good_products = [p for p in products
                     if safe_rating(p) >= 4.0
                     and p.get("affiliateStatus") not in ["inactive", None]
                     and p.get("affiliateStatus") != ""]
    if not good_products:
        # affiliateStatusがactiveなものを優先
        good_products = [p for p in products
                         if p.get("affiliateStatus") in ["affiliate-active", "active"]]
    if not good_products:
        good_products = products if products else []
    return rng.choice(good_products) if good_products else None


def pick_event(events):
    today = datetime.date.today()
    upcoming = []
    for e in events:
        if e.get("status") == "past":
            continue
        date_str = e.get("date", "")
        try:
            if "〜" in date_str:
                date_str = date_str.split("〜")[0].strip()
            if "-" in date_str:
                event_date = datetime.date.fromisoformat(date_str[:10])
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

    # 天気コメント
    weather_intro = ""
    if weather == "rain":
        weather_intro = "今日は雨ですね☔ 雨の日でも愛犬と楽しめるスポットをご紹介！\n\n"
    elif weather == "sunny":
        weather_intro = "今日はお出かけ日和🌞 愛犬と一緒に行きたいスポットをご紹介！\n\n"

    # 緊急イベント告知
    urgent_intro = ""
    if urgent_days is not None:
        if urgent_days == 0:
            urgent_intro = "🚨 今日開催！見逃せないドッグイベントです！\n\n"
        elif urgent_days == 1:
            urgent_intro = "⏰ 明日開催！まだ間に合います！\n\n"
        else:
            urgent_intro = f"📅 あと{urgent_days}日！直前告知です！\n\n"

    if theme in ["spot", "weather_indoor"]:
        spot_type_note = "（室内スポット）" if theme == "weather_indoor" else ""
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
サモエドのDaisyと一緒に九州を旅するコンセプトのアカウントです。

以下のスポット情報を元に、Instagramの投稿キャプションを作成してください。

スポット名: {item.get('name')}{spot_type_note}
エリア: {item.get('area')}
種別: {item.get('type')}
大型犬: {item.get('largeDog', '要確認')}
メモ: {item.get('memo', '')}
営業時間: {item.get('hours', '')}
料金: {item.get('fee', '')}

【ルール】
- 300文字以内（ハッシュタグ・注記除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- Daisyが実際に訪れた感想風に書く（一人称: Daisyが〜）
- 「要確認」「不明」の情報は書かない
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない
- 改行を適切に使う

キャプションのみ出力してください。"""

    elif theme == "product":
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。

以下の商品情報を元に、Instagramの投稿キャプションを作成してください。

商品名: {item.get('productName')}
カテゴリ: {item.get('category')}
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

イベント名: {item.get('title') or item.get('name')}
エリア: {item.get('area')}
会場: {item.get('venue', '')}
開催日: {item.get('date') or item.get('eventDate')}
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
        today = datetime.date.today()
        season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"
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

    # 天気・緊急告知のイントロを追加
    intro = urgent_intro or weather_intro
    full_caption = f"{intro}{base_caption}"

    return full_caption


def build_image_prompt(theme, item, weather="unknown"):
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"
    weather_desc = "rainy atmosphere with puddles" if weather == "rain" else "sunny bright day" if weather == "sunny" else "pleasant day"

    if theme in ["spot", "weather_indoor"]:
        name = item.get('name', '')
        area = item.get('area', '')
        spot_type = item.get('type', '')
        indoor_note = "cozy indoor" if theme == "weather_indoor" else "outdoor"
        return f"""Create a professional Japanese advertisement flyer for a dog-friendly spot in Kyushu.
Subject: A fluffy white Samoyed dog enjoying {indoor_note} activities at '{name}' in {area} ({spot_type}).
Composition: Square format, Samoyed dog as main subject, beautiful Kyushu scenery background, {weather_desc}.
Style: Bright, cheerful, modern Japanese advertisement style, {season} colors, clean typography.
Text/content to render: Large title '{name}' at top, area badge '{area}', '大型犬OK' badge, '犬連れOK' badge.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram flyer design.
Avoid: blurry text, cluttered layout."""

    elif theme == "product":
        product_name = item.get('productName', '')
        category = item.get('category', '')
        return f"""Create a professional Japanese advertisement flyer for a dog product.
Subject: A fluffy white Samoyed dog using or near '{product_name}' ({category}).
Composition: Square format, Samoyed dog as main subject, product displayed prominently, clean background.
Style: Bright, clean, modern Japanese advertisement style, warm colors, professional product photography feel.
Text/content to render: Large title '{product_name}', category badge '{category}', '楽天で購入' CTA button, '大型犬おすすめ' badge.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram flyer design.
Avoid: blurry text, cluttered layout."""

    elif theme in ["event", "event_urgent"]:
        event_name = item.get('title') or item.get('name', '')
        area = item.get('area', '')
        date_str = item.get('date') or item.get('eventDate', '')
        urgency = "URGENT - happening soon!" if theme == "event_urgent" else ""
        return f"""Create a professional Japanese event announcement poster. {urgency}
Subject: A fluffy white Samoyed dog at a lively dog event in Kyushu.
Composition: Square format, festive atmosphere, event details prominently displayed.
Style: Bright, energetic, modern Japanese event poster style, vibrant colors.
Text/content to render: Large title '{event_name}', date '{date_str}', location '{area}', 'イベント開催！' announcement.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram event poster design.
Avoid: blurry text, cluttered layout."""

    else:  # summary
        return f"""Create a professional Japanese advertisement flyer for a dog-friendly travel guide website.
Subject: A fluffy white Samoyed dog posing happily in front of beautiful Kyushu scenery.
Composition: Square format, Samoyed as main subject, Kyushu landscape background, clean layout, {weather_desc}.
Style: Bright, cheerful, modern Japanese advertisement style, {season} colors, clean typography.
Text/content to render: Large title '九州犬連れガイド', '455スポット掲載', '大型犬OK情報満載', site URL at bottom.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram flyer design.
Avoid: blurry text, cluttered layout."""


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
    today = datetime.date.today()
    weekday = today.weekday()
    base_theme = THEME_BY_WEEKDAY[weekday]

    spots, products, events = load_data()

    # 天気を取得
    weather = get_weather("福岡")
    print(f"今日の天気: {weather}")

    # 直前イベントを確認
    urgent_event = check_urgent_event(events)
    urgent_days = urgent_event[0] if urgent_event else None
    urgent_event_data = urgent_event[1] if urgent_event else None

    # テーマを決定（優先順位: 緊急イベント > 天気連動 > 曜日テーマ）
    theme = base_theme
    item = None
    weather_note = ""

    if urgent_days is not None and urgent_days <= 1:
        # 当日・翌日のイベントは最優先で告知
        theme = "event_urgent"
        item = urgent_event_data
        print(f"緊急イベント告知モード: {item.get('title') or item.get('name')} (あと{urgent_days}日)")
    elif base_theme == "spot" and weather == "rain":
        # 雨の日は室内スポット特集に切り替え
        theme = "weather_indoor"
        item, _ = pick_spot(spots, weather="rain", prefer_indoor=True)
        weather_note = "雨の日室内スポット"
        print(f"雨の日モード: 室内スポット「{item.get('name')}」を選択")
    elif base_theme == "spot" and weather == "sunny":
        item, _ = pick_spot(spots, weather="sunny")
        print(f"晴れモード: 屋外スポット「{item.get('name')}」を選択")
    elif base_theme == "spot":
        item, _ = pick_spot(spots)
        print(f"通常モード: スポット「{item.get('name')}」を選択")
    elif base_theme == "product":
        item = pick_product(products)
        if not item:
            # 商品データがない場合はスポットに切り替え
            theme = "spot"
            item, _ = pick_spot(spots, weather)
        print(f"商品モード: 「{item.get('productName', item.get('name', ''))}」を選択")
    elif base_theme == "event":
        item = pick_event(events)
        if not item:
            theme = "spot"
            item, _ = pick_spot(spots, weather)
        print(f"イベントモード: 「{item.get('title') or item.get('name', '')}」を選択")
    else:  # summary
        item = None
        print("サマリーモード")

    # キャプション生成
    client = OpenAI()
    caption = generate_caption(theme, item or {}, client, weather=weather, urgent_days=urgent_days)

    # AI注記を追加
    full_caption = f"{caption}\n\n{AI_DISCLAIMER}"

    # リンク
    link = get_item_link(theme, item or {})

    # 画像プロンプト
    image_prompt = build_image_prompt(theme, item or {}, weather=weather)

    # 楽天Room用投稿文（商品テーマのみ）
    rakuten_room_comment = None
    rakuten_room_url = None
    if theme == "product" and item:
        product_name = item.get('productName', '')
        category = item.get('category', '')
        memo = item.get('memo', '')
        prompt = f"""楽天ROOMの投稿コメントを作成してください。
商品名: {product_name}
カテゴリ: {category}
メモ: {memo}
【ルール】100文字以内、大型犬・サモエドとの旅行に役立つ観点、絵文字1〜2個、自然な口コミ風
コメントのみ出力してください。"""
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        rakuten_room_comment = resp.choices[0].message.content.strip()
        rakuten_room_url = item.get('rakutenAffiliateUrl') or item.get('normalUrl') or ''

    # 出力データ
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
        "image_prompt": image_prompt,
        "image_path": str(OUTPUT_DIR / f"post_{today.isoformat()}.png"),
        "rakuten_room_comment": rakuten_room_comment,
        "rakuten_room_url": rakuten_room_url,
    }

    output_file = OUTPUT_DIR / f"post_{today.isoformat()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


if __name__ == "__main__":
    main()

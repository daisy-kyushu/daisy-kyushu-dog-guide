#!/usr/bin/env python3
"""
Daisy九州犬連れガイド - 毎日Instagram自動投稿スクリプト（メイン）
毎朝8時に実行。投稿文・画像を生成してユーザーに確認を求める。
"""

import json
import os
import sys
import subprocess
import datetime
import hashlib
import random
import base64
import requests
from pathlib import Path
from openai import OpenAI

# ===== 設定 =====
SITE_URL = "https://daisy-kyushu-dog-guide.pages.dev"
DATA_DIR = Path("/home/ubuntu/daisy-kyushu-dog-guide")
OUTPUT_DIR = Path("/home/ubuntu/daily_post_output")
OUTPUT_DIR.mkdir(exist_ok=True)

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
}

HASHTAGS = {
    "spot": "#犬連れ旅行 #九州犬連れ #犬とお出かけ #サモエド #大型犬 #ドッグフレンドリー #北九州 #福岡犬連れ #犬旅",
    "product": "#犬グッズ #大型犬グッズ #サモエド #犬のいる生活 #楽天 #犬用品 #愛犬グッズ #ペットグッズ #犬連れ旅行",
    "event": "#犬イベント #九州犬イベント #ドッグイベント #犬連れ #サモエド #大型犬 #北九州 #福岡 #犬とお出かけ",
    "summary": "#犬連れ旅行 #九州犬連れ #サモエド #大型犬 #ドッグフレンドリー #犬旅 #犬のいる生活 #九州旅行 #犬とお出かけ",
}


def load_data():
    with open(DATA_DIR / "spots.json") as f:
        spots = json.load(f)
    with open(DATA_DIR / "products.json") as f:
        products = json.load(f)
    with open(DATA_DIR / "events.json") as f:
        events = json.load(f)
    return spots, products, events


def get_today_seed():
    today = datetime.date.today().isoformat()
    return int(hashlib.md5(today.encode()).hexdigest(), 16) % (2**31)


def pick_spot(spots):
    seed = get_today_seed()
    rng = random.Random(seed)
    good_spots = [s for s in spots if s.get("largeDog") in ["可", "OK", "○", "大型犬可"]
                  and s.get("status") not in ["閉業", "要確認のみ"]]
    if not good_spots:
        good_spots = [s for s in spots if s.get("status") not in ["閉業"]]
    return rng.choice(good_spots)


def pick_product(products):
    seed = get_today_seed() + 1
    rng = random.Random(seed)
    good_products = [p for p in products if p.get("rating", 0) >= 4.0
                     and p.get("affiliateStatus") != "inactive"]
    if not good_products:
        good_products = products
    return rng.choice(good_products)


def pick_event(events):
    today = datetime.date.today()
    upcoming = []
    for e in events:
        date_str = e.get("eventDate") or e.get("date", "")
        try:
            if "〜" in date_str:
                date_str = date_str.split("〜")[0]
            event_date = datetime.date.fromisoformat(date_str[:10])
            if today <= event_date <= today + datetime.timedelta(days=60):
                upcoming.append((event_date, e))
        except:
            pass
    if not upcoming:
        return events[0] if events else None
    upcoming.sort(key=lambda x: x[0])
    return upcoming[0][1]


def generate_caption(theme, item, client):
    if theme == "spot":
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
サモエドのDaisyと一緒に九州を旅するコンセプトのアカウントです。

以下のスポット情報を元に、Instagramの投稿キャプションを作成してください。

スポット名: {item.get('name')}
エリア: {item.get('area')}
種別: {item.get('type')}
大型犬: {item.get('largeDog', '要確認')}
メモ: {item.get('memo', '')}
営業時間: {item.get('hours', '要確認')}
料金: {item.get('fee', '要確認')}

【ルール】
- 300文字以内（ハッシュタグ除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- Daisyが実際に訪れた感想風に書く（一人称: Daisyが〜）
- 「要確認」の情報は書かない
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない
- 改行を適切に使う

キャプションのみ出力してください。"""

    elif theme == "product":
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。

以下の商品情報を元に、Instagramの投稿キャプションを作成してください。

商品名: {item.get('productName')}
カテゴリ: {item.get('category')}
対象: {item.get('target')}
メモ: {item.get('memo', '')}
評価: {item.get('rating', '')}点（{item.get('reviewCount', '')}件）

【ルール】
- 300文字以内（ハッシュタグ除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- 大型犬・サモエドとの旅行に役立つ観点で紹介
- 具体的なメリットを1〜2つ書く
- 「要確認」の情報は書かない
- 最後に「楽天で購入できます🛒 詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない
- 改行を適切に使う

キャプションのみ出力してください。"""

    elif theme == "event":
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。

以下のイベント情報を元に、Instagramの投稿キャプションを作成してください。

イベント名: {item.get('title') or item.get('name')}
エリア: {item.get('area')}
会場: {item.get('venue', '')}
開催日: {item.get('date') or item.get('eventDate')}
入場料: {item.get('fee', '要確認')}
概要: {item.get('description', '')}

【ルール】
- 300文字以内（ハッシュタグ除く）
- 最初の1行は短いキャッチコピー（20文字以内）
- 開催日・場所は必ず明記する
- 「要確認」の情報は省く
- 最後に「詳しくはプロフのリンクから🐾」
- ハッシュタグは含めない
- 改行を適切に使う

キャプションのみ出力してください。"""

    else:  # summary
        prompt = f"""あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。

今週の投稿まとめ・サイト紹介のInstagramキャプションを作成してください。

サイト概要:
- 九州の犬連れスポット300件以上掲載
- 大型犬・サモエド向け情報に特化
- イベント情報・おすすめグッズも掲載

【ルール】
- 300文字以内（ハッシュタグ除く）
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
    return response.choices[0].message.content.strip()


def generate_ad_image(theme, item, client, output_path):
    """DALL-E 3で広告風チラシ画像を生成"""
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"

    if theme == "spot":
        name = item.get('name', '')
        area = item.get('area', '')
        spot_type = item.get('type', '')
        image_prompt = f"""Create a professional Japanese advertisement flyer for a dog-friendly spot in Kyushu.
Subject: A fluffy white Samoyed dog enjoying outdoor activities at '{name}' in {area} ({spot_type}).
Composition: Square format, Samoyed dog as main subject, beautiful Kyushu scenery background, Japanese text overlay areas.
Style: Bright, cheerful, modern Japanese advertisement style, {season} colors, clean typography.
Text/content to render: Large title '{name}' at top, area badge '{area}', '大型犬OK' badge, '犬連れOK' badge.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram flyer design.
Avoid: blurry text, cluttered layout."""

    elif theme == "product":
        product_name = item.get('productName', '')
        category = item.get('category', '')
        image_prompt = f"""Create a professional Japanese advertisement flyer for a dog product.
Subject: A fluffy white Samoyed dog using or near '{product_name}' ({category}).
Composition: Square format, Samoyed dog as main subject, product displayed prominently, clean background.
Style: Bright, clean, modern Japanese advertisement style, warm colors, professional product photography feel.
Text/content to render: Large title '{product_name}', category badge '{category}', '楽天で購入' CTA button, '大型犬おすすめ' badge.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram flyer design.
Avoid: blurry text, cluttered layout."""

    elif theme == "event":
        event_name = item.get('title') or item.get('name', '')
        area = item.get('area', '')
        date = item.get('date') or item.get('eventDate', '')
        image_prompt = f"""Create a professional Japanese event announcement poster.
Subject: A fluffy white Samoyed dog at a lively dog event in Kyushu.
Composition: Square format, festive atmosphere, event details prominently displayed.
Style: Bright, energetic, modern Japanese event poster style, vibrant colors.
Text/content to render: Large title '{event_name}', date '{date}', location '{area}', 'イベント開催！' announcement.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram event poster design.
Avoid: blurry text, cluttered layout."""

    else:  # summary
        image_prompt = f"""Create a professional Japanese advertisement flyer for a dog-friendly travel guide website.
Subject: A fluffy white Samoyed dog posing happily in front of beautiful Kyushu scenery.
Composition: Square format, Samoyed as main subject, Kyushu landscape background, clean layout.
Style: Bright, cheerful, modern Japanese advertisement style, {season} colors, clean typography.
Text/content to render: Large title '九州犬連れガイド', '300スポット掲載', '大型犬OK情報満載', site URL at bottom.
Constraints: 1:1 aspect ratio, Japanese text must be readable, professional Instagram flyer design.
Avoid: blurry text, cluttered layout."""

    # gpt-image-2で画像生成
    response = client.images.generate(
        model="gpt-image-2",
        prompt=image_prompt,
        size="1024x1024",
        n=1,
    )
    # base64デコードして保存
    image_data = response.data[0].b64_json
    import base64
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
    # CDN URLを抽出
    for line in result.stdout.split("\n"):
        if "CDN URL:" in line:
            return line.split("CDN URL:")[1].strip()
    raise Exception("CDN URL not found in upload output")


def get_item_link(theme, item):
    if theme == "spot":
        spot_id = item.get('id', '')
        return f"{SITE_URL}/spots.html#{spot_id}" if spot_id else SITE_URL
    elif theme == "product":
        return item.get('rakutenAffiliateUrl') or item.get('normalUrl') or SITE_URL
    elif theme == "event":
        return item.get('officialUrl') or SITE_URL
    else:
        return SITE_URL


def main():
    print("=" * 60)
    print("🐾 Daisy九州犬連れガイド - 本日の投稿案を生成中...")
    print("=" * 60)

    today = datetime.date.today()
    weekday = today.weekday()
    theme = THEME_BY_WEEKDAY[weekday]
    theme_label = THEME_LABELS[theme]

    print(f"\n📅 {today.strftime('%Y年%m月%d日')} ({['月','火','水','木','金','土','日'][weekday]}曜日)")
    print(f"📌 テーマ: {theme_label}")

    spots, products, events = load_data()

    if theme == "spot":
        item = pick_spot(spots)
        item_name = item.get('name', '')
        print(f"✅ スポット: {item_name} ({item.get('area')})")
    elif theme == "product":
        item = pick_product(products)
        item_name = item.get('productName', '')
        print(f"✅ 商品: {item_name}")
    elif theme == "event":
        item = pick_event(events)
        if item:
            item_name = item.get('title') or item.get('name', '')
            print(f"✅ イベント: {item_name}")
        else:
            print("⚠️ 近日イベントなし → スポット投稿に切り替え")
            theme = "spot"
            item = pick_spot(spots)
            item_name = item.get('name', '')
    else:
        item = None
        item_name = "サイト紹介"

    client = OpenAI()

    # 投稿文生成
    print("\n📝 投稿文を生成中...")
    caption = generate_caption(theme, item or {}, client)
    hashtags = HASHTAGS[theme]
    full_caption = f"{caption}\n\n{hashtags}"

    # 画像生成
    print("🎨 広告風チラシ画像を生成中...")
    image_path = OUTPUT_DIR / f"post_{today.isoformat()}.png"
    generate_ad_image(theme, item or {}, client, image_path)
    print(f"✅ 画像生成完了: {image_path}")

    # 画像アップロード
    print("☁️  画像をアップロード中...")
    image_cdn_url = upload_image(image_path)
    print(f"✅ アップロード完了: {image_cdn_url}")

    # リンク
    link = get_item_link(theme, item or {})

    # 結果を保存
    output = {
        "date": today.isoformat(),
        "weekday": ['月','火','水','木','金','土','日'][weekday],
        "theme": theme,
        "theme_label": theme_label,
        "item_name": item_name,
        "caption": caption,
        "hashtags": hashtags,
        "full_caption": full_caption,
        "link": link,
        "image_path": str(image_path),
        "image_cdn_url": image_cdn_url,
    }

    output_file = OUTPUT_DIR / f"post_{today.isoformat()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ユーザーへの確認メッセージ
    print("\n" + "=" * 60)
    print("📱 本日のInstagram投稿案")
    print("=" * 60)
    print(f"\n【テーマ】{theme_label}：{item_name}")
    print(f"\n【キャプション】\n{full_caption}")
    print(f"\n【リンク】{link}")
    print(f"\n【画像】{image_cdn_url}")
    print(f"\n💾 保存先: {output_file}")

    return output


if __name__ == "__main__":
    result = main()
    print("\n✨ 投稿案の生成が完了しました！")
    print("上記の内容でInstagramに投稿してよければ「投稿する」とお伝えください。")
    print("修正がある場合は内容をお知らせください。")

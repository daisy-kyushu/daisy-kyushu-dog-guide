#!/usr/bin/env python3
"""
carousel_post.py
週1回（月曜日）に「九州犬連れスポット5選」カルーセル投稿を自動生成・投稿するスクリプト。
保存率を高めるため「まとめ系」コンテンツを作成する。
"""

import json
import random
import datetime
import subprocess
import os
import sys
import pathlib
import tempfile
import base64
import urllib.request

# ===== 設定 =====
BASE_DIR = pathlib.Path(__file__).parent
OUTPUT_DIR = pathlib.Path("/home/ubuntu/daily_post_output")
OUTPUT_DIR.mkdir(exist_ok=True)

SITE_URL = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # 環境変数から取得

AI_NOTE = "※この投稿はAIが自動生成しています。営業時間・料金・ペット可否等の情報は変更される場合があります。お出かけ前に必ず公式サイトや現地にご確認ください。"

HASHTAGS = (
    "#犬のいる生活 #犬連れ旅行 #ペットと旅行 #サモエド "
    "#九州旅行 #九州犬連れ #大型犬おでかけ #わんこ旅 #犬連れスポット "
    "#サモエド部 #白い犬 #もふもふ犬 #大型犬のいる生活 #犬連れ九州 #daisy_samoyed1217 "
    "#保存してね #犬連れおすすめ #週末おでかけ #ドッグフレンドリー"
)

# テーマローテーション（週ごとに変える）
WEEKLY_THEMES = [
    {"label": "福岡県 犬連れスポット5選", "area_filter": "福岡", "emoji": "🌸"},
    {"label": "大分県 犬連れスポット5選", "area_filter": "大分", "emoji": "♨️"},
    {"label": "熊本県 犬連れスポット5選", "area_filter": "熊本", "emoji": "🏯"},
    {"label": "長崎県 犬連れスポット5選", "area_filter": "長崎", "emoji": "⛵"},
    {"label": "宮崎県 犬連れスポット5選", "area_filter": "宮崎", "emoji": "🌴"},
    {"label": "鹿児島県 犬連れスポット5選", "area_filter": "鹿児島", "emoji": "🌋"},
    {"label": "佐賀県 犬連れスポット5選", "area_filter": "佐賀", "emoji": "🎈"},
    {"label": "九州 ドッグカフェ5選", "area_filter": None, "category_filter": "カフェ", "emoji": "☕"},
    {"label": "九州 ドッグラン5選", "area_filter": None, "category_filter": "ドッグラン", "emoji": "🐕"},
    {"label": "九州 犬連れ宿泊5選", "area_filter": None, "category_filter": "ホテル", "emoji": "🏨"},
]


def load_spots():
    with open(BASE_DIR / "spots.json", encoding="utf-8") as f:
        return json.load(f)


def pick_carousel_spots(spots, theme):
    """テーマに合ったスポットを5件選ぶ"""
    area_filter = theme.get("area_filter")
    cat_filter = theme.get("category_filter")

    filtered = []
    for s in spots:
        if s.get("dogFriendly") not in ["ok", "conditional_ok"]:
            continue
        area = s.get("area", "") or ""
        pref = s.get("prefecture", "") or ""
        cat = s.get("category", "") or ""
        name = s.get("name", "") or ""

        if area_filter:
            if area_filter not in area and area_filter not in pref and area_filter not in name:
                continue
        if cat_filter:
            if cat_filter.lower() not in cat.lower():
                continue

        filtered.append(s)

    if len(filtered) < 3:
        # フォールバック: 全スポットからランダム
        filtered = [s for s in spots if s.get("dogFriendly") in ["ok", "conditional_ok"]]

    # スコアリング（URL・営業時間・説明があるものを優先）
    def score(s):
        sc = 0
        if s.get("url"): sc += 3
        if s.get("hours"): sc += 2
        if s.get("description"): sc += 2
        if s.get("lat") and s.get("lng"): sc += 1
        if s.get("fee"): sc += 1
        return sc

    filtered.sort(key=score, reverse=True)
    top = filtered[:20]
    return random.sample(top, min(5, len(top)))


def generate_carousel_image(spot, index, total, theme):
    """各スポットのカルーセル画像をAI生成してCDN URLを返す"""
    name = spot.get("name", "スポット")
    area = spot.get("area", spot.get("prefecture", "九州"))
    category = spot.get("category", "")
    description = spot.get("description", "")
    hours = spot.get("hours", "")
    fee = spot.get("fee", "")
    dog_friendly = spot.get("dogFriendly", "ok")

    dog_label = "🐾 犬連れOK" if dog_friendly == "ok" else "🐾 条件付きOK"

    # 画像生成プロンプト
    prompt = (
        f"Instagram carousel card {index} of {total}. "
        f"Beautiful Japanese dog-friendly travel spot introduction card. "
        f"Spot name: {name} in {area}. Category: {category}. "
        f"Vibrant, warm, inviting atmosphere with a white Samoyed dog in the scene. "
        f"Card layout: large scenic photo background with semi-transparent overlay at bottom. "
        f"Text overlay shows: spot number '{index}/{total}', spot name in Japanese '{name}', "
        f"area '{area}', dog-friendly badge '{dog_label}'. "
        f"Color scheme: warm coral and cream tones. "
        f"Instagram-ready 4:5 ratio, professional photography style, "
        f"soft natural lighting, cheerful and welcoming mood."
    )

    save_path = OUTPUT_DIR / f"carousel_{datetime.date.today().isoformat()}_{index}.png"

    try:
        # OpenAI DALL-E経由で画像生成
        import openai
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1280",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url

        # 画像をダウンロード
        urllib.request.urlretrieve(image_url, save_path)

        # S3にアップロードしてCDN URLを取得
        result = subprocess.run(
            ["manus-upload-file", str(save_path)],
            capture_output=True, text=True, timeout=60
        )
        for line in result.stdout.splitlines():
            if line.startswith("https://"):
                return line.strip()
        return image_url  # フォールバック

    except Exception as e:
        print(f"   ⚠️ 画像生成エラー ({name}): {e}")
        # フォールバック: OGP画像
        return f"{SITE_URL}/assets/og-image.png"


def build_caption(spots, theme):
    """カルーセル投稿のキャプションを生成"""
    today = datetime.date.today()
    emoji = theme.get("emoji", "🐾")
    label = theme["label"]

    lines = [
        f"{emoji} 保存して使って！{label} {emoji}",
        "",
        "旅行前に保存しておくと便利です✨",
        "",
    ]

    for i, spot in enumerate(spots, 1):
        name = spot.get("name", "スポット")
        area = spot.get("area", spot.get("prefecture", ""))
        hours = spot.get("hours", "")
        fee = spot.get("fee", "")
        dog = "🐾 犬連れOK" if spot.get("dogFriendly") == "ok" else "🐾 条件付きOK"

        lines.append(f"【{i}】{name}（{area}）")
        lines.append(f"　{dog}")
        if hours:
            lines.append(f"　🕐 {hours}")
        if fee:
            lines.append(f"　💰 {fee}")
        lines.append("")

    lines.append(f"詳しくはプロフィールのリンクから👆")
    lines.append(f"🔗 {SITE_URL}")
    lines.append("")
    lines.append(AI_NOTE)

    return "\n".join(lines)


def post_carousel_to_instagram(media_urls, caption):
    """Instagram MCPにカルーセル投稿する"""
    media_items = [{"type": "image", "media_url": url} for url in media_urls]

    payload = {
        "type": "post",
        "caption": caption,
        "media": media_items
    }

    input_json = json.dumps(payload, ensure_ascii=False)

    print(f"   📤 Instagram カルーセル投稿中（{len(media_items)}枚）...")
    result = subprocess.run(
        ["manus-mcp-cli", "tool", "call", "create_instagram",
         "--server", "instagram",
         "--input", input_json],
        capture_output=True, text=True, timeout=180
    )

    if result.returncode == 0:
        print("   ✅ カルーセル投稿成功！")
        return True, result.stdout
    else:
        print(f"   ❌ 投稿失敗: {result.stderr[:300]}")
        return False, result.stderr


def main():
    print("=" * 60)
    print("🎠 Daisy九州犬連れガイド - カルーセル投稿生成中...")
    print("=" * 60)

    today = datetime.date.today()
    # 週番号でテーマをローテーション
    week_num = today.isocalendar()[1]
    theme = WEEKLY_THEMES[week_num % len(WEEKLY_THEMES)]

    print(f"\n📅 {today.strftime('%Y年%m月%d日')} - 今週のテーマ: {theme['label']}")

    spots = load_spots()
    selected_spots = pick_carousel_spots(spots, theme)

    print(f"\n📍 選定スポット ({len(selected_spots)}件):")
    for i, s in enumerate(selected_spots, 1):
        print(f"   {i}. {s.get('name')} ({s.get('area', s.get('prefecture', ''))})")

    # 各スポットの画像を生成
    print("\n🎨 カルーセル画像を生成中...")
    media_urls = []
    for i, spot in enumerate(selected_spots, 1):
        print(f"   [{i}/{len(selected_spots)}] {spot.get('name')} の画像を生成中...")
        url = generate_carousel_image(spot, i, len(selected_spots), theme)
        media_urls.append(url)
        print(f"   → {url[:80]}...")

    # キャプション生成
    caption = build_caption(selected_spots, theme)
    full_caption = f"{caption}\n\n{HASHTAGS}"

    print(f"\n📝 キャプション（先頭100文字）:\n{full_caption[:100]}...")

    # 結果を保存
    output = {
        "date": today.isoformat(),
        "type": "carousel",
        "theme": theme["label"],
        "spots": [s.get("name") for s in selected_spots],
        "media_urls": media_urls,
        "caption": full_caption,
    }
    output_file = OUTPUT_DIR / f"carousel_{today.isoformat()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Instagram投稿
    success, result_msg = post_carousel_to_instagram(media_urls, full_caption)
    output["instagram_posted"] = success
    output["instagram_result"] = result_msg[:300]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 保存先: {output_file}")
    print("\n✨ カルーセル投稿完了！")
    return output


if __name__ == "__main__":
    main()

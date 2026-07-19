#!/usr/bin/env python3
"""
stories_post.py
週3回（火・木・土）にストーリーズを自動投稿するスクリプト。
エンゲージメントを高めるため「アンケート風」「行きたい！」を促す画像を作成する。
（Instagram APIはアンケートスタンプ非対応のため、画像内にアンケートデザインを組み込む）
"""

import json
import random
import datetime
import subprocess
import os
import pathlib
import urllib.request

# ===== 設定 =====
BASE_DIR = pathlib.Path(__file__).parent
OUTPUT_DIR = pathlib.Path("/home/ubuntu/daily_post_output")
OUTPUT_DIR.mkdir(exist_ok=True)

SITE_URL = "https://daisy-kyushu.github.io/daisy-kyushu-dog-guide"

AI_NOTE = "※AI自動投稿。情報は変更される場合があります。必ず公式サイトでご確認ください。"

# ストーリーズのテーマパターン
STORY_THEMES = [
    {
        "type": "poll",
        "question": "次の週末、どっちに行きたい？",
        "option_a": "🏖️ 海・ビーチ",
        "option_b": "🌿 山・森",
        "cta": "コメントで教えてね！",
    },
    {
        "type": "poll",
        "question": "愛犬とのお出かけ、何が好き？",
        "option_a": "☕ ドッグカフェ",
        "option_b": "🐕 ドッグラン",
        "cta": "どっちも好き！という方はコメントで！",
    },
    {
        "type": "poll",
        "question": "九州で行ってみたい県は？",
        "option_a": "🌸 福岡・長崎",
        "option_b": "♨️ 大分・熊本",
        "cta": "行ったことある場所もコメントで教えて！",
    },
    {
        "type": "poll",
        "question": "犬連れ旅行で一番困ること？",
        "option_a": "🏨 宿探し",
        "option_b": "🍽️ 食事場所",
        "cta": "他にも困ることがあればコメントで！",
    },
    {
        "type": "spot_highlight",
        "cta": "詳しくはプロフィールのリンクから👆",
    },
    {
        "type": "event_reminder",
        "cta": "イベント情報はプロフィールのリンクから👆",
    },
    {
        "type": "tip",
        "tips": [
            "夏の犬連れ旅行は早朝・夕方がおすすめ🌅",
            "ドッグランは事前に登録が必要な場合があります📋",
            "愛犬の水分補給を忘れずに💧",
            "ペット可の宿は早めの予約がおすすめ🏨",
            "犬連れNGの施設もあるので事前確認を✅",
        ],
        "cta": "他にも役立つ情報はプロフィールのリンクから！",
    },
]


def load_data():
    with open(BASE_DIR / "spots.json", encoding="utf-8") as f:
        spots = json.load(f)
    events_path = BASE_DIR / "events.json"
    events = []
    if events_path.exists():
        with open(events_path, encoding="utf-8") as f:
            events = json.load(f)
    return spots, events


def pick_story_theme(spots, events, weekday):
    """曜日に合わせてストーリーズテーマを選択"""
    today = datetime.date.today()

    # 直近3日以内のイベントがあればイベントリマインダー優先
    for ev in events:
        date_str = ev.get("date", "")
        if not date_str:
            continue
        try:
            ev_date = datetime.date.fromisoformat(date_str[:10])
            days_until = (ev_date - today).days
            if 0 <= days_until <= 3:
                return {"type": "event_reminder", "event": ev, "cta": "詳しくはプロフィールのリンクから👆"}
        except Exception:
            pass

    # 曜日別テーマ
    if weekday == 1:  # 火曜: アンケート
        polls = [t for t in STORY_THEMES if t["type"] == "poll"]
        return random.choice(polls)
    elif weekday == 3:  # 木曜: スポットハイライト
        ok_spots = [s for s in spots if s.get("dogFriendly") in ["ok", "conditional_ok"]]
        spot = random.choice(ok_spots) if ok_spots else None
        return {"type": "spot_highlight", "spot": spot, "cta": "詳しくはプロフィールのリンクから👆"}
    elif weekday == 5:  # 土曜: 豆知識・Tips
        tips = [t for t in STORY_THEMES if t["type"] == "tip"]
        return random.choice(tips)
    else:
        return random.choice(STORY_THEMES)


def generate_story_image(theme, today):
    """ストーリーズ画像をAI生成してCDN URLを返す"""
    story_type = theme.get("type")

    if story_type == "poll":
        prompt = (
            f"Instagram Story image with poll design. "
            f"Beautiful background: Japanese nature scene with a white Samoyed dog. "
            f"Overlay design: "
            f"Question text at top: '{theme['question']}' in Japanese. "
            f"Two large rounded buttons below: "
            f"Button A (left, coral/pink): '{theme['option_a']}' "
            f"Button B (right, mint/teal): '{theme['option_b']}'. "
            f"Small text at bottom: '{theme['cta']}'. "
            f"Warm, cheerful colors. Instagram Story 9:16 ratio. "
            f"Semi-transparent dark overlay for text readability. "
            f"Cute, engaging design that encourages interaction."
        )
    elif story_type == "spot_highlight":
        spot = theme.get("spot", {})
        name = spot.get("name", "九州の犬連れスポット") if spot else "九州の犬連れスポット"
        area = spot.get("area", "九州") if spot else "九州"
        prompt = (
            f"Instagram Story image for dog-friendly spot highlight. "
            f"Beautiful Japanese travel scene with a white Samoyed dog. "
            f"Spot name: '{name}' in {area}. "
            f"Text overlay: '今日のおすすめスポット' at top, spot name large in center, "
            f"'🐾 犬連れOK' badge, area name, CTA '{theme['cta']}' at bottom. "
            f"Vibrant, warm photography style. Instagram Story 9:16 ratio. "
            f"Inviting, travel-inspiring mood."
        )
    elif story_type == "event_reminder":
        event = theme.get("event", {})
        ev_name = event.get("title") or event.get("name", "ドッグイベント")
        ev_date = event.get("date", "")
        prompt = (
            f"Instagram Story image for dog event reminder. "
            f"Exciting event announcement design. "
            f"Event: '{ev_name}'. Date: '{ev_date}'. "
            f"White Samoyed dog excited in the scene. "
            f"Text: '🚨 イベント情報' at top, event name large, date, "
            f"'詳しくはリンクから' at bottom. "
            f"Energetic, eye-catching design. Instagram Story 9:16 ratio. "
            f"Bright colors, festive atmosphere."
        )
    elif story_type == "tip":
        tips_list = theme.get("tips", [])
        tip = random.choice(tips_list) if tips_list else "犬連れ旅行を楽しもう！"
        theme["selected_tip"] = tip
        prompt = (
            f"Instagram Story image for dog travel tip. "
            f"Clean, informative design with white Samoyed dog. "
            f"Text overlay: '🐾 犬連れ旅行のヒント' at top, "
            f"tip text large in center: '{tip}'. "
            f"'{theme['cta']}' at bottom. "
            f"Soft, friendly colors. Instagram Story 9:16 ratio. "
            f"Educational but fun and approachable design."
        )
    else:
        prompt = (
            "Instagram Story image for dog-friendly travel in Kyushu Japan. "
            "White Samoyed dog in beautiful Japanese scenery. "
            "Warm, inviting atmosphere. Instagram Story 9:16 ratio."
        )

    save_path = OUTPUT_DIR / f"story_{today.isoformat()}.png"

    try:
        import openai
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1792",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        urllib.request.urlretrieve(image_url, save_path)

        result = subprocess.run(
            ["manus-upload-file", str(save_path)],
            capture_output=True, text=True, timeout=60
        )
        for line in result.stdout.splitlines():
            if line.startswith("https://"):
                return line.strip(), theme

        return image_url, theme

    except Exception as e:
        print(f"   ⚠️ ストーリーズ画像生成エラー: {e}")
        return f"{SITE_URL}/assets/og-image.png", theme


def post_story_to_instagram(image_url):
    """Instagram MCPにストーリーズ投稿する"""
    payload = {
        "type": "story",
        "media": [{"type": "image", "media_url": image_url}]
    }

    input_json = json.dumps(payload, ensure_ascii=False)

    print("   📤 Instagram ストーリーズ投稿中...")
    result = subprocess.run(
        ["manus-mcp-cli", "tool", "call", "create_instagram",
         "--server", "instagram",
         "--input", input_json],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode == 0:
        print("   ✅ ストーリーズ投稿成功！")
        return True, result.stdout
    else:
        print(f"   ❌ 投稿失敗: {result.stderr[:300]}")
        return False, result.stderr


def main():
    print("=" * 60)
    print("📱 Daisy九州犬連れガイド - ストーリーズ投稿生成中...")
    print("=" * 60)

    today = datetime.date.today()
    weekday = today.weekday()

    print(f"\n📅 {today.strftime('%Y年%m月%d日')} ({['月','火','水','木','金','土','日'][weekday]}曜日)")

    spots, events = load_data()
    theme = pick_story_theme(spots, events, weekday)

    print(f"\n📌 ストーリーズテーマ: {theme['type']}")

    # 画像生成
    print("\n🎨 ストーリーズ画像を生成中...")
    image_url, theme = generate_story_image(theme, today)
    print(f"   → {image_url[:80]}...")

    # 結果を保存
    output = {
        "date": today.isoformat(),
        "type": "story",
        "theme": theme,
        "image_url": image_url,
    }
    output_file = OUTPUT_DIR / f"story_{today.isoformat()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Instagram投稿
    success, result_msg = post_story_to_instagram(image_url)
    output["instagram_posted"] = success
    output["instagram_result"] = result_msg[:300]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 保存先: {output_file}")
    print("\n✨ ストーリーズ投稿完了！")
    return output


if __name__ == "__main__":
    main()

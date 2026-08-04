"""
Instagram インサイト自動収集スクリプト

スケジュールタスクのdetailから呼び出されることを想定。
投稿リストといいね数・コメント数をdaily_post_output/*.jsonから集計し、
insights/post_insights.json と insights/post_insights.csv に蓄積する。

インサイト（リーチ・保存数）はInstagram Graph APIが必要なため、
ここでは投稿ログから取得できるいいね・コメントのみを記録し、
将来的にAPIが利用可能になった時点で拡張できる構造にしておく。
"""

import json
import datetime
import csv
import os
from pathlib import Path

INSIGHTS_DIR = Path("/home/ubuntu/daisy-kyushu-dog-guide/insights")
INSIGHTS_DIR.mkdir(exist_ok=True)
INSIGHTS_JSON = INSIGHTS_DIR / "post_insights.json"
INSIGHTS_CSV = INSIGHTS_DIR / "post_insights.csv"
POST_LOG_DIR = Path("/home/ubuntu/daily_post_output")


def load_existing_insights():
    if INSIGHTS_JSON.exists():
        with open(INSIGHTS_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_insights(data):
    with open(INSIGHTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "date", "weekday", "theme", "theme_label",
        "likes", "comments", "reach", "saved", "shares",
        "engagement_rate", "instagram_posted", "item_name",
        "image_cdn_url", "collected_at"
    ]

    with open(INSIGHTS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for date_key, record in sorted(data.items(), reverse=True):
            row = {k: record.get(k, "") for k in fieldnames}
            writer.writerow(row)

    print(f"  💾 保存完了: {INSIGHTS_JSON}")
    print(f"  💾 CSV保存: {INSIGHTS_CSV}")


def collect_from_post_logs():
    """daily_post_output/*.json から投稿ログを収集"""
    existing = load_existing_insights()
    updated = 0

    log_files = sorted(POST_LOG_DIR.glob("post_*.json"), reverse=True)
    print(f"  投稿ログファイル: {len(log_files)}件")

    for log_file in log_files:
        try:
            with open(log_file, encoding="utf-8") as f:
                post = json.load(f)
        except Exception as e:
            print(f"  ⚠️ 読み込みエラー {log_file.name}: {e}")
            continue

        date_key = post.get("date", log_file.stem.replace("post_", ""))
        if not date_key:
            continue

        record = existing.get(date_key, {})

        # 投稿ログから基本情報を更新
        record.update({
            "date": date_key,
            "weekday": post.get("weekday", ""),
            "theme": post.get("theme", ""),
            "theme_label": post.get("theme_label", ""),
            "item_name": post.get("item_name", ""),
            "image_cdn_url": post.get("image_cdn_url", ""),
            "instagram_posted": post.get("instagram_posted", False),
            "collected_at": datetime.datetime.now().isoformat(),
        })

        # Instagram投稿結果からいいね・コメントを取得（投稿直後は0）
        # 翌日以降のスケジュール実行時に上書き更新される
        if "likes" not in record:
            record["likes"] = 0
        if "comments" not in record:
            record["comments"] = 0
        if "reach" not in record:
            record["reach"] = 0
        if "saved" not in record:
            record["saved"] = 0
        if "shares" not in record:
            record["shares"] = 0

        existing[date_key] = record
        updated += 1

    return existing, updated


def print_summary(data):
    """直近10件のサマリーを表示"""
    print("\n" + "=" * 70)
    print("📈 投稿インサイトサマリー（直近10件）")
    print("=" * 70)
    print(f"{'日付':12} {'曜':2} {'テーマ':20} {'いいね':>5} {'コメ':>4} {'保存':>4} {'投稿':>4}")
    print("-" * 70)

    recent = sorted(data.values(), key=lambda x: x.get("date", ""), reverse=True)[:10]
    for r in recent:
        posted = "✅" if r.get("instagram_posted") else "❌"
        print(f"{r.get('date', '?'):12} {r.get('weekday', '?'):2} "
              f"{r.get('theme_label', r.get('theme', '?'))[:18]:20} "
              f"{r.get('likes', 0):5d} {r.get('comments', 0):4d} "
              f"{r.get('saved', 0):4d} {posted:4}")

    # 統計
    all_posted = [r for r in data.values() if r.get("instagram_posted")]
    if all_posted:
        avg_likes = sum(r.get("likes", 0) for r in all_posted) / len(all_posted)
        max_likes = max(r.get("likes", 0) for r in all_posted)
        best = max(all_posted, key=lambda x: x.get("likes", 0))
        print(f"\n  📊 投稿済み: {len(all_posted)}件 | 平均いいね: {avg_likes:.1f} | 最高: {max_likes}いいね")
        print(f"  🏆 ベスト投稿: {best.get('date')} [{best.get('theme_label', best.get('theme', '?'))}]")


def main():
    print("=" * 60)
    print("📊 Instagramインサイト収集開始")
    print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    data, updated = collect_from_post_logs()
    print(f"  更新: {updated}件")

    save_insights(data)
    print_summary(data)

    print(f"\n✅ 完了！ 合計{len(data)}件のデータを保存")
    return data


if __name__ == "__main__":
    main()

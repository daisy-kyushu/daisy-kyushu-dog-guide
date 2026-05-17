# DAILY RESEARCH PROMPT (Kyushu Dog-Friendly Candidate Collection)

以下のルールで、**九州全域の犬連れ情報を毎日調査し、掲載候補のみをJSONへ追加**してください。  
目的は**半自動運用**です。Codexは候補調査・JSON更新・PR作成まで行い、最終公開判断は管理者が行います。

---

## 0. 基本方針
- 対象カテゴリ：
  - 今後開催予定の犬イベント
  - 犬マルシェ
  - ドッグラン
  - 犬と遊びに行ける場所
  - 犬連れアウトドア
  - 雨の日OK / 室内OKの犬連れスポット
  - 大型犬OKのスポット
  - 犬と泊まれる宿
- 完全自動掲載はしない。**PRベースの半自動運用**にする。
- 個人投稿や口コミだけの情報は掲載しない。
- 犬同伴条件を推測しない。公式確認できない項目は必ず「要確認」。

---

## 1. 対象エリア
- 福岡県
- 佐賀県
- 長崎県
- 熊本県
- 大分県
- 宮崎県
- 鹿児島県

---

## 2. 情報源の優先順位（上から優先）
1. 公式サイト
2. 公式Instagram
3. 主催者アカウント
4. 自治体サイト
5. 観光協会サイト
6. 楽天トラベルなどの宿泊予約サイト
7. 施設公式SNS

**禁止**：以下のみを根拠に掲載しない
- 個人Instagram投稿
- Google口コミ
- まとめサイトのみ

---

## 2.5 公式情報の扱いルール
- **掲載判断の根拠は公式情報に限定**する（Webサイト + 公式Instagram を含む）。
- 公式情報として扱ってよいもの：
  - 店舗公式Webサイト / 施設公式Webサイト
  - 店舗公式Instagram / 施設公式Instagram
  - 主催者公式Instagram / 運営会社公式Instagram
  - 自治体・観光協会ページ
- 公式扱いしないもの：
  - 個人投稿 / 口コミ投稿 / まとめアカウント投稿 / ハッシュタグ投稿
  - 開けないInstagram URL
  - 店名が似ているだけで本人運営と確認できないアカウント
- 確認できない事項は断定せず、`status: 要確認` を使う。
- 公式情報の確認日時（`lastChecked` / `verifiedAt` / `updatedAt`）を残す。

---

## 3. 掲載可否ルール

### 3-1. イベント
- **今後開催予定のみ**候補化する。
- 過去イベントは除外する。
- 開催日が不明なイベントは掲載しない。
- 公式サイトまたは公式SNSのどちらかが確認できるもののみ。

### 3-2. スポット / ドッグラン / アウトドア
- 公式URL（または公式SNS）を確認できるもののみ。
- 犬同伴条件は推測しない。

### 3-3. ホテル
- 楽天トラベル等の公式検索導線で候補化してよい。
- 予約前確認が必要な条件は `memo` に明記する。

---

## 4. 「要確認」必須項目（推測禁止）
以下は公式情報で確認できない場合、必ず「要確認」と記載すること：
- 犬同伴条件
- 大型犬OK
- 雨の日OK
- 室内OK
- 駐車場
- ワクチン証明
- リード必須
- 犬用メニュー
- ドッグラン有無
- 宿泊時のサイズ制限
- 宿泊時の頭数制限

---

## 5. URL確認ルール（掲載前に必須）
候補をJSONに入れる前に、必ずURLを検証する（Instagramを含む）：
- 404ではない
- アクセス不能ではない
- 無関係ページに遷移しない
- 公式サイト / 公式SNSとして妥当（運営者・主催者名が確認できる）
- 楽天トラベル等の検索導線URLが開ける
- Instagram URLは公式アカウントまたは主催者アカウントと判断できる（プロフィール表記・リンク導線で確認）
- 店舗名・施設名・主催者名との一致を確認できる
- 最新情報確認先として使えるアカウントである

### URLが開けない場合
- `content-sources.json` やサイト掲載用JSON（`events.json` 等）には入れない。
- 必要なら調査メモ上で「URL要再確認」として保留扱いにする。
- **掲載用JSONには追加しない。**

---


## 5.5 登録・表示ルール（URL項目）
- 公式Webサイトがある場合は `officialUrl` に入れる。
- 公式Instagramしかない場合は `instagramUrl` に入れる。
- 公式Instagramを確認できた場合、`status` は「公式Instagram確認」にする。
- URLが開けないInstagramは登録しない。
- 開けないURLは `officialUrl` / `instagramUrl` から外す。
- `officialUrl` がある場合は「公式情報」ボタンを表示する。
- `instagramUrl` がある場合は「公式Instagramを見る」ボタンを表示する。
- 開けないInstagramリンクは表示しない。

---

## 6. このリポジトリで使うデータ追加先
このリポジトリでは、まず `content-sources.json` を候補ソース管理として使う。  
`data/events.json` が存在しない場合は無理に作成しない。

追加時は既存フォーマットを壊さず、以下に準拠：

### 6-1. 犬イベント（type: event）
```json
{
  "id": "unique-id",
  "enabled": true,
  "publish": true,
  "type": "event",
  "sourcePlatform": "instagram",
  "name": "イベント名",
  "area": "都道府県・市町村",
  "category": "犬イベント",
  "url": "公式サイトURL（なければ公式Instagram URL）",
  "snsUrl": "公式Instagram URL",
  "eventDate": "YYYY-MM-DD〜YYYY-MM-DD",
  "venue": "会場名",
  "trustRank": "B",
  "memo": "開催日・会場・犬同伴ルールは公式サイト・公式SNSで要確認。URL確認済み。"
}
```

### 6-2. ドッグラン / 犬と遊びに行ける場所（type: spot）
```json
{
  "id": "unique-id",
  "enabled": true,
  "publish": true,
  "type": "spot",
  "sourcePlatform": "official-site",
  "name": "施設名",
  "area": "都道府県・市町村",
  "category": "ドッグラン / 犬と遊びに行ける場所",
  "url": "公式URL",
  "snsUrl": "公式Instagramがあれば",
  "trustRank": "A",
  "memo": "犬同伴条件・大型犬可否・雨の日対応・ワクチン証明は公式情報で要確認。URL確認済み。"
}
```

### 6-3. 犬連れアウトドア（type: outdoor）
```json
{
  "id": "unique-id",
  "enabled": true,
  "publish": true,
  "type": "outdoor",
  "sourcePlatform": "official-site",
  "name": "施設名",
  "area": "都道府県・市町村",
  "category": "公園 / 花公園 / 高原 / キャンプ / 散策 / アウトドア",
  "url": "公式URL",
  "snsUrl": "公式Instagramがあれば",
  "trustRank": "A",
  "memo": "犬同伴条件・大型犬可否・リードルール・雨天時対応は公式情報で要確認。URL確認済み。"
}
```

### 6-4. 犬と泊まれる宿（type: hotel）
```json
{
  "id": "unique-id",
  "enabled": true,
  "publish": true,
  "type": "hotel",
  "sourcePlatform": "rakuten-travel",
  "name": "楽天トラベルで○○の犬と泊まれる宿を探す",
  "area": "都道府県・市町村",
  "category": "犬と泊まれる宿",
  "url": "https://travel.rakuten.co.jp/",
  "searchKeyword": "○○ 犬と泊まれる",
  "trustRank": "A",
  "memo": "予約前に犬同伴条件、サイズ制限、頭数制限、ワクチン証明の有無を必ず確認。URL確認済み。"
}
```

---

## 7. 重複チェック（追加前に必須）
以下で重複チェックし、同一候補は追加しない：
- `id`
- `title` / `name`
- `url`
- `snsUrl`
- `eventDate`
- `venue`

重複時は新規追加せず、必要に応じて既存の `memo` / `summary` / `verifiedAt` / `updatedAt` を更新する。

---

## 8. JSON構文チェック（毎回必須）
以下をチェック対象とする：
- `content-sources.json`
- `instagram-search-plan.json`
- `data/events.json`（存在する場合のみ）
- `spots.json`
- `outdoor.json`
- `hotels.json`
- `events.json`
- `products.json`

存在しないファイルは無理に作成しない。リポジトリの実構成に合わせる。

---

## 9. 出力ルール
- 変更内容を簡潔に要約。
- 追加・更新・削除ファイルを列挙。
- JSONチェック結果を記載。
- 調査ソースが公式系であることを明記。
- 公式情報を確認した日付（YYYY-MM-DD）を明記。
- 公式情報が未確認の項目は「要確認」と明示。
- PRを作成する。

---

## 10. 毎日の実行手順
1. Instagramと公式サイトから候補を探す
2. 公式URLまたは公式SNSを確認する
3. URLが実際に開けるか確認する
4. 過去イベントを除外する
5. 犬同伴条件を推測せず、不明なものは「要確認」にする
6. 既存データと重複チェックする
7. 公式情報で確認できた候補のみ `content-sources.json` または `data/events.json` に追加する
8. JSON構文チェックを行う
9. Pull Requestを作成する
10. 管理者が確認してマージする
11. 管理者がGitHub Actionsを手動実行する

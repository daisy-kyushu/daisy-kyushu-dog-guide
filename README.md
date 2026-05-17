# Daisy Kyushu Dog Guide 完全版

GitHub Pages用の完全版です。  
CSS/JSは各HTMLに埋め込み済みなので、フォルダ崩れでデザインが壊れにくい構成です。

## 使い方

1. このZIPを解凍
2. 解凍したフォルダを開く
3. 中身を全部選択
4. GitHubリポジトリ直下にアップロード
5. Commit changes
6. Settings → Pages → main / root を確認
7. 数分後に公開URLを確認

## GitHub直下に見えるべき主なファイル

```txt
index.html
spots.html
hotels.html
events.html
checklist.html
listing.html
contact.html
privacy.html
ad-policy.html
products.json
hotels.json
spots.json
events.json
daisy_samoyed1217_qr.png
```

## 楽天商品更新

GitHub Secretsに以下を登録済みなら、Actionsで実行できます。

```txt
RAKUTEN_APP_ID
RAKUTEN_AFFILIATE_ID
```

実行手順：

```txt
Actions
↓
Update Rakuten Products
↓
Run workflow
```

## 注意

楽天トラベルは404対策として、楽天トラベル公式トップを開き、サイト内に検索ワード例を表示する方式にしています。
宿泊条件は変わるため、予約前に必ず楽天トラベル掲載ページと宿の公式情報を確認してください。


## v2更新内容

- イベント一覧は「今後開催予定」のみ表示します。
- `events.json` に過去イベントが残っていても、画面表示時に自動で非表示になります。
- Actions の `Update Events` を実行すると、過去イベントを `events.json` から削除して今後開催イベントだけに整理します。

## v3追加機能

- `weekend.html`：今週末行けるスポット候補
- `map.html`：地図から探す
- `admin.html`：Googleフォーム回答をスプレッドシート管理する手順
- `pr.html`：PR掲載メニュー・料金表
- `instagram-drafts.html`：Instagram投稿下書き
- `generate-instagram-drafts.js`：投稿下書き自動生成
- `Generate Instagram Drafts`：GitHub Actionsで投稿下書きを生成

過去イベントは画面上で自動非表示になり、`Update Events` 実行時に `events.json` から整理されます。


## 掲載ルール（公式情報の扱い）

- 公式情報は、**公式Webサイトだけでなく公式Instagramも含む**運用です。
- 公式として扱う情報・扱わない情報・Instagram判定条件・登録/表示ルールは `DATA_RULES.md` を参照してください。
- URLが開けないInstagramは掲載対象外です。


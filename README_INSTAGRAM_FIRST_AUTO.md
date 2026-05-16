# Instagram優先 自動掲載パック

このパックは、犬イベントをInstagram中心で探し、ホテルは「犬と泊まれる」、遊び場は「犬と遊びに行ける場所」、アウトドアは「くじゅう花公園」などを候補化して、サイト掲載用JSONへ自動反映するためのものです。

## 方針

- 人気が出やすい犬イベントはInstagramから探す
- ホテルは楽天トラベルの「犬と泊まれる」検索導線にする
- 犬と遊びに行ける場所を spot として追加
- くじゅう花公園のような場所は outdoor として追加
- 不明な犬同伴条件は必ず「要確認」にする
- 過去イベントは掲載しない

## 入っているファイル

```txt
content-sources.json
instagram-search-plan.json
auto-collect-content.js
.github/workflows/instagram-first-auto-publish.yml
CODEX_CHROME_INSTAGRAM_PROMPT.md
README_INSTAGRAM_FIRST_AUTO.md
```

## 使い方

1. ZIPを解凍
2. 中身をGitHub直下へアップロード
3. Actionsを開く
4. Instagram First Auto Publish を選択
5. Run workflow を押す

## Codex Chromeプラグインで使う場合

`CODEX_CHROME_INSTAGRAM_PROMPT.md` の中身をCodexに貼り付けてください。

Codexにやらせること：

```txt
Instagramで犬イベントを探す
公式アカウント・公式サイトを確認する
content-sources.json に追記する
Actionsを実行する
公開サイトで確認する
```

## 注意

Instagramを機械的に大量スクレイピングする仕組みではありません。
Chromeプラグインで公式投稿を確認し、掲載できる候補だけを `content-sources.json` に入れる運用です。

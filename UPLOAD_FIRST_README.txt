このZIPは「リポジトリ直下にアップロードする版」です。

重要：
- ZIPを解凍してください。
- 解凍してできたフォルダを開いてください。
- その中にある index.html / assets / data / docs / scripts / .github などを全部選択してください。
- GitHubのリポジトリ直下にアップロードしてください。
- フォルダごとアップロードしないでください。

正しいGitHub直下の見え方：
.github
assets
data
docs
scripts
README.md
index.html
spots.html
hotels.html
events.html
checklist.html
listing.html
contact.html
privacy.html
ad-policy.html
package.json

今回の修正内容：
1. 楽天トラベルの404になりやすい古い検索URLを修正
2. 楽天トラベルは公式トップを開き、検索ワード例を表示する方式に変更
3. 楽天商品候補を約20件に増加
4. 楽天API更新後に商品画像付きバナーとして表示
5. トップページにもDaisyおすすめグッズのバナー枠を追加
6. .github/workflows を入れて、Update Rakuten Products / Hotels / Events が出るように修正

アップロード後：
Actions → Update Rakuten Products → Run workflow
を押すと、楽天APIで商品データが更新されます。

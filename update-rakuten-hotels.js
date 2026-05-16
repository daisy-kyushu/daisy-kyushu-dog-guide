const fs = require("fs/promises");
const path = require("path");

const DATA_PATH = path.join(__dirname, "hotels.json");

async function main() {
  const today = new Date().toISOString().slice(0, 10);
  const hotels = [
    {
      id: "rakuten-travel-oita-pet-search",
      name: "楽天トラベルで大分県の犬と泊まれる宿を探す",
      area: "大分県",
      dogSize: "宿ごとに要確認",
      roomWithDog: "宿ごとに要確認",
      mealAreaWithDog: "宿ごとに要確認",
      dogRun: "宿ごとに要確認",
      vaccineRequired: "宿ごとに要確認",
      officialUrl: "https://travel.rakuten.co.jp/",
      rakutenTravelUrl: "https://travel.rakuten.co.jp/",
      searchKeyword: "大分 犬 同伴",
      lastChecked: today,
      status: "楽天トラベル公式トップへ誘導",
      memo: "楽天トラベルの検索欄で「大分 犬 同伴」「大分 ペットと泊まれる宿」などで検索してください。犬同伴条件・料金・頭数制限・ワクチン証明の有無は変更される場合があります。"
    },
    {
      id: "rakuten-travel-kyushu-pet-search",
      name: "楽天トラベルで九州の犬と泊まれる宿を探す",
      area: "九州",
      dogSize: "宿ごとに要確認",
      roomWithDog: "宿ごとに要確認",
      mealAreaWithDog: "宿ごとに要確認",
      dogRun: "宿ごとに要確認",
      vaccineRequired: "宿ごとに要確認",
      officialUrl: "https://travel.rakuten.co.jp/",
      rakutenTravelUrl: "https://travel.rakuten.co.jp/",
      searchKeyword: "九州 犬 同伴",
      lastChecked: today,
      status: "楽天トラベル公式トップへ誘導",
      memo: "楽天トラベルの検索欄で「九州 犬 同伴」「九州 ペットと泊まれる宿」などで検索してください。宿ごとの条件は必ず確認してください。"
    }
  ];

  await fs.writeFile(DATA_PATH, JSON.stringify(hotels, null, 2), "utf8");
  console.log("hotels.json を更新しました。");
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

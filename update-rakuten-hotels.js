const fs = require("fs/promises");

const AFF_BASE = "https://hb.afl.rakuten.co.jp/hgc/";
const DEFAULT_RAKUTEN_TRAVEL_URL = "https://travel.rakuten.co.jp/pet/";
const CAUTION = "料金・空室・犬同伴条件・頭数制限・サイズ制限・ワクチン証明の条件は変動するため、予約前に楽天トラベル側・宿公式側で必ず確認してください。";
const NOTE_ACTIVE = "楽天トラベルのアフィリエイト導線を設定済みです。";
const NOTE_SEARCH = "楽天トラベルの通常導線のみです。";

const REGION_DESTINATIONS = [
  { keys: ["福岡", "fukuoka"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Fukuoka?f_query=%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["佐賀", "saga"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Saga?f_query=%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["長崎", "nagasaki"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Nagasaki?f_query=%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["熊本", "kumamoto"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Kumamoto?f_query=%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["湯布院", "由布院", "由布", "yufuin"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Oita?f_query=%E6%B9%AF%E5%B8%83%E9%99%A2%20%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["大分", "oita"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Oita?f_query=%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["宮崎", "miyazaki"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Miyazaki?f_query=%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["鹿児島", "kagoshima"], url: "https://search.travel.rakuten.co.jp/ds/hotellist/Japan-Kagoshima?f_query=%E7%8A%AC%20%E5%90%8C%E4%BC%B4" },
  { keys: ["九州", "kyushu"], url: "https://travel.rakuten.co.jp/pet/" }
];

function sanitizeMemo(memo) {
  return String(memo || "")
    .replaceAll(NOTE_ACTIVE, "")
    .replaceAll(NOTE_SEARCH, "")
    .replaceAll(CAUTION, "")
    .replace(/\s+/g, " ")
    .trim();
}

function pickRegionDestination(hotel) {
  const haystack = [hotel.id, hotel.name, hotel.area, hotel.searchKeyword]
    .map((value) => String(value || "").toLowerCase())
    .join(" ");

  const matched = REGION_DESTINATIONS.find((region) =>
    region.keys.some((key) => haystack.includes(String(key).toLowerCase()))
  );

  return matched ? matched.url : "";
}

function sanitizeTravelUrl(url) {
  const value = String(url || "").trim();

  // 楽天トラベルの keyword/Search.do は404になりやすいため使わない。
  if (!value || value === "https://travel.rakuten.co.jp/" || value.includes("/keyword/Search.do")) {
    return DEFAULT_RAKUTEN_TRAVEL_URL;
  }

  try {
    const parsed = new URL(value);
    const allowedHosts = ["travel.rakuten.co.jp", "search.travel.rakuten.co.jp"];
    if (!allowedHosts.includes(parsed.hostname)) return DEFAULT_RAKUTEN_TRAVEL_URL;
    return parsed.toString();
  } catch (error) {
    return DEFAULT_RAKUTEN_TRAVEL_URL;
  }
}

function buildDestination(hotel) {
  return sanitizeTravelUrl(pickRegionDestination(hotel) || hotel.rakutenTravelUrl);
}

function buildAffiliateUrl(destination, affiliateId) {
  if (!affiliateId || !destination) return "";
  const encodedDest = encodeURIComponent(destination);
  return `${AFF_BASE}${affiliateId}/?pc=${encodedDest}&m=${encodedDest}`;
}

function buildMemo(currentMemo, affiliateActive, destination) {
  const clean = sanitizeMemo(currentMemo);
  const lead = affiliateActive ? NOTE_ACTIVE : NOTE_SEARCH;
  const regionNote = destination.includes("search.travel.rakuten.co.jp")
    ? "地域別の楽天トラベル宿一覧へ誘導します。"
    : "楽天トラベルのペット同伴宿ページへ誘導します。";
  return `${lead} ${regionNote} ${clean ? clean + " " : ""}${CAUTION}`.trim();
}

async function main() {
  const affiliateId = process.env.RAKUTEN_AFFILIATE_ID || "";
  const today = new Date().toISOString().slice(0, 10);
  const hotels = JSON.parse(await fs.readFile("hotels.json", "utf8"));

  const updated = hotels.map((hotel) => {
    const destination = buildDestination(hotel);
    const affiliateUrl = buildAffiliateUrl(destination, affiliateId);

    let affiliateStatus = "link-missing";
    if (affiliateUrl) affiliateStatus = "affiliate-active";
    else if (destination) affiliateStatus = "search-only";

    return {
      ...hotel,
      rakutenTravelUrl: destination,
      rakutenTravelAffiliateUrl: affiliateUrl,
      affiliateStatus,
      lastChecked: today,
      memo: buildMemo(hotel.memo, affiliateStatus === "affiliate-active", destination)
    };
  });

  await fs.writeFile("hotels.json", JSON.stringify(updated, null, 2) + "\n", "utf8");
  console.log(`hotels updated: ${updated.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

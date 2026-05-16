const fs = require("fs/promises");

const today = () => new Date().toISOString().slice(0, 10);

async function readJson(path, fallback = []) {
  try {
    return JSON.parse(await fs.readFile(path, "utf8"));
  } catch {
    return fallback;
  }
}

async function writeJson(path, data) {
  await fs.writeFile(path, JSON.stringify(data, null, 2), "utf8");
}

function datesIn(text) {
  return String(text || "").match(/\d{4}-\d{2}-\d{2}/g) || [];
}

function isFutureDateText(text) {
  const dates = datesIn(text);
  if (!dates.length) return false;
  return dates[dates.length - 1] >= today();
}

function sameId(list, id) {
  return list.some(x => x.id === id);
}

function sameName(list, name) {
  return list.some(x => String(x.name || "").trim() === String(name || "").trim());
}

function mapQuery(source) {
  return `${source.name || ""} ${source.area || ""}`.trim();
}

function spotFrom(source) {
  return {
    id: source.id,
    name: source.name,
    area: source.area || "要確認",
    type: source.category || "犬と遊びに行ける場所",
    dogAllowed: "要確認",
    largeDog: "要確認",
    rainyOk: "要確認",
    indoorOk: "要確認",
    parking: "要確認",
    officialUrl: source.url,
    snsUrl: source.snsUrl || "",
    lastChecked: today(),
    status: `自動候補 / ${source.sourcePlatform || "source"} / 信頼度${source.trustRank || "C"}`,
    memo: source.memo || "犬同伴条件は公式情報で要確認。",
    weekendRecommended: true,
    mapQuery: mapQuery(source)
  };
}

function outdoorFrom(source) {
  return {
    id: source.id,
    name: source.name,
    area: source.area || "要確認",
    type: source.category || "犬連れアウトドア",
    dogAllowed: "要確認",
    largeDog: "要確認",
    rainyOk: "屋外中心 / 要確認",
    indoorOk: "施設ごとに要確認",
    officialUrl: source.url,
    snsUrl: source.snsUrl || "",
    mapQuery: mapQuery(source),
    lastChecked: today(),
    status: `自動候補 / ${source.sourcePlatform || "source"} / 信頼度${source.trustRank || "C"}`,
    memo: source.memo || "犬同伴条件は公式情報で要確認。"
  };
}

function hotelFrom(source) {
  return {
    id: source.id,
    name: source.name,
    area: source.area || "要確認",
    dogSize: "宿ごとに要確認",
    roomWithDog: "宿ごとに要確認",
    mealAreaWithDog: "宿ごとに要確認",
    dogRun: "宿ごとに要確認",
    vaccineRequired: "宿ごとに要確認",
    rakutenTravelUrl: source.url || "https://travel.rakuten.co.jp/",
    searchKeyword: source.searchKeyword || `${source.area || ""} 犬と泊まれる`.trim(),
    lastChecked: today(),
    status: `自動候補 / ${source.sourcePlatform || "rakuten-travel"} / 信頼度${source.trustRank || "A"}`,
    memo: source.memo || "予約前に犬同伴条件を必ず確認してください。"
  };
}

function eventFrom(source) {
  return {
    id: source.id,
    name: source.name,
    date: source.eventDate || "要確認",
    area: source.area || "要確認",
    venue: source.venue || "要確認",
    dogRules: "公式サイト・公式SNSで要確認",
    officialUrl: source.url,
    officialSnsUrl: source.snsUrl || "",
    lastChecked: today(),
    status: `Instagram候補 / 信頼度${source.trustRank || "B"}`,
    memo: source.memo || "イベント情報は変更・中止になる場合があります。参加前に必ず公式情報を確認してください。"
  };
}

async function main() {
  const sources = (await readJson("content-sources.json", [])).filter(s => s.enabled && s.publish);

  const spots = await readJson("spots.json", []);
  const outdoor = await readJson("outdoor.json", []);
  const hotels = await readJson("hotels.json", []);
  const events = await readJson("events.json", []);

  const report = [];

  for (const source of sources) {
    report.push({
      id: source.id,
      type: source.type,
      name: source.name,
      platform: source.sourcePlatform || "",
      url: source.url || "",
      checkedAt: today(),
      publish: !!source.publish
    });

    if (source.type === "spot" && !sameId(spots, source.id) && !sameName(spots, source.name)) {
      spots.push(spotFrom(source));
    }

    if (source.type === "outdoor" && !sameId(outdoor, source.id) && !sameName(outdoor, source.name)) {
      outdoor.push(outdoorFrom(source));
    }

    if (source.type === "hotel" && !sameId(hotels, source.id)) {
      hotels.push(hotelFrom(source));
    }

    if (source.type === "event") {
      if (!source.eventDate || !isFutureDateText(source.eventDate)) continue;
      if (!sameId(events, source.id) && !sameName(events, source.name)) {
        events.push(eventFrom(source));
      }
    }
  }

  const futureEvents = events
    .filter(e => isFutureDateText(e.date))
    .sort((a, b) => String(a.date).localeCompare(String(b.date)));

  await writeJson("spots.json", spots);
  await writeJson("outdoor.json", outdoor);
  await writeJson("hotels.json", hotels);
  await writeJson("events.json", futureEvents);
  await writeJson("auto-collection-report.json", report);

  console.log(`spots: ${spots.length}`);
  console.log(`outdoor: ${outdoor.length}`);
  console.log(`hotels: ${hotels.length}`);
  console.log(`events: ${futureEvents.length}`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

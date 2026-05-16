const fs = require("fs/promises");
const path = require("path");
const APP_ID = process.env.RAKUTEN_APP_ID;
const AFF_ID = process.env.RAKUTEN_AFFILIATE_ID;
const DATA_PATH = path.join(__dirname, "products.json");
const queries = [
  {id:"car-seat-cover",keyword:"犬 車 シートカバー 大型犬",category:"車移動",scene:["車移動", "抜け毛対策", "汚れ対策"]},
  {id:"drive-bed",keyword:"犬 ドライブベッド 大型犬",category:"車移動",scene:["車移動"]},
  {id:"large-harness",keyword:"大型犬 ハーネス",category:"安全対策",scene:["車移動", "ドッグラン", "イベント"]},
  {id:"dog-cart",keyword:"大型犬 ペットカート",category:"移動",scene:["宿泊旅行", "イベント", "観光"]},
  {id:"water-bottle",keyword:"犬 散歩 給水ボトル",category:"持ち物",scene:["宿泊旅行", "イベント", "ドッグラン"]},
  {id:"raincoat",keyword:"大型犬 レインコート",category:"雨の日",scene:["雨の日"]},
  {id:"odor-bag",keyword:"犬 うんち袋 防臭袋",category:"マナー",scene:["宿泊旅行", "イベント", "カフェ"]},
  {id:"brush",keyword:"犬 抜け毛 ブラシ 大型犬",category:"抜け毛対策",scene:["車移動", "宿泊旅行"]},
  {id:"folding-bowl",keyword:"犬 折りたたみ フードボウル",category:"旅行",scene:["宿泊旅行", "イベント"]},
  {id:"pet-towel",keyword:"犬 吸水 タオル 大型犬",category:"雨の日",scene:["雨の日", "車移動"]},
  {id:"pet-sheet",keyword:"犬 ペットシーツ 厚型",category:"宿泊旅行",scene:["宿泊旅行", "車移動"]},
  {id:"dog-wet-tissue",keyword:"犬 ウェットティッシュ",category:"マナー",scene:["カフェ", "車移動", "宿泊旅行"]},
  {id:"cool-mat",keyword:"犬 冷感マット 大型犬",category:"暑さ対策",scene:["車移動", "宿泊旅行", "夏"]},
  {id:"winter-wear",keyword:"大型犬 防寒 犬服",category:"寒さ対策",scene:["冬のおでかけ"]},
  {id:"long-lead",keyword:"犬 ロングリード 大型犬",category:"ドッグラン",scene:["ドッグラン", "公園"]},
  {id:"dog-bag",keyword:"犬 お散歩バッグ",category:"持ち物",scene:["カフェ", "イベント", "散歩"]},
  {id:"cooling-vest",keyword:"犬 クールベスト 大型犬",category:"暑さ対策",scene:["夏", "イベント", "散歩"]},
  {id:"paw-cream",keyword:"犬 肉球クリーム",category:"ケア",scene:["散歩後", "宿泊旅行"]},
  {id:"car-step",keyword:"犬 車 ステップ 大型犬",category:"車移動",scene:["車移動"]},
  {id:"travel-bed",keyword:"犬 トラベルベッド",category:"宿泊旅行",scene:["宿泊旅行", "車移動"]},
  {id:"lead-light",keyword:"犬 LEDライト 散歩",category:"安全対策",scene:["夜散歩", "旅行"]},
  {id:"name-tag",keyword:"犬 迷子札",category:"安全対策",scene:["イベント", "宿泊旅行"]},
  {id:"poop-pouch",keyword:"犬 マナーポーチ 消臭",category:"マナー",scene:["イベント", "カフェ", "宿泊旅行"]},
  {id:"pet-backpack",keyword:"犬 旅行 バッグ 大型犬 用品",category:"持ち物",scene:["宿泊旅行", "車移動"]}
];
function sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms));}
function scoreItem(item){const reviewAverage=Number(item.reviewAverage||0);const reviewCount=Number(item.reviewCount||0);const price=Number(item.itemPrice||0);let score=reviewAverage*20+Math.min(reviewCount,2000)/10;if(price>0)score+=5;return score;}
async function searchRakuten(q){const params=new URLSearchParams({applicationId:APP_ID,affiliateId:AFF_ID,format:"json",keyword:q.keyword,hits:"20",sort:"-reviewCount"});const res=await fetch(`https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?${params}`);if(!res.ok)throw new Error(`Rakuten API error ${res.status}: ${await res.text()}`);const data=await res.json();const items=(data.Items||[]).map(e=>e.Item);if(!items.length)return null;return items.sort((a,b)=>scoreItem(b)-scoreItem(a))[0];}
async function main(){if(!APP_ID||!AFF_ID){console.log("RAKUTEN_APP_ID / RAKUTEN_AFFILIATE_ID が未設定です。GitHub Secretsを確認してください。");return;}const updated=[];const today=new Date().toISOString().slice(0,10);for(const q of queries){try{const item=await searchRakuten(q);await sleep(1300);if(!item)continue;updated.push({id:q.id,category:q.category,productName:item.itemName,target:q.keyword,dogSize:q.keyword.includes("大型犬")?["大型犬"]:["小型犬","中型犬","大型犬"],scene:q.scene,normalUrl:item.itemUrl,rakutenAffiliateUrl:item.affiliateUrl||item.itemUrl,rating:item.reviewAverage||"",reviewCount:item.reviewCount||"",itemPrice:item.itemPrice||"",shopName:item.shopName||"",mediumImageUrls:(item.mediumImageUrls||[]).map(x=>x.imageUrl),whyCandidate:"楽天APIでレビュー件数・評価を参考に自動選定した候補です。購入前にリンク先で最新情報を確認してください。",lastChecked:today,status:"楽天API取得済み",memo:"価格・在庫・評価は変動します。断定表現を避けて紹介してください。"});}catch(err){console.error(`Failed: ${q.keyword}`,err.message);}}if(updated.length){await fs.writeFile(DATA_PATH,JSON.stringify(updated,null,2),"utf8");console.log(`products.json を ${updated.length} 件で更新しました。`);}else{console.log("更新対象の商品がありませんでした。");}}
main().catch(err=>{console.error(err);process.exit(1);});

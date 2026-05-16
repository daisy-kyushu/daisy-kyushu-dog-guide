const fs=require("fs/promises");

function eventEndDate(dateText){
  const matches=String(dateText||"").match(/\d{4}-\d{2}-\d{2}/g);
  return matches&&matches.length?matches[matches.length-1]:null;
}

function isUpcomingEvent(ev){
  const end=eventEndDate(ev.date);
  if(!end) return false;
  const today=new Date().toISOString().slice(0,10);
  return end>=today;
}

async function main(){
  const today=new Date().toISOString().slice(0,10);
  const events=JSON.parse(await fs.readFile("events.json","utf8"));
  const upcoming=events
    .filter(isUpcomingEvent)
    .sort((a,b)=>(eventEndDate(a.date)||"9999-99-99").localeCompare(eventEndDate(b.date)||"9999-99-99"));
  upcoming.forEach(e=>e.lastChecked=today);
  await fs.writeFile("events.json",JSON.stringify(upcoming,null,2),"utf8");
  console.log(`events.json を今後開催イベント ${upcoming.length} 件に整理しました。`);
}

main().catch(e=>{console.error(e);process.exit(1);});

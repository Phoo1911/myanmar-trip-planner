"use client";
import {useEffect,useState} from 'react';
import Concierge from './Concierge';
import Commerce from './Commerce';
import {DRAFT_KEY,parseDraft,type Route,type TripSpot} from './trip-storage';
type Lang='ko'|'en'|'my';
const tr=(l:Lang,ko:string,en:string,my:string)=>({ko,en,my}[l]);

// Step 3: per-day checks from the saved trip, then one travel-desk request prefilled with that plan.
export default function Prepare({lang,cart,onPlan,safetySource}:{lang:Lang;cart:TripSpot[];onPlan:()=>void;safetySource:string}){
 const[draft,D]=useState<{days:number;route:Route}|null>(null),[ready,READY]=useState(false);
 useEffect(()=>{try{D(parseDraft(localStorage.getItem(DRAFT_KEY),cart))}catch{D(null)}READY(true)},[cart]);
 const free=tr(lang,'자유 일정','Open day','လွတ်လပ်သောနေ့');
 const notes=(draft?draft.route.days.map(d=>'DAY '+d.day+': '+(d.stops.map(s=>s.name[lang]).join(' → ')||free)).join('\n'):cart.map(p=>p.name[lang]).join(', ')).slice(0,900);
 const check=(title:string,note:string,kind:'check'|'request'|'info')=><li className="check-item"><span className={'tag '+kind}>{kind==='check'?tr(lang,'확인 필요','Check needed','စစ်ရန်လို'):kind==='request'?tr(lang,'요청 가능','Can request','တောင်းဆိုနိုင်'):tr(lang,'공식 출처','Official source','တရားဝင်ရင်းမြစ်')}</span><div className="grow"><b>{title}</b><p>{note}</p></div>{kind==='info'&&<a href={safetySource} target="_blank" rel="noreferrer">{tr(lang,'공식 출처','Official source','တရားဝင်ရင်းမြစ်')} ↗</a>}</li>;
 return <section className="prepare-stage">
  <div><h1 className="step-title">{tr(lang,'떠나기 전에 준비할 것','Before you go','မထွက်ခွာမီ ပြင်ဆင်ရန်')}</h1><p className="step-sub">{tr(lang,'일정에 맞춰 확인할 것과 요청할 것을 정리했어요. 아래 상담 요청 한 번으로 운영팀에 전달됩니다.','Checks and requests for your plan, gathered in one place. One travel-desk request below sends them together.','သင့်ခရီးစဉ်အတွက် စစ်ရန်နှင့် တောင်းဆိုရန်များ။ အောက်ပါ တောင်းဆိုမှုတစ်ခုဖြင့် ပို့နိုင်သည်။')}</p></div>
  {ready&&!cart.length&&<div className="empty-state">{tr(lang,'아직 담은 장소가 없어요. 1단계에서 장소를 담고 2단계에서 순서를 저장하면 날짜별로 정리돼요.','No places yet. Add places in step 1 and save an order in step 2 to see a day-by-day list.','နေရာ မထည့်ရသေးပါ။')} <button className="secondary" onClick={onPlan}>{tr(lang,'지도·일정으로','Go to map & plan','မြေပုံ·အစီအစဉ်သို့')}</button></div>}
  {ready&&cart.length>0&&!draft&&<div className="alert">{tr(lang,'저장된 방문 순서가 없어 담은 장소만 보여요. 2단계에서 순서를 만들고 저장하면 날짜별로 정리됩니다.','No saved visit order, so only your places are listed. Arrange and save in step 2 for a day-by-day list.','သိမ်းထားသော အစီအစဉ်မရှိပါ။')} <button className="secondary" onClick={onPlan}>{tr(lang,'순서 만들기','Arrange order','အစီအစဉ်လုပ်ရန်')}</button></div>}
  <div className="check-grid">
   {(draft?draft.route.days:cart.length?[{day:0,stops:cart}]:[]).map((d,i)=><article key={d.day} className="day-card">
    <div className="results-head"><h2>{d.day?'DAY '+d.day:tr(lang,'담은 장소','Saved places','ထည့်ထားသောနေရာ')}</h2><span className="fine">{d.stops.map(s=>s.name[lang]).join(' → ')||free}</span></div>
    <ul className="check-list">
     {i===0&&check(tr(lang,'지역별 여행경보','Regional travel advice','ဒေသအလိုက် ခရီးသွားသတိပေးချက်'),tr(lang,'출발 전 최신 경보를 확인하세요. 이 서비스는 안전을 보장하지 않습니다.','Check the latest advice before departure. This service does not certify safety.','ထွက်ခွာမီ နောက်ဆုံးသတိပေးချက်ကို စစ်ပါ။'),'info')}
     {d.stops.length>0&&check(tr(lang,'입장·복장·영업 조건','Entry, dress code and opening','ဝင်ခွင့်၊ ဝတ်စားဆင်ယင်မှု၊ ဖွင့်ချိန်'),tr(lang,'확인된 출처가 없어요. 방문 전에 확인하거나 운영팀에 물어보세요.','No verified source yet. Check before visiting or ask the travel desk.','အတည်ပြုရင်းမြစ် မရှိသေးပါ။'),'check')}
     {d.stops.length>1&&check(tr(lang,'장소 사이 이동 시간','Travel time between stops','နေရာများကြား သွားလာချိန်'),tr(lang,'직선거리 순서일 뿐, 실제 도로·소요시간은 확인되지 않았어요.','Order is straight-line only; road routes and times are unverified.','လမ်းကြောင်းနှင့် ကြာချိန် မစစ်ရသေးပါ။'),'check')}
     {!d.stops.length&&<li className="fine">{tr(lang,'장소를 더 담거나, 아래 요청서에 현지 추천을 요청할 수 있어요.','Add more places, or ask the travel desk for local suggestions below.','နေရာထပ်ထည့်ပါ သို့မဟုတ် ဒေသအကြံပြုချက် တောင်းပါ။')}</li>}
    </ul>
   </article>)}
   {cart.length>0&&<article className="day-card">
    <div className="results-head"><h2>{tr(lang,'여행 전체','Whole trip','ခရီးစဉ်တစ်ခုလုံး')}</h2><span className="fine">{tr(lang,'아래 요청서에서 선택','Choose in the request below','အောက်ပါတောင်းဆိုမှုတွင် ရွေးပါ')}</span></div>
    <ul className="check-list">
     {check(tr(lang,'차량·기사','Vehicle and driver','ယာဉ်နှင့် ယာဉ်မောင်း'),tr(lang,'‘차량’을 고르면 운영팀이 가능 여부와 견적을 확인해요.','Choose “Vehicle”; the desk checks availability and quotes.','ယာဉ်ကို ရွေးပါ။'),'request')}
     {check(tr(lang,'숙소','Stay','တည်းခိုရေး'),tr(lang,'‘숙소’를 고르고 희망 지역·예산을 추가 요청에 적어 주세요.','Choose “Stay” and add your preferred area and budget.','တည်းခိုရေးကို ရွေးပြီး နေရာနှင့် ဘတ်ဂျက် ရေးပါ။'),'request')}
     {check(tr(lang,'현지 가이드','Local guide','ဒေသဧည့်လမ်းညွှန်'),tr(lang,'‘가이드’를 고르고 원하는 언어를 적어 주세요.','Choose “Guide” and note the language you need.','ဧည့်လမ်းညွှန်ကို ရွေးပြီး ဘာသာစကား ရေးပါ။'),'request')}
    </ul>
   </article>}
  </div>
  <div className="request-card">{ready&&<Concierge key={notes} lang={lang} initial={{days:draft?.days,notes}}/>}</div>
  <details className="request-card"><summary>{tr(lang,'운영자 배정 상품 바로 예약','Book operator-allocated offers','ခွဲတမ်းပါ ကမ်းလှမ်းချက် ဘွတ်ကင်')}</summary><Commerce lang={lang}/></details>
  <p className="fine">{tr(lang,'가격은 운영자 견적으로만 안내돼요. 공급사 확정 전에는 예약이 아니며, 체험판에서는 결제가 없습니다.','Prices come only from operator quotes. Nothing is booked before supplier confirmation, and the preview takes no payment.','ဈေးနှုန်းကို လုပ်ငန်းရှင်ထံမှသာ ရရှိမည်။ ငွေပေးချေမှု မရှိပါ။')}</p>
 </section>
}

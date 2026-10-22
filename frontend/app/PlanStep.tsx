"use client";
import {useEffect,useMemo,useState} from 'react';
import dynamic from 'next/dynamic';
import Trip from './Trip';
import type {Route,TripSpot} from './trip-storage';
const Map=dynamic(()=>import('./Map'),{ssr:false});
type Lang='ko'|'en'|'my';
type Road={days:{day:number;distance_m:number;time_s:number}[]};
const api=process.env.NEXT_PUBLIC_API_URL||'/api';
const tr=(l:Lang,ko:string,en:string,my:string)=>({ko,en,my}[l]);

// Step 2: the map shows the arranged visit order beside the editable trip, with optional road times and a share link.
export default function PlanStep({lang,cart,onRemove,onBrowse,onNext,onClear}:{lang:Lang;cart:TripSpot[];onRemove:(id:string)=>void;onBrowse:()=>void;onNext:()=>void;onClear:()=>void}){
 const[route,R]=useState<Route|null>(null),[selected,D]=useState('');
 const[geoReady,GEO]=useState(false),[road,ROAD]=useState<Road|null>(null),[roadBusy,RB]=useState(false),[roadError,RE]=useState('');
 const[shareUrl,SHARE]=useState(''),[shareBusy,SB]=useState(false),[shareError,SE]=useState(''),[copied,COPIED]=useState(false);
 useEffect(()=>{const a=new AbortController();fetch(api+'/discovery/geo-status',{signal:a.signal}).then(r=>r.ok?r.json():Promise.reject()).then(d=>GEO(!!d.configured)).catch(()=>{});return()=>a.abort()},[]);
 useEffect(()=>{ROAD(null);RE('')},[route]);
 useEffect(()=>{SHARE('');SE('');COPIED(false)},[cart,route]);
 const stops=useMemo(()=>route?route.days.flatMap(d=>d.stops):cart,[route,cart]);
 const labels=useMemo(()=>route?Object.fromEntries(route.days.flatMap(d=>d.stops.map((p,i)=>[p.id,'D'+d.day+'·'+(i+1)+' '+p.name[lang]]))):Object.fromEntries(cart.map((p,i)=>[p.id,(i+1)+' '+p.name[lang]])),[route,cart,lang]);

 async function roadTimes(){
  if(!route)return;RB(true);RE('');
  try{const r=await fetch(api+'/routes/road',{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(60000),body:JSON.stringify({days:route.days.map(d=>({day:d.day,stops:d.stops.map(p=>({id:p.id,lat:p.lat,lng:p.lng}))}))})});
   if(!r.ok)throw Error(String(r.status));ROAD(await r.json());
  }catch(e){RE(e instanceof Error&&e.message==='429'?tr(lang,'오늘 무료 지도 조회 한도에 도달했어요. 내일 다시 시도해 주세요.','Today\'s free map lookup limit is reached. Try again tomorrow.','ယနေ့ အခမဲ့ကန့်သတ်ချက် ပြည့်ပါပြီ။'):tr(lang,'도로 이동시간을 불러오지 못했어요. 다시 시도해 주세요.','Could not load road times. Please retry.','လမ်းကြာချိန် မရနိုင်ပါ။ ပြန်စမ်းပါ။'))}finally{RB(false)}
 }
 async function share(){
  SB(true);SE('');COPIED(false);
  const places=cart.map(p=>({...p,references:(p.references||[]).slice(0,3)}));
  const draft=route?{days:route.days.length,route:route.days.map(d=>({day:d.day,stop_ids:d.stops.map(p=>p.id)}))}:undefined;
  try{const r=await fetch(api+'/trips',{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(20000),body:JSON.stringify({places,draft})});
   if(!r.ok)throw Error(String(r.status));const data=await r.json();SHARE(location.origin+'/?trip='+encodeURIComponent(data.id));
  }catch(e){SE(e instanceof Error&&e.message==='413'?tr(lang,'일정이 너무 커서 공유할 수 없어요. 장소를 줄여 주세요.','The trip is too large to share. Remove some places.','ခရီးစဉ် ကြီးလွန်းသည်။'):tr(lang,'공유 링크를 만들지 못했어요. 다시 시도해 주세요.','Could not create a share link. Please retry.','မျှဝေလင့်ခ် မဖန်တီးနိုင်ပါ။'))}finally{SB(false)}
 }
 const km=(m:number)=>(m/1000).toFixed(1)+' km';const minutes=(s:number)=>{const m=Math.round(s/60);return m>=60?Math.floor(m/60)+tr(lang,'시간 ','h ','နာရီ ')+(m%60)+tr(lang,'분','m','မိနစ်'):m+tr(lang,'분','m','မိနစ်')};

 return <section className="stage plan-stage">
  <div className="stage-map"><Map places={stops} selectedId={stops.some(p=>p.id===selected)?selected:undefined} onSelect={D} lang={lang} labels={labels}/><p className="map-chip">{route?tr(lang,'직선거리 기준 방문 순서','Straight-line visit order','တိုက်ရိုက်အကွာအဝေးအလိုက် အစီအစဉ်'):tr(lang,'담은 장소','Saved places','ထည့်ထားသောနေရာ')} · {road?tr(lang,'도로 시간은 자동차 기준 추정','Road times are driving estimates','ယာဉ်ဖြင့် ခန့်မှန်းချိန်'):tr(lang,'실제 도로·이동시간 미확인','Road routes and times unverified','လမ်းကြောင်းနှင့် ကြာချိန် မစစ်ရသေး')}</p></div>
  <aside className="panel">
   <Trip lang={lang} cart={cart} onRemove={onRemove} onBrowse={onBrowse} onRoute={R}/>
   {route&&geoReady&&<div className="tool-card">
    <div className="results-head"><h2>{tr(lang,'도로 이동시간','Road travel times','လမ်းခရီးကြာချိန်')}</h2><button className="secondary" disabled={roadBusy} onClick={roadTimes}>{roadBusy?'…':road?tr(lang,'다시 계산','Recalculate','ပြန်တွက်ရန်'):tr(lang,'계산하기','Calculate','တွက်ရန်')}</button></div>
    {roadError&&<p role="alert" className="alert">{roadError}</p>}
    {road&&<ul className="road-list">{road.days.map(d=><li key={d.day}><b>DAY {d.day}</b><span>{d.time_s?tr(lang,'약 ','about ','ခန့် ')+km(d.distance_m)+' · '+minutes(d.time_s):tr(lang,'이동 없음','No transfer','ခရီးမရှိ')}</span></li>)}</ul>}
    <p className="fine">{tr(lang,'자동차 기준 지도 추정치예요. 교통·도로 통제·안전 상황은 반영되지 않았어요. © OpenStreetMap, Geoapify','Driving estimates from map data. Traffic, closures and safety are not included. © OpenStreetMap, Geoapify','ယာဉ်ဖြင့် ခန့်မှန်းချိန်သာ။ ယာဉ်ကြော၊ လုံခြုံရေး မပါဝင်ပါ။')}</p>
   </div>}
   {cart.length>0&&<div className="tool-card">
    <div className="results-head"><h2>{tr(lang,'일정 공유','Share this trip','ခရီးစဉ်မျှဝေရန်')}</h2><button className="secondary" disabled={shareBusy} onClick={share}>{shareBusy?'…':tr(lang,'링크 만들기','Create link','လင့်ခ်ဖန်တီးရန်')}</button></div>
    {shareError&&<p role="alert" className="alert">{shareError}</p>}
    {shareUrl&&<div className="ask-row"><label className="grow">{tr(lang,'공유 링크','Share link','မျှဝေလင့်ခ်')}<input readOnly value={shareUrl} onFocus={e=>e.currentTarget.select()}/></label><button className="secondary" onClick={()=>navigator.clipboard?.writeText(shareUrl).then(()=>COPIED(true)).catch(()=>{})}>{copied?tr(lang,'복사됨 ✓','Copied ✓','ကူးပြီး ✓'):tr(lang,'복사','Copy','ကူးရန်')}</button></div>}
    <p className="fine">{tr(lang,'링크를 아는 누구나 이 일정의 장소와 순서를 볼 수 있어요. 이름·연락처는 저장하지 않으며, 무료 체험판이라 30일 안에 사라질 수 있어요.','Anyone with the link can see these places and their order. No names or contact details are stored; in this free preview links can disappear within 30 days.','လင့်ခ်ရှိသူတိုင်း ကြည့်နိုင်သည်။ ရက် ၃၀ အတွင်း ပျောက်နိုင်သည်။')}</p>
   </div>}
   <button className="next-btn" disabled={!cart.length} onClick={onNext}>{tr(lang,'준비하기','Prepare','ပြင်ဆင်ရန်')} →</button>
   <button className="secondary" disabled={!cart.length} onClick={onClear}>{tr(lang,'이 기기 일정 전체 삭제','Delete device trip','ဤစက်ရှိခရီးစဉ်ဖျက်ရန်')}</button>
  </aside>
 </section>
}

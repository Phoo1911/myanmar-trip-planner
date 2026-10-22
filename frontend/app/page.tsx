"use client";
import {useEffect,useState} from 'react';
import Discover from './Discover';
import PlanStep from './PlanStep';
import Prepare from './Prepare';
import {CART_KEY,DRAFT_KEY,parsePlaces,signature,type TripSpot} from './trip-storage';
type Lang='ko'|'en'|'my';
type Step='input'|'plan'|'prepare';
const api=process.env.NEXT_PUBLIC_API_URL||'/api';
const tr=(l:Lang,ko:string,en:string,my:string)=>({ko,en,my}[l]);
const ADVICE='https://www.gov.uk/foreign-travel-advice/myanmar';

export default function Home(){
 const[lang,L]=useState<Lang>('ko'),[step,T]=useState<Step>('input'),[cart,CART]=useState<TripSpot[]>([]),[notice,NOTICE]=useState(''),[noticeGo,NGO]=useState(false);
 const[storageReady,STORAGE]=useState(false),[storageError,STORAGEERROR]=useState(false);
 const[safety,S]=useState<{source:string;checked_at:string;message:Record<Lang,string>}|null>(null);
 const[shared,SHARED]=useState<{places:TripSpot[];days:{day:number;stop_ids:string[]}[]|null}|null>(null);
 useEffect(()=>{try{CART(parsePlaces(localStorage.getItem(CART_KEY)))}catch{STORAGEERROR(true)}STORAGE(true)},[]);
 useEffect(()=>{if(!storageReady)return;try{localStorage.setItem(CART_KEY,JSON.stringify(parsePlaces(JSON.stringify(cart))));STORAGEERROR(false)}catch{STORAGEERROR(true)}},[cart,storageReady]);
 useEffect(()=>{document.documentElement.lang=lang},[lang]);
 useEffect(()=>{const a=new AbortController();fetch(api+'/safety',{signal:a.signal}).then(r=>r.ok?r.json():Promise.reject()).then(S).catch(()=>{});return()=>a.abort()},[]);
 useEffect(()=>{window.scrollTo(0,0)},[step]);
 useEffect(()=>{const id=new URLSearchParams(location.search).get('trip');if(!id)return;const a=new AbortController();
  fetch(api+'/trips/'+encodeURIComponent(id),{signal:a.signal}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{const places=parsePlaces(JSON.stringify(d.places));if(!places.length)throw Error();SHARED({places,days:d.draft?.route||null})})
   .catch(()=>{if(!a.signal.aborted){NGO(false);NOTICE(tr(lang,'공유 링크가 만료됐거나 찾을 수 없어요.','The share link has expired or cannot be found.','မျှဝေလင့်ခ် သက်တမ်းကုန် သို့မဟုတ် မတွေ့ပါ။'))}});return()=>a.abort()},[]);
 useEffect(()=>{if(!notice){NGO(false);return}const t=setTimeout(()=>NOTICE(''),6000);return()=>clearTimeout(t)},[notice]);

 function add(spots:TripSpot[]){
  if(spots.filter(p=>!cart.some(old=>old.id===p.id)).length>24-cart.length){NGO(false);NOTICE(tr(lang,'최대 24곳까지 저장할 수 있습니다. 일부 장소만 선택해 주세요.','Choose fewer places. A trip can hold 24 places.','၂၄ နေရာအထိသာ သိမ်းနိုင်သည်။'));return}
  CART(old=>{const all=new globalThis.Map(old.map(p=>[p.id,p]));spots.forEach(p=>{const existing=all.get(p.id);all.set(p.id,{...p,references:[...new Set([...(existing?.references||[]),...(p.references||[])])].slice(0,8)})});return [...all.values()].slice(0,24)});
  NGO(true);NOTICE(spots.some(p=>p.coordinate_scope==='city_centre')?tr(lang,'담았어요. 도시 중심점은 실제 방문 지점이 아니니 확인해 주세요.','Added. City centres are not actual venues; check them.','ထည့်ပြီး။ မြို့လယ်သည် လည်ပတ်နေရာမဟုတ်ပါ။'):tr(lang,'내 여행에 담았어요.','Added to your trip.','ခရီးစဉ်ထဲ ထည့်ပြီး။'));
 }
 function remove(id:string){CART(old=>old.filter(p=>p.id!==id));try{localStorage.removeItem(DRAFT_KEY)}catch{}}
 function clear(){CART([]);try{localStorage.removeItem(DRAFT_KEY)}catch{};NGO(false);NOTICE(tr(lang,'이 기기의 장소와 일정을 삭제했습니다.','Device places and draft deleted.','ဤစက်ရှိ အစီအစဉ်ဖျက်ပြီး။'))}
 function go(next:Step){NOTICE('');NGO(false);T(next)}
 function dismissShared(){SHARED(null);history.replaceState(null,'',location.pathname)}
 function loadShared(){
  if(!shared)return;const{places,days}=shared;
  try{if(days){const byId=new globalThis.Map(places.map(p=>[p.id,p]));const route={days:days.map(d=>({day:d.day,stops:d.stop_ids.map(id=>byId.get(id)!).filter(Boolean)}))};
   localStorage.setItem(DRAFT_KEY,JSON.stringify({version:1,signature:signature(places,days.length),days:days.length,route,savedAt:new Date().toISOString()}))}else localStorage.removeItem(DRAFT_KEY)}catch{}
  CART(places);dismissShared();go('plan');
 }

 const steps:[Step,string][]=[['input',tr(lang,'입력','Find','ရှာရန်')],['plan',tr(lang,'지도·일정','Map & plan','မြေပုံ·အစီအစဉ်')],['prepare',tr(lang,'준비','Prepare','ပြင်ဆင်ရန်')]];
 const at=steps.findIndex(([s])=>s===step);
 return <main className="onestop">
  <header className="topbar">
   <a href="/" className="brand">◈ Myanmar Journey</a>
   <nav className="stepper" aria-label={tr(lang,'여행 단계','Trip steps','ခရီးစဉ်အဆင့်များ')}>{steps.map(([s,label],i)=><button key={s} aria-current={step===s?'step':undefined} onClick={()=>go(s)}><span className="step-num">{i<at?'✓':i+1}</span>{label}{s==='plan'&&cart.length>0&&<span className="count">{cart.length}</span>}</button>)}</nav>
   <select aria-label="Language" value={lang} onChange={e=>L(e.target.value as Lang)}><option value="ko">한국어</option><option value="en">English</option><option value="my">မြန်မာ</option></select>
  </header>
  <div className="notice-bar">
   {process.env.NEXT_PUBLIC_DEMO_MODE==='true'&&<span>{tr(lang,'무료 체험판 · 실제 예약·결제 없음 · 실고객 정보를 넣지 마세요 · DB는 30일 후 만료','Free preview · no real bookings or payments · no real customer data · database expires after 30 days','အခမဲ့စမ်းသပ်စနစ် · အမှန်တကယ်ဘွတ်ကင်မရှိ · ဖောက်သည်ဒေတာ မထည့်ပါနှင့်')}</span>}
   <details><summary>{tr(lang,'출발 전 미얀마 지역별 여행경보를 확인하세요','Check Myanmar regional travel advice before you go','မထွက်ခွာမီ ဒေသအလိုက်သတိပေးချက်ကိုစစ်ပါ')} {safety?.checked_at&&'· '+safety.checked_at}</summary><p>{safety?.message[lang]} <a href={safety?.source||ADVICE} target="_blank" rel="noreferrer">{tr(lang,'공식 출처','Official source','တရားဝင်ရင်းမြစ်')} ↗</a></p></details>
  </div>
  {shared&&<div className="shared-banner" role="status"><span>{tr(lang,'공유받은 일정이 있어요','A trip was shared with you','မျှဝေထားသော ခရီးစဉ်ရှိသည်')} · {shared.places.length}{tr(lang,'곳',' places',' နေရာ')}{cart.length>0&&' · '+tr(lang,'불러오면 이 기기의 현재 일정은 바뀝니다','Loading replaces the trip on this device','ဖွင့်လျှင် လက်ရှိခရီးစဉ် အစားထိုးမည်')}</span><button onClick={loadShared}>{tr(lang,'이 일정 불러오기','Load this trip','ဤခရီးစဉ်ဖွင့်ရန်')}</button><button className="secondary" onClick={dismissShared}>{tr(lang,'닫기','Dismiss','ပိတ်ရန်')}</button></div>}
  {storageError&&<p role="alert" className="flash">{tr(lang,'브라우저 저장소를 사용할 수 없습니다. 새로고침하면 담은 장소가 사라질 수 있습니다.','Browser storage unavailable. Places may be lost on reload.','ဘရောက်ဇာတွင် သိမ်းမရပါ။')}</p>}
  {notice&&<p role="status" className="flash">{notice}{step==='input'&&noticeGo&&<button className="secondary" onClick={()=>go('plan')}>{tr(lang,'지도·일정으로','Go to map & plan','မြေပုံ·အစီအစဉ်သို့')} →</button>}</p>}
  {step==='input'&&<Discover lang={lang} cart={cart} onAdd={add} onRemove={remove} onNext={()=>go('plan')}/>}
  {step==='plan'&&storageReady&&<PlanStep lang={lang} cart={cart} onRemove={remove} onBrowse={()=>go('input')} onNext={()=>go('prepare')} onClear={clear}/>}
  {step==='prepare'&&storageReady&&<Prepare lang={lang} cart={cart} onPlan={()=>go('plan')} safetySource={safety?.source||ADVICE}/>}
  <footer className="site-footer">Myanmar Journey · {tr(lang,'관리자 승인은 요청 접수 승인입니다. 공급사 예약 확정이나 결제가 아닙니다.','Approval accepts the inquiry only. It does not confirm a supplier booking or payment.','လက်ခံခြင်းသည် မေးမြန်းမှုကိုသာ လက်ခံခြင်းဖြစ်သည်။')}</footer>
 </main>
}

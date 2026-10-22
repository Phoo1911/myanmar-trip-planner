"use client";
import {useEffect,useRef,useState} from 'react';
import type {TripSpot} from './trip-storage';
type Lang='ko'|'en'|'my';
type Source={id:string;text:string;url:string;similarity:number};
type Result={summary:string;recommendations:{place:TripSpot;reason:string;sources:Source[]}[];discoveries:Source[];warning:string|null};
const tr=(l:Lang,ko:string,en:string,my:string)=>({ko,en,my}[l]);
export default function AIRecommendations({lang,region,onAddAll}:{lang:Lang;region:string;onAddAll:(p:TripSpot[])=>void}){
 const [query,Q]=useState(''),[ready,K]=useState<boolean|null>(null),[busy,B]=useState(false),[result,R]=useState<Result|null>(null),[error,E]=useState('');
 const active=useRef<AbortController|null>(null);
 useEffect(()=>{const a=new AbortController();fetch('/api/discovery/ai-status',{signal:a.signal}).then(r=>r.ok?r.json():Promise.reject()).then(d=>K(d.configured)).catch(()=>{if(!a.signal.aborted)K(false)});return()=>a.abort()},[]);
 useEffect(()=>{active.current?.abort();R(null);B(false);E('');return()=>active.current?.abort()},[lang,region]);
 async function recommend(){active.current?.abort();const a=new AbortController();active.current=a;B(true);R(null);E('');
  try{const r=await fetch('/api/discovery/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,language:lang,region_id:region}),signal:AbortSignal.any([a.signal,AbortSignal.timeout(105000)])});
   // A 503 with Retry-After is a transient provider overload; a bare 503 means the key is not configured.
   if(!r.ok)throw Error(r.status===503&&r.headers.get('Retry-After')?'busy':String(r.status));const data=await r.json();if(!a.signal.aborted)R(data);
  }catch(e){if(!a.signal.aborted)E(e instanceof Error&&e.message==='429'?tr(lang,'무료 AI 사용 한도에 도달했습니다. 잠시 후 다시 시도하세요.','Free AI quota reached. Try later.','အခမဲ့ AI ကန့်သတ်ချက်ပြည့်ပါပြီ။ နောက်မှပြန်စမ်းပါ။'):e instanceof Error&&e.message==='busy'?tr(lang,'AI 서비스가 일시적으로 혼잡합니다. 30초 후 다시 시도해 주세요.','The AI service is temporarily busy. Please retry in 30 seconds.','AI ဝန်ဆောင်မှု ယာယီ အလုပ်များနေပါသည်။ စက္ကန့် ၃၀ အကြာတွင် ပြန်စမ်းပါ။'):e instanceof Error&&e.message==='503'?tr(lang,'AI 연결을 설정하고 있습니다.','AI connection is being configured.','AI ချိတ်ဆက်မှု ပြင်ဆင်နေပါသည်။'):tr(lang,'추천을 만들지 못했습니다. 다시 시도해 주세요.','Could not generate recommendations. Please retry.','အကြံပြုချက် မဖန်တီးနိုင်ပါ။ ပြန်စမ်းပါ။'))}finally{if(!a.signal.aborted)B(false)}
 }
 const ideas=lang==='ko'?['양곤에서 불교 건축과 시장을 보고 싶어요','사원 중심으로 여유로운 여행을 하고 싶어요']:lang==='en'?['Buddhist architecture and markets in Yangon','A relaxed trip focused on temples']:['ရန်ကုန်မှာ ဘုရားတွေနဲ့ ဈေးတွေကို လည်ချင်တယ်','ဘုရားတွေကို အေးအေးဆေးဆေး လည်ချင်တယ်'];
 return <section className="content-trip ai-recommendations"><span className="eyebrow">AI TRAVEL MATCH</span><h3>{tr(lang,'어떤 여행을 하고 싶으세요?','What kind of trip do you want?','ဘယ်လိုခရီးမျိုး သွားချင်ပါသလဲ။')}</h3><p>{tr(lang,'장소 이름을 몰라도 괜찮아요. 취향을 말하면 의미가 가까운 자료를 찾아 추천해 드립니다.','Describe your interests without knowing place names. AI retrieves related evidence and suggests places.','နေရာအမည် မသိလည်း ရပါတယ်။ စိတ်ဝင်စားမှုကို ပြောပြပါ။ AI က သက်ဆိုင်သောအချက်အလက်များ ရှာပြီး နေရာအကြံပြုပေးမည်။')}</p>
 <form onSubmit={e=>{e.preventDefault();recommend()}}><label className="block mt-3">{tr(lang,'여행 취향 · 한국어 / English / မြန်မာ','Travel preferences · 한국어 / English / မြန်မာ','ခရီးသွားစိတ်ဝင်စားမှု · 한국어 / English / မြန်မာ')}<textarea value={query} onChange={e=>{active.current?.abort();B(false);R(null);E('');Q(e.target.value)}} rows={3} minLength={3} maxLength={500} required disabled={busy} placeholder={ideas[0]}/></label>
 <div className="flex flex-wrap gap-2 my-3">{ideas.map(idea=><button type="button" key={idea} disabled={busy} onClick={()=>{Q(idea);R(null);E('')}}>{idea}</button>)}</div>
 <p className="text-xs text-slate-600 mb-3">{tr(lang,'입력한 취향과 공개 출처를 Google AI로 처리합니다. 개인정보는 입력하지 마세요.','Your preferences and public evidence are processed by Google AI. Do not enter private information.','သင့်စိတ်ဝင်စားမှုနှင့် အများပြည်သူရင်းမြစ်များကို Google AI ဖြင့် လုပ်ဆောင်ပါသည်။ ကိုယ်ရေးအချက်အလက် မထည့်ပါနှင့်။')}</p>
 <button disabled={busy||!ready||query.trim().length<3}>{busy?tr(lang,'의미를 검색하고 추천하는 중…','Retrieving and recommending…','အဓိပ္ပာယ်အလိုက် ရှာဖွေအကြံပြုနေသည်…'):tr(lang,'AI 맞춤 추천 받기','Get AI recommendations','AI အကြံပြုချက်ရယူရန်')}</button></form>
 {ready===false&&<p role="status">{tr(lang,'다국어 AI 연결 준비 중입니다. 아래 콘텐츠 검색은 사용할 수 있습니다.','Multilingual AI setup is pending. Content search below is available.','ဘာသာစကားစုံ AI ချိတ်ဆက်မှု ပြင်ဆင်နေသည်။ အောက်တွင် အကြောင်းအရာ ရှာနိုင်ပါသည်။')}</p>}
 {error&&<p role="alert">{error}</p>}
 {result&&<div aria-live="polite"><p className="my-4">{result.summary}</p>{result.recommendations.length===0&&<p>{tr(lang,'현재 출처에서 취향에 맞는 지도 장소를 추천하기 어렵습니다.','Current evidence does not support a mapped recommendation.','လက်ရှိရင်းမြစ်များဖြင့် သင့်လျော်သော မြေပုံနေရာ မအကြံပြုနိုင်ပါ။')}</p>}
 <div className="content-results">{result.recommendations.map(rec=><article key={rec.place.id}><h4>{rec.place.name[lang]}</h4><p>{rec.reason}</p><details><summary>{tr(lang,'추천 근거 보기','View recommendation evidence','အကြံပြုချက် ရင်းမြစ်ကြည့်ရန်')}</summary>{rec.sources.map(s=><p key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.text} ↗</a></p>)}</details><button onClick={()=>onAddAll([{...rec.place,references:rec.sources.map(s=>s.url)}])}>{tr(lang,'일정에 담기','Add to trip','ခရီးစဉ်ထဲထည့်ရန်')}</button></article>)}</div>
 {result.recommendations.length>0&&<button className="mt-3" onClick={()=>onAddAll(result.recommendations.map(r=>({...r.place,references:r.sources.map(s=>s.url)})))}>{tr(lang,'추천 장소 모두 일정에 담기','Add all recommendations to trip','အကြံပြုနေရာအားလုံး ခရီးစဉ်ထဲထည့်ရန်')}</button>}
 {result.discoveries.length>0&&<details className="mt-4"><summary>{tr(lang,'함께 찾은 콘텐츠 · 위치 확인 필요','Related discoveries · location check needed','သက်ဆိုင်ရာအကြောင်းအရာ · တည်နေရာစစ်ဆေးရန်လိုသည်')}</summary>{result.discoveries.map(s=><p key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.text} ↗</a></p>)}</details>}
 {result.warning&&<p>{tr(lang,'콘텐츠 검색이 일시 중단되어 지도 자료만 사용했습니다.','Social search unavailable; using catalog evidence only.','အကြောင်းအရာရှာဖွေမှု မရသဖြင့် မြေပုံရင်းမြစ်သာ သုံးထားသည်။')}</p>}
 <p className="text-xs mt-4">{tr(lang,'AI 제안 · 등록된 명소 범위가 제한적입니다. 실제 이동 경로·영업·인기·가격·안전은 확인되지 않았습니다.','AI suggestions from limited coverage. Road routes, opening, popularity, prices and safety are unverified.','AI အကြံပြုချက် · နေရာအချက်အလက် အကန့်အသတ်ရှိသည်။ လမ်းကြောင်း၊ ဖွင့်ချိန်၊ လူကြိုက်များမှု၊ ဈေးနှုန်းနှင့် လုံခြုံရေး မစစ်ရသေးပါ။')}</p></div>}
 </section>
}

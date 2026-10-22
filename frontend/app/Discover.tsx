"use client";
import {useEffect,useMemo,useRef,useState} from 'react';
import dynamic from 'next/dynamic';
import type {TripSpot} from './trip-storage';
const Map=dynamic(()=>import('./Map'),{ssr:false});
type Lang='ko'|'en'|'my';
type Spot=TripSpot&{category:string;source:string;place_id?:string;source_kind?:string;checked_at?:string;region_id?:string;region_name?:string;evidence?:{url:string}};
type Source={id:string;text:string;url:string};
type AIResult={summary:string;recommendations:{place:TripSpot;reason:string;sources:Source[]}[];discoveries:Source[];warning:string|null;auto_places?:{place:TripSpot;reason:string;sources:Source[]}[];unlocated?:{name:string;reason:string;source:Source}[];geocoding?:string};
type Candidate={place:TripSpot;source_url:string|null;matched_name:string};
type Item={title:string;excerpt:string;url:string;places:Candidate[];collected_at:string};
const api=process.env.NEXT_PUBLIC_API_URL||'/api';
const tr=(l:Lang,ko:string,en:string,my:string)=>({ko,en,my}[l]);
const LEGACY_REGION:Record<string,string>={yangon:'MM.17',bagan:'MM.08',inle:'MM.11'};
const LEGACY_NAMES:Record<string,string>={yangon:'양곤 Yangon ရန်ကုန်',bagan:'바간 Bagan ပုဂံ',inle:'인레 Inle Nyaungshwe အင်းလေး'};
const CATEGORIES=['cafe','restaurant','heritage','viewpoint','city'];
const categoryName=(l:Lang,k:string)=>{const i=CATEGORIES.indexOf(k);return i<0?k:tr(l,['카페','맛집','문화유산','전망','도시 중심'][i],['Café','Restaurant','Heritage','Viewpoint','City centre'][i],['ကော်ဖီဆိုင်','စားသောက်ဆိုင်','အမွေအနှစ်','ရှုခင်း','မြို့လယ်'][i])};

// Step 1: one input for preferences, post links and pasted text, with the map and the trip always in view.
export default function Discover({lang,cart,onAdd,onRemove,onNext}:{lang:Lang;cart:TripSpot[];onAdd:(spots:TripSpot[])=>void;onRemove:(id:string)=>void;onNext:()=>void}){
 const[spots,SPOTS]=useState<Spot[]>([]),[regions,REGIONS]=useState<{id:string;name:string}[]>([]),[loading,LOADING]=useState(true),[loadError,LOADERROR]=useState(false),[attempt,ATTEMPT]=useState(0);
 const[mode,MODE]=useState<'ask'|'search'>('ask'),[region,G]=useState(''),[q,Q]=useState(''),[category,C]=useState(''),[selected,D]=useState('');
 const[text,T]=useState(''),[busy,B]=useState(false),[aiReady,K]=useState<boolean|null>(null),[searchReady,SK]=useState(false);
 const[ai,AI]=useState<AIResult|null>(null),[aiError,AIERR]=useState(''),[matches,M]=useState<Candidate[]>([]),[checked,CHECK]=useState<string[]>([]),[resolveMsg,RMSG]=useState(''),[asked,ASKED]=useState(false);
 const[topic,TOPIC]=useState('Myanmar travel itinerary places'),[items,I]=useState<Item[]>([]),[browseBusy,BB]=useState(false),[browseMsg,BMSG]=useState('');
 const run=useRef<AbortController|null>(null),browse=useRef<AbortController|null>(null);
 const saved=new Set(cart.map(p=>p.id));const full=cart.length>=24;

 useEffect(()=>{let active=true;const controller=new AbortController();LOADERROR(false);LOADING(true);
  (async()=>{for(let n=0;n<3;n++){try{
   const signal=AbortSignal.any([controller.signal,AbortSignal.timeout(12000)]);
   const response=await fetch(api+'/hotspots',{cache:'no-store',signal});if(!response.ok)throw Error(String(response.status));
   const data=await response.json();if(!Array.isArray(data))throw Error('Invalid places');
   const nr=await fetch(api+'/discovery/regions',{cache:'no-store',signal});if(!nr.ok)throw Error('Regions unavailable');const national=await nr.json();
   if(active){REGIONS(national.regions);SPOTS([...data,...national.cities]);LOADING(false)}return;
  }catch{if(!active)return;if(n<2)await new Promise(resolve=>setTimeout(resolve,1500*(n+1)))}}
  if(active){LOADERROR(true);LOADING(false)}})();
  return()=>{active=false;controller.abort()};
 },[attempt]);
 useEffect(()=>{const a=new AbortController();
  fetch(api+'/discovery/ai-status',{signal:a.signal}).then(r=>r.ok?r.json():Promise.reject()).then(d=>K(!!d.configured)).catch(()=>{if(!a.signal.aborted)K(false)});
  fetch(api+'/discovery/status',{signal:a.signal}).then(r=>r.ok?r.json():Promise.reject()).then(d=>SK(d.search==='configured')).catch(()=>{});
  return()=>{a.abort();run.current?.abort();browse.current?.abort()}},[]);
 useEffect(()=>{run.current?.abort();B(false);AI(null);AIERR('')},[lang]);

 async function recommend(query:string,signal:AbortSignal){
  try{const r=await fetch(api+'/discovery/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,language:lang,region_id:region}),signal:AbortSignal.any([signal,AbortSignal.timeout(105000)])});
   // A 503 with Retry-After is a transient provider overload; a bare 503 means the key is not configured.
   if(!r.ok)throw Error(r.status===503&&r.headers.get('Retry-After')?'busy':String(r.status));const data=await r.json();if(!signal.aborted)AI(data);
  }catch(e){if(signal.aborted)return;const code=e instanceof Error?e.message:'';
   AIERR(code==='429'?tr(lang,'무료 AI 사용 한도에 도달했습니다. 잠시 후 다시 시도하세요.','Free AI quota reached. Try later.','အခမဲ့ AI ကန့်သတ်ချက်ပြည့်ပါပြီ။ နောက်မှပြန်စမ်းပါ။'):code==='busy'?tr(lang,'AI 서비스가 일시적으로 혼잡합니다. 30초 후 다시 시도해 주세요.','The AI service is temporarily busy. Please retry in 30 seconds.','AI ဝန်ဆောင်မှု ယာယီ အလုပ်များနေပါသည်။ စက္ကန့် ၃၀ အကြာတွင် ပြန်စမ်းပါ။'):code==='503'?tr(lang,'AI 연결을 설정하고 있습니다.','AI connection is being configured.','AI ချိတ်ဆက်မှု ပြင်ဆင်နေပါသည်။'):tr(lang,'AI 추천을 만들지 못했습니다. 다시 시도해 주세요.','Could not generate AI recommendations. Please retry.','AI အကြံပြုချက် မဖန်တီးနိုင်ပါ။ ပြန်စမ်းပါ။'))}
 }
 async function resolve(body:string,url:string,signal:AbortSignal){
  try{const r=await fetch(api+'/discovery/resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:body,source_url:url}),signal:AbortSignal.any([signal,AbortSignal.timeout(25000)])});
   if(!r.ok)throw Error(String(r.status));const data=await r.json();if(signal.aborted)return;
   M(data.matches);CHECK(data.matches.filter((p:Candidate)=>p.place.coordinate_scope!=='city_centre').map((p:Candidate)=>p.place.id));
   if(data.ambiguous_names?.length)RMSG(tr(lang,'동명이칭은 자동 선택하지 않았습니다.','Ambiguous names were not selected.','အမည်တူနေရာများ အလိုအလျောက်မရွေးပါ။'));
  }catch(e){if(signal.aborted)return;RMSG(e instanceof Error&&e.message==='422'?tr(lang,'공개 게시물 주소를 확인하세요. Facebook·사진 게시물은 본문을 붙여넣어 주세요.','Check the public post link. For Facebook or photo posts, paste the text.','အများပြည်သူပို့စ်လင့်ခ်ကို စစ်ပါ။ Facebook သို့မဟုတ် ဓာတ်ပုံပို့စ်အတွက် စာသားထည့်ပါ။'):tr(lang,'글에서 장소를 찾지 못했습니다. 다시 시도해 주세요.','Could not read places from the text. Please retry.','စာသားမှ နေရာ မရှာနိုင်ပါ။ ပြန်စမ်းပါ။'))}
 }
 async function submit(){
  const raw=text.trim();if(raw.length<3)return;
  run.current?.abort();const a=new AbortController();run.current=a;
  B(true);ASKED(true);AI(null);AIERR('');M([]);CHECK([]);RMSG('');
  const url=(raw.match(/https?:\/\/\S+/)||[''])[0];const body=raw.replace(url,'').trim();
  if(new TextEncoder().encode(body).length>12000){RMSG(tr(lang,'글을 조금 줄여주세요. 최대 12KB입니다.','Please shorten the text to 12KB.','စာသားကို 12KB အောက်လျှော့ပါ။'));B(false);return}
  const jobs:Promise<void>[]=[resolve(body.slice(0,4000),url,a.signal)];
  if(aiReady&&body.length>=3&&body.length<=500)jobs.push(recommend(body,a.signal));
  else if(aiReady&&body.length>500)AIERR(tr(lang,'AI 추천은 500자 이하 취향 문장에서 동작해요. 이번에는 글에 나온 장소만 찾았어요.','AI suggestions need a preference under 500 characters. This time only places named in the text were matched.','AI အကြံပြုချက်အတွက် စာလုံး ၅၀၀ အောက်သာ။ ယခု စာထဲပါနေရာများကိုသာ ရှာထားသည်။'));
  await Promise.allSettled(jobs);if(!a.signal.aborted)B(false);
 }
 async function discover(){
  browse.current?.abort();const a=new AbortController();browse.current=a;BB(true);BMSG('');I([]);
  try{const r=await fetch(api+'/discovery/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:topic,region_id:region}),signal:AbortSignal.any([a.signal,AbortSignal.timeout(25000)])});
   if(!r.ok)throw Error(String(r.status));const data=await r.json();if(a.signal.aborted)return;I(data.items);
   if(!data.items.length)BMSG(tr(lang,'검색 결과가 없습니다. 다른 주제로 찾아보세요.','No indexed results. Try another topic.','ရလဒ်မရှိပါ။ အကြောင်းအရာပြောင်းပါ။'));
  }catch(e){if(!a.signal.aborted)BMSG(e instanceof Error&&e.message==='429'?tr(lang,'무료 검색 한도에 도달했습니다.','Free search limit reached.','အခမဲ့ရှာဖွေမှု ကန့်သတ်ချက်ပြည့်ပါပြီ။'):tr(lang,'콘텐츠를 불러오지 못했습니다.','Could not load content.','အကြောင်းအရာ မဖတ်နိုင်ပါ။'))}finally{if(!a.signal.aborted)BB(false)}
 }

 const shown=useMemo(()=>spots.filter(p=>(!category||p.category===category)&&(!region||(p.region_id||LEGACY_REGION[p.place_id||''])===region)&&(Object.values(p.name).join(' ')+' '+p.place_id+' '+(p.region_name||'')+' '+(LEGACY_NAMES[p.place_id||'']||'')).toLowerCase().includes(q.trim().toLowerCase())),[spots,category,region,q]);
 const found=useMemo(()=>{const all=new globalThis.Map<string,TripSpot>();ai?.recommendations.forEach(r=>all.set(r.place.id,r.place));ai?.auto_places?.forEach(r=>all.set(r.place.id,r.place));matches.forEach(m=>all.set(m.place.id,m.place));return [...all.values()]},[ai,matches]);
 const mapPlaces=mode==='search'?shown:found.length?found:shown;
 const unverified=tr(lang,'미검증','unverified','မစစ်ရသေး');
 const labels=useMemo(()=>Object.fromEntries(found.map((p,i)=>[p.id,(i+1)+' '+p.name[lang]+(p.auto_located?' · '+unverified:'')])),[found,lang,unverified]);
 const active=mapPlaces.some(p=>p.id===selected)?selected:undefined;
 useEffect(()=>{if(selected)document.getElementById('pick-'+selected)?.scrollIntoView({block:'nearest',behavior:'smooth'})},[selected]);
 const picked=matches.filter(p=>checked.includes(p.place.id));
 const ideas=lang==='ko'?['양곤에서 불교 건축과 시장을 보고 싶어요','사원 중심으로 여유로운 여행을 하고 싶어요']:lang==='en'?['Buddhist architecture and markets in Yangon','A relaxed trip focused on temples']:['ရန်ကုန်မှာ ဘုရားတွေနဲ့ ဈေးတွေကို လည်ချင်တယ်','ဘုရားတွေကို အေးအေးဆေးဆေး လည်ချင်တယ်'];
 const addButton=(p:TripSpot,references:string[]=[])=><button className={saved.has(p.id)?'pick-btn on':'pick-btn'} disabled={saved.has(p.id)||full} aria-pressed={saved.has(p.id)} onClick={()=>onAdd([{...p,references}])}>{saved.has(p.id)?tr(lang,'담음 ✓','Added ✓','ထည့်ပြီး ✓'):tr(lang,'담기','Add','ထည့်ရန်')}</button>;

 return <section className="stage">
  <div className="panel">
   <div className="mode-tabs" role="tablist" aria-label={tr(lang,'찾는 방법','How to find','ရှာနည်း')}>
    <button role="tab" aria-selected={mode==='ask'} onClick={()=>MODE('ask')}>{tr(lang,'추천·가져오기','Suggest & import','အကြံပြု·ထည့်ရန်')}</button>
    <button role="tab" aria-selected={mode==='search'} onClick={()=>MODE('search')}>{tr(lang,'장소 검색','Search places','နေရာရှာရန်')}</button>
   </div>
   {mode==='ask'?<>
    <div><h1 className="step-title">{tr(lang,'어떤 여행을 원하세요?','What kind of trip do you want?','ဘယ်လိုခရီးမျိုး သွားချင်ပါသလဲ။')}</h1><p className="step-sub">{tr(lang,'취향을 말하거나, 본 SNS 링크·글을 붙여넣으세요. 한 번에 장소를 찾아 지도에 올려 드려요.','Describe what you like, or paste a post link or text. We find the places and put them on the map.','စိတ်ဝင်စားမှုကို ပြောပါ သို့မဟုတ် ပို့စ်လင့်ခ်/စာသား ထည့်ပါ။ နေရာများကို မြေပုံပေါ် တင်ပေးမည်။')}</p></div>
    <form className="ask-box" onSubmit={e=>{e.preventDefault();submit()}}>
     <label htmlFor="ask">{tr(lang,'취향 · 링크 · 글','Preference · link · text','စိတ်ဝင်စားမှု · လင့်ခ် · စာသား')}</label>
     <textarea id="ask" value={text} rows={3} maxLength={4000} disabled={busy} placeholder={ideas[0]} onChange={e=>{run.current?.abort();B(false);T(e.target.value)}}/>
     <div className="ask-row">
      <label className="region-pick">{tr(lang,'지역','Region','ဒေသ')}<select value={region} onChange={e=>G(e.target.value)}><option value="">{tr(lang,'전체','All','အားလုံး')}</option>{regions.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
      <button disabled={busy||text.trim().length<3}>{busy?tr(lang,'찾는 중…','Finding…','ရှာနေသည်…'):tr(lang,'장소 찾기','Find places','နေရာရှာရန်')}</button>
     </div>
    </form>
    <div className="chips">{ideas.map(idea=><button type="button" className="chip" key={idea} disabled={busy} onClick={()=>T(idea)}>{idea}</button>)}<span className="chip muted">{tr(lang,'사진 · 준비 중','Photos · coming soon','ဓာတ်ပုံ · မကြာမီ')}</span></div>
    <p className="fine">{tr(lang,'취향 문장은 Google AI로 처리합니다. 개인정보나 비공개 글은 넣지 마세요.','Preferences are processed by Google AI. Do not enter private information or private posts.','စိတ်ဝင်စားမှုကို Google AI ဖြင့် လုပ်ဆောင်သည်။ ကိုယ်ရေးအချက်အလက် မထည့်ပါနှင့်။')}{aiReady===false&&' '+tr(lang,'AI 추천은 연결 준비 중이며, 글에서 장소 찾기는 사용할 수 있어요.','AI suggestions are not connected yet; matching places in text still works.','AI မချိတ်ဆက်ရသေးပါ။ စာသားမှ နေရာရှာနိုင်သည်။')}</p>
    {aiError&&<p role="alert" className="alert">{aiError}</p>}{resolveMsg&&<p role="status" className="fine">{resolveMsg}</p>}
    {ai&&<div aria-live="polite" className="results">
     <div className="results-head"><h2>{tr(lang,'AI 추천','AI suggestions','AI အကြံပြုချက်')} {ai.recommendations.length}</h2>{ai.recommendations.length>0&&<button className="link-btn" disabled={full} onClick={()=>onAdd(ai.recommendations.map(r=>({...r.place,references:r.sources.map(s=>s.url)})))}>{tr(lang,'모두 담기','Add all','အားလုံးထည့်ရန်')}</button>}</div>
     <p className="summary">{ai.summary}</p>
     <ol className="cards">{ai.recommendations.map((rec,i)=><li id={'pick-'+rec.place.id} key={rec.place.id} className={'card'+(active===rec.place.id?' active':'')}><button className="num" onClick={()=>D(rec.place.id)} aria-label={tr(lang,'지도에서 보기','Show on map','မြေပုံတွင်ကြည့်ရန်')+' '+rec.place.name[lang]}>{i+1}</button><div className="card-body"><h3>{rec.place.name[lang]}</h3><p>{rec.reason}</p><details><summary>{tr(lang,'근거','Evidence','ရင်းမြစ်')} {rec.sources.length}</summary>{rec.sources.map(s=><p key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.text} ↗</a></p>)}</details></div>{addButton(rec.place,rec.sources.map(s=>s.url))}</li>)}</ol>
     {!!ai.auto_places?.length&&<><div className="results-head"><h2>{tr(lang,'글에서 새로 찾은 장소','New places found in posts','ပို့စ်များမှ နေရာသစ်')} {ai.auto_places.length}</h2>{!full&&<button className="link-btn" onClick={()=>onAdd(ai.auto_places!.map(r=>({...r.place,auto_located:true,references:r.sources.map(s=>s.url)})))}>{tr(lang,'모두 담기','Add all','အားလုံးထည့်ရန်')}</button>}</div>
     <ol className="cards">{ai.auto_places.map((rec,i)=><li id={'pick-'+rec.place.id} key={rec.place.id} className={'card'+(active===rec.place.id?' active':'')}><button className="num" onClick={()=>D(rec.place.id)} aria-label={tr(lang,'지도에서 보기','Show on map','မြေပုံတွင်ကြည့်ရန်')+' '+rec.place.name[lang]}>{ai.recommendations.length+i+1}</button><div className="card-body"><h3>{rec.place.name[lang]} <span className="tag check">{tr(lang,'자동 위치·미검증','Auto-located · unverified','အလိုအလျောက်တည်နေရာ · မစစ်ရသေး')}</span></h3><p>{rec.reason}</p><details><summary>{tr(lang,'근거','Evidence','ရင်းမြစ်')} {rec.sources.length}</summary>{rec.sources.map(s=><p key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.text} ↗</a></p>)}</details></div>{addButton({...rec.place,auto_located:true},rec.sources.map(s=>s.url))}</li>)}</ol>
     <p className="fine">{tr(lang,'글에 나온 이름으로 지도 서비스가 찾은 위치입니다. 같은 이름의 다른 지점일 수 있으니 방문 전에 확인하세요.','Located by a map service from the name in the post. It may be another branch with the same name; check before visiting.','ပို့စ်ထဲမှ အမည်ဖြင့် မြေပုံဝန်ဆောင်မှုက ရှာထားသည်။ မသွားမီ စစ်ပါ။')}</p></>}
     {!!ai.unlocated?.length&&<details className="fine"><summary>{tr(lang,'위치를 찾지 못한 장소','Places without a confirmed location','တည်နေရာ မတွေ့သောနေရာများ')} {ai.unlocated.length}</summary>{ai.unlocated.map(u=><p key={u.name}>{u.name} · <a href={u.source.url} target="_blank" rel="noreferrer">{tr(lang,'출처','Source','ရင်းမြစ်')} ↗</a></p>)}{ai.geocoding==='unavailable'&&<p>{tr(lang,'지도 위치 찾기가 지금 연결되지 않았어요.','Map lookup is not connected right now.','မြေပုံရှာဖွေမှု မချိတ်ဆက်ရသေးပါ။')}</p>}</details>}
     {ai.discoveries.length>0&&<details className="fine"><summary>{tr(lang,'함께 찾은 콘텐츠 · 위치 확인 필요','Related content · location check needed','သက်ဆိုင်ရာအကြောင်းအရာ · တည်နေရာစစ်ရန်')}</summary>{ai.discoveries.map(s=><p key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.text} ↗</a></p>)}</details>}
     {ai.warning&&<p className="fine">{tr(lang,'콘텐츠 검색이 일시 중단되어 지도 자료만 사용했습니다.','Social search unavailable; using map records only.','အကြောင်းအရာရှာဖွေမှု မရသဖြင့် မြေပုံဒေတာသာ သုံးထားသည်။')}</p>}
    </div>}
    {matches.length>0&&<div className="results">
     <div className="results-head"><h2>{tr(lang,'글에서 찾은 장소','Places named in the text','စာသားထဲမှ နေရာများ')} {matches.length}</h2></div>
     <div className="candidates">{matches.map(p=><label key={p.place.id}><input type="checkbox" checked={checked.includes(p.place.id)} onChange={e=>CHECK(old=>e.target.checked?[...old,p.place.id]:old.filter(id=>id!==p.place.id))}/><span>{p.place.name[lang]}{p.place.coordinate_scope==='city_centre'&&<small>{tr(lang,'도시 중심점 · 명소 아님','City centre · not an attraction','မြို့လယ် · လည်ပတ်နေရာမဟုတ်')}</small>}</span>{p.source_url&&<a href={p.source_url} target="_blank" rel="noreferrer">{tr(lang,'원문','Source','မူရင်း')} ↗</a>}</label>)}</div>
     <button disabled={!picked.length||full} onClick={()=>onAdd(picked.map(p=>({...p.place,references:p.source_url?[p.source_url]:[]})))}>{tr(lang,'선택한 장소 담기','Add selected','ရွေးထားသည်များ ထည့်ရန်')} ({picked.length})</button>
    </div>}
    {asked&&!busy&&!aiError&&!ai?.recommendations.length&&!matches.length&&!resolveMsg&&<p className="empty-state">{tr(lang,'맞는 장소를 찾지 못했어요. 모르는 장소를 추측해 지도에 찍지 않습니다. 다른 표현이나 장소 이름으로 시도해 보세요.','No matching places. Unknown locations are never guessed. Try other words or a place name.','ကိုက်ညီသောနေရာ မတွေ့ပါ။ မသိသောတည်နေရာကို မခန့်မှန်းပါ။')}</p>}
    <p className="fine">{tr(lang,'추천은 출처에 근거한 제안입니다. 영업·가격·혼잡도·안전은 확인되지 않았습니다.','Suggestions are grounded in sources. Opening, prices, crowds and safety are unverified.','အကြံပြုချက်များသည် ရင်းမြစ်အခြေခံဖြစ်သည်။ ဖွင့်ချိန်၊ ဈေးနှုန်း၊ လုံခြုံရေး မစစ်ရသေးပါ။')}</p>
    {searchReady&&<details className="browse"><summary>{tr(lang,'공개 여행 콘텐츠 둘러보기','Browse public travel content','အများပြည်သူ ခရီးအကြောင်းအရာ ကြည့်ရန်')}</summary>
     <form className="ask-row" onSubmit={e=>{e.preventDefault();discover()}}><label className="grow">{tr(lang,'주제','Topic','အကြောင်းအရာ')}<input value={topic} minLength={2} maxLength={100} disabled={browseBusy} onChange={e=>TOPIC(e.target.value)}/></label><button disabled={browseBusy||topic.trim().length<2}>{browseBusy?'…':tr(lang,'찾기','Search','ရှာရန်')}</button></form>
     {browseMsg&&<p role="status" className="fine">{browseMsg}</p>}
     {items.map(item=><article key={item.url} className="content-item"><a href={item.url} target="_blank" rel="noreferrer"><h4>{item.title} ↗</h4></a><p>{item.excerpt}</p><div className="chips">{item.places.map(p=><button key={p.place.id} className="chip" disabled={saved.has(p.place.id)||full} onClick={()=>onAdd([{...p.place,references:[item.url]}])}>{saved.has(p.place.id)?'✓ ':'+ '}{p.place.name[lang]}</button>)}</div><small>{tr(lang,'검색 색인 발췌 · 확인일','Search excerpt · retrieved','ရှာဖွေမှုအကျဉ်း · စုဆောင်းရက်')} {item.collected_at.slice(0,10)}</small></article>)}
    </details>}
   </>:<>
    <div><h1 className="step-title">{tr(lang,'장소 직접 찾기','Find places yourself','နေရာကိုယ်တိုင်ရှာရန်')}</h1><p className="step-sub">{shown.length} {tr(lang,'곳 · 지도 자료 기준','places · mapped records','နေရာ · မြေပုံဒေတာ')}</p></div>
    <div className="filters"><label>{tr(lang,'장소 검색','Search places','နေရာရှာရန်')}<input type="search" placeholder={tr(lang,'장소 이름 또는 지역','Place name or region','နေရာအမည် သို့မဟုတ် ဒေသ')} value={q} onChange={e=>Q(e.target.value)}/></label><div className="ask-row"><label className="grow">{tr(lang,'지역','Region','ဒေသ')}<select value={region} onChange={e=>G(e.target.value)}><option value="">{tr(lang,'전체 지역','All regions','ဒေသအားလုံး')}</option>{regions.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label><label className="grow">{tr(lang,'분류','Category','အမျိုးအစား')}<select value={category} onChange={e=>C(e.target.value)}><option value="">{tr(lang,'전체','All','အားလုံး')}</option>{CATEGORIES.map(k=><option key={k} value={k}>{categoryName(lang,k)}</option>)}</select></label></div><button className="link-btn" onClick={()=>{Q('');C('');G('')}}>{tr(lang,'필터 초기화','Clear filters','စစ်ထုတ်မှုဖယ်ရန်')}</button></div>
    {loading&&<p role="status" className="fine">{tr(lang,'장소를 불러오는 중입니다. 서버가 시작 중이면 잠시 걸릴 수 있습니다.','Loading places. The server may need a moment to start.','နေရာများကို ဖတ်နေသည်။')}</p>}
    {loadError&&<div role="alert" className="alert">{tr(lang,'장소를 불러오지 못했습니다.','Could not load places.','နေရာများကို ဖတ်မရပါ။')} <button className="secondary" onClick={()=>ATTEMPT(a=>a+1)}>{tr(lang,'다시 불러오기','Retry','ပြန်ဖတ်ရန်')}</button></div>}
    {!loading&&!loadError&&!shown.length&&<p className="empty-state">{tr(lang,'검색 조건에 맞는 장소가 없습니다. 다른 이름이나 분류로 찾아보세요.','No matching places. Try another name or category.','ကိုက်ညီသော နေရာမရှိပါ။')}</p>}
    <ol className="cards">{shown.map(p=><li id={'pick-'+p.id} key={p.id} className={'card'+(active===p.id?' active':'')}><div className="card-body"><button className="card-title" onClick={()=>D(p.id)}>{p.name[lang]}</button><p>{p.region_name||p.place_id} · {p.coordinate_scope==='city_centre'?tr(lang,'도시 중심점 · 관광 명소 아님','City centre · not a specific attraction','မြို့လယ် · သီးခြားလည်ပတ်နေရာမဟုတ်'):categoryName(lang,p.category)+' · '+(p.source_kind==='openstreetmap'?tr(lang,'지도 등록 · 현장 미확인','Mapped · not field verified','မြေပုံနေရာ · မစစ်ရသေး'):tr(lang,'위치 검토됨','Location reviewed','တည်နေရာ စစ်ပြီး'))}</p><details><summary>{tr(lang,'참고자료','References','ကိုးကားချက်များ')}</summary>{p.checked_at&&<p>{tr(lang,'자료 수집일','Data collected','ဒေတာစုဆောင်းရက်')}: {p.checked_at.slice(0,10)}</p>}<p><a href={p.evidence?.url||p.source} target="_blank" rel="noreferrer">{tr(lang,'원본 자료','Original source','မူရင်း')} ↗</a> · <a href={p.source} target="_blank" rel="noreferrer">{tr(lang,'위치 출처','Location source','တည်နေရာရင်းမြစ်')} ↗</a></p></details></div>{addButton(p)}</li>)}</ol>
    <p className="fine"><a href="https://www.geonames.org/" target="_blank" rel="noreferrer">GeoNames · CC BY 4.0</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a> · <a href={api+'/catalog'} target="_blank" rel="noreferrer">{tr(lang,'명소 원본','Landmark data','မူရင်းဒေတာ')}</a></p>
   </>}
  </div>
  <div className="stage-map"><Map places={mapPlaces} selectedId={active} onSelect={D} lang={lang} labels={mode==='ask'?labels:undefined}/><p className="map-chip">{mode==='ask'&&found.length?tr(lang,'찾은 장소','Found places','တွေ့ရှိသောနေရာ')+' '+found.length:mapPlaces.length+' '+tr(lang,'곳','places','နေရာ')} · {tr(lang,'영업·가격·안전 별도 확인','Opening, prices, safety unverified','ဖွင့်ချိန်၊ ဈေး၊ လုံခြုံရေး မစစ်ရသေး')}</p></div>
  <aside className="panel trip-mini" aria-label={tr(lang,'내 여행','My trip','ကျွန်ုပ်ခရီးစဉ်')}>
   <div className="results-head"><h2>{tr(lang,'내 여행','My trip','ကျွန်ုပ်ခရီးစဉ်')}</h2><span className="fine">{cart.length}/24</span></div>
   {!cart.length?<p className="empty-state">{tr(lang,'추천에서 담기를 누르면 여기에 모여요.','Places you add appear here.','ထည့်ထားသောနေရာများ ဤနေရာတွင် ပေါ်မည်။')}</p>:<ol className="mini-list">{cart.map((p,i)=><li key={p.id}><span className="num small">{i+1}</span><span className="grow">{p.name[lang]}{p.coordinate_scope==='city_centre'&&<small>{tr(lang,'도시 중심점','City centre','မြို့လယ်')}</small>}{p.auto_located&&<small>{tr(lang,'자동 위치·미검증','Auto-located · unverified','မစစ်ရသေး')}</small>}</span><button className="icon-btn" aria-label={tr(lang,p.name[lang]+' 빼기','Remove '+p.name[lang],p.name[lang]+' ဖယ်ရန်')} onClick={()=>onRemove(p.id)}>×</button></li>)}</ol>}
   <button className="next-btn" disabled={!cart.length} onClick={onNext}>{tr(lang,'지도·일정으로','Go to map & plan','မြေပုံ·အစီအစဉ်သို့')} →</button>
   <p className="fine center">{tr(lang,'이 기기에만 보관 · 다른 기기와 동기화되지 않아요','Kept on this device only · no cross-device sync','ဤစက်တွင်သာ သိမ်းသည်')}</p>
  </aside>
 </section>
}

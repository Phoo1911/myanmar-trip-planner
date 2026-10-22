"use client";
import {useMemo,useState} from 'react';
import dynamic from 'next/dynamic';
import Trip from './Trip';
import type {Route,TripSpot} from './trip-storage';
const Map=dynamic(()=>import('./Map'),{ssr:false});
type Lang='ko'|'en'|'my';
const tr=(l:Lang,ko:string,en:string,my:string)=>({ko,en,my}[l]);

// Step 2: the map shows the arranged visit order beside the editable trip.
export default function PlanStep({lang,cart,onRemove,onBrowse,onNext,onClear}:{lang:Lang;cart:TripSpot[];onRemove:(id:string)=>void;onBrowse:()=>void;onNext:()=>void;onClear:()=>void}){
 const[route,R]=useState<Route|null>(null),[selected,D]=useState('');
 const stops=useMemo(()=>route?route.days.flatMap(d=>d.stops):cart,[route,cart]);
 const labels=useMemo(()=>route?Object.fromEntries(route.days.flatMap(d=>d.stops.map((p,i)=>[p.id,'D'+d.day+'·'+(i+1)+' '+p.name[lang]]))):Object.fromEntries(cart.map((p,i)=>[p.id,(i+1)+' '+p.name[lang]])),[route,cart,lang]);
 return <section className="stage plan-stage">
  <div className="stage-map"><Map places={stops} selectedId={stops.some(p=>p.id===selected)?selected:undefined} onSelect={D} lang={lang} labels={labels}/><p className="map-chip">{route?tr(lang,'직선거리 기준 방문 순서','Straight-line visit order','တိုက်ရိုက်အကွာအဝေးအလိုက် အစီအစဉ်'):tr(lang,'담은 장소','Saved places','ထည့်ထားသောနေရာ')} · {tr(lang,'실제 도로·이동시간 미확인','Road routes and times unverified','လမ်းကြောင်းနှင့် ကြာချိန် မစစ်ရသေး')}</p></div>
  <aside className="panel">
   <Trip lang={lang} cart={cart} onRemove={onRemove} onBrowse={onBrowse} onRoute={R}/>
   <button className="next-btn" disabled={!cart.length} onClick={onNext}>{tr(lang,'준비하기','Prepare','ပြင်ဆင်ရန်')} →</button>
   <button className="secondary" disabled={!cart.length} onClick={onClear}>{tr(lang,'이 기기 일정 전체 삭제','Delete device trip','ဤစက်ရှိခရီးစဉ်ဖျက်ရန်')}</button>
  </aside>
 </section>
}

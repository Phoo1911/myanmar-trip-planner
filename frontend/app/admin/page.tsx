"use client";
import {useState} from 'react';
import {SocialAdmin} from '../Social';
import {InventoryAdmin} from '../Commerce';
import {ConciergeAdmin} from '../Concierge';
type Lang='ko'|'en'|'my';
type Row={id:string;status:string;version:number;request:{email:string;product_id:string;start_date:string;guests:number}};
const api=process.env.NEXT_PUBLIC_API_URL||'/api';
const tr=(l:Lang,ko:string,en:string,my:string)=>({ko,en,my}[l]);
async function call(path:string,options:RequestInit={}){const r=await fetch(api+path,{...options,headers:{'Content-Type':'application/json',...options.headers}});if(!r.ok)throw new Error(String(r.status));return r.json()}

// Operator tools, kept off the public travel flow. Every action still requires the admin bearer token.
export default function Admin(){
 const[lang,L]=useState<Lang>('ko'),[admin,A]=useState(''),[rows,U]=useState<Row[]>([]),[busy,B]=useState(false),[error,E]=useState('');
 async function act(fn:()=>Promise<void>){B(true);E('');try{await fn()}catch{E(tr(lang,'요청에 실패했습니다. 토큰과 연결을 확인하세요.','Request failed. Check the token and connection.','တောင်းဆိုမှု မအောင်မြင်ပါ။'))}finally{B(false)}}
 const status=(s:string)=>({requested:tr(lang,'확인 대기','Pending review','စစ်ဆေးရန် စောင့်ဆိုင်းနေ'),approved:tr(lang,'상담 요청 승인 (예약 미확정)','Request approved (not a reservation)','လက်ခံပြီး (ဘွတ်ကင် မအတည်ပြုရသေး)'),rejected:tr(lang,'요청 거절','Rejected','ငြင်းပယ်ပြီး')} as Record<string,string>)[s]||s;
 return <main className="onestop">
  <header className="topbar"><a href="/" className="brand">◈ Myanmar Journey · {tr(lang,'관리자','Admin','စီမံခန့်ခွဲသူ')}</a><select aria-label="Language" value={lang} onChange={e=>L(e.target.value as Lang)}><option value="ko">한국어</option><option value="en">English</option><option value="my">မြန်မာ</option></select></header>
  <section className="admin-stage">
   <p className="mb-5">{tr(lang,'관리자 승인은 요청 접수 승인입니다. 공급사 예약 확정이나 결제가 아닙니다.','Approval accepts the inquiry only. It does not confirm a supplier booking or payment.','လက်ခံခြင်းသည် မေးမြန်းမှုကိုသာ လက်ခံခြင်းဖြစ်သည်။')}</p>
   <form className="flex flex-wrap items-end gap-4" onSubmit={e=>{e.preventDefault();act(async()=>U(await call('/admin/bookings',{headers:{Authorization:'Bearer '+admin}})))}}><label>{tr(lang,'관리자 접근 토큰','Admin access token','စီမံခန့်ခွဲသူ တိုကင်')}<input type="password" required value={admin} onChange={e=>A(e.target.value)} autoComplete="off"/></label><button disabled={busy}>{tr(lang,'문의 목록 불러오기','Load inquiries','စာရင်းဖတ်ရန်')}</button></form>
   {error&&<p role="alert" className="alert mt-4">{error}</p>}
   <div className="mt-6 grid gap-4">{rows.map(row=><article key={row.id} className="rounded-xl border border-green-900/20 bg-white p-5"><p>{row.request.email} · {row.request.product_id} · {row.request.start_date} · {row.request.guests}</p><p className="my-3">{status(row.status)}</p>{row.status==='requested'&&<div className="flex gap-3">{(['approved','rejected'] as const).map(s=><button key={s} disabled={busy} onClick={()=>act(async()=>{await call('/admin/bookings/'+row.id,{method:'PATCH',headers:{Authorization:'Bearer '+admin},body:JSON.stringify({status:s,version:row.version})});U(await call('/admin/bookings',{headers:{Authorization:'Bearer '+admin}}))})}>{s==='approved'?tr(lang,'요청 승인','Approve request','လက်ခံရန်'):tr(lang,'거절','Reject','ငြင်းပယ်ရန်')}</button>)}</div>}</article>)}</div>
   <ConciergeAdmin lang={lang} token={admin}/><InventoryAdmin lang={lang} token={admin}/><SocialAdmin lang={lang} token={admin}/>
  </section>
 </main>
}

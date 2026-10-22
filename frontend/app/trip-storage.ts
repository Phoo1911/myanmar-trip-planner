// Only public place data belongs here. Never persist receipt or admin credentials.
export type TripSpot={id:string;name:Record<'ko'|'en'|'my',string>;lat:number;lng:number;references?:string[];coordinate_scope?:'city_centre'};
export type Route={days:{day:number;stops:TripSpot[]}[]};
export const CART_KEY='journey:places:v1';
export const DRAFT_KEY='journey:draft:v1';
export const signature=(cart:TripSpot[],days:number)=>JSON.stringify([cart.map(p=>p.id),days]);
export function parsePlaces(raw:string|null):TripSpot[]{
 if(!raw||raw.length>40000)return [];
 try{const value=JSON.parse(raw);if(!Array.isArray(value)||value.length>24)return [];
 const seen=new Set<string>();return value.map(p=>{
 if(!p||typeof p.id!=='string'||!p.id.length||p.id.length>128||seen.has(p.id)||!Number.isFinite(p.lat)||p.lat<9||p.lat>29||!Number.isFinite(p.lng)||p.lng<92||p.lng>102||!['ko','en','my'].every(l=>typeof p.name?.[l]==='string'&&p.name[l].length>0&&p.name[l].length<=200))throw Error('Invalid place');
 seen.add(p.id);return {id:p.id,name:{ko:p.name.ko,en:p.name.en,my:p.name.my},lat:p.lat,lng:p.lng,...(p.coordinate_scope==='city_centre'?{coordinate_scope:'city_centre' as const}:{}),...(Array.isArray(p.references)?{references:p.references.filter((u:unknown)=>{try{if(typeof u!=='string'||u.length>1000)return false;const url=new URL(u);return url.protocol==='https:'&&!url.username&&!url.password&&(!url.port||url.port==='443')&&![...url.searchParams.keys()].some(k=>['access_token','token','api_key','password','key'].includes(k.toLowerCase()))&&['facebook.com','tiktok.com','youtube.com','youtu.be','instagram.com'].some(d=>url.hostname===d||url.hostname.endsWith('.'+d))}catch{return false}}).slice(0,8)}:{})};});
 }catch{return []}
}
export function parseDraft(raw:string|null,cart:TripSpot[]):{days:number;route:Route;savedAt:string}|null{
 if(!raw||raw.length>50000)return null;
 try{const d=JSON.parse(raw);if(d.version!==1||!Number.isInteger(d.days)||d.days<1||d.days>14||d.signature!==signature(cart,d.days)||!Number.isFinite(Date.parse(d.savedAt))||!Array.isArray(d.route?.days)||d.route.days.length!==d.days)return null;
 const ids:string[]=[];const days=d.route.days.map((day:{day:number;stops:TripSpot[]},i:number)=>{
 if(day.day!==i+1||!Array.isArray(day.stops)||day.stops.length>4)throw Error('Invalid day');
 const stops=day.stops.map(p=>{const spot=cart.find(c=>c.id===p.id);if(!spot||ids.includes(p.id))throw Error('Invalid stop');ids.push(p.id);return spot});return {day:i+1,stops};});
 if(!cart.length||ids.length!==cart.length)return null;
 return {days:d.days,route:{days},savedAt:d.savedAt};
 }catch{return null}
}

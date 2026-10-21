import {NextRequest,NextResponse} from 'next/server';
export const dynamic='force-dynamic';
async function proxy(req:NextRequest,{params}:{params:Promise<{path:string[]}>}){
 const {path}=await params;
 if(!['catalog','health','places','products','safety','itineraries','bookings','admin','hotspots','social','offers','reservations','routes'].includes(path[0]))return NextResponse.json({detail:'Not found'},{status:404});
 const base=process.env.API_HOSTPORT?'http://'+process.env.API_HOSTPORT:process.env.API_INTERNAL_ORIGIN||'http://127.0.0.1:8000';
 const headers=new Headers();
 for(const name of ['content-type','authorization','idempotency-key']){const v=req.headers.get(name);if(v)headers.set(name,v)}
 headers.set('X-Internal-Token',process.env.INTERNAL_PROXY_TOKEN||'');
 headers.set('X-Client-Address',(req.headers.get('x-forwarded-for')||'local').split(',').at(-1)!.trim());
 try{
 const body=['GET','HEAD'].includes(req.method)?undefined:await req.text();
 if(body&&new TextEncoder().encode(body).length>16384)return NextResponse.json({detail:'Too large'},{status:413});
 const response=await fetch(base+'/'+path.map(encodeURIComponent).join('/')+req.nextUrl.search,{method:req.method,headers,body,cache:'no-store',signal:AbortSignal.timeout(40000),redirect:'error'});
 return new NextResponse(await response.text(),{status:response.status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
 }catch{return NextResponse.json({detail:'Service unavailable'},{status:502})}
}
export {proxy as GET,proxy as POST,proxy as PATCH};

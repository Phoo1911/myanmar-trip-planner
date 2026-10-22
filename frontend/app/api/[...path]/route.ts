import {NextRequest,NextResponse} from 'next/server';
export const dynamic='force-dynamic';
async function proxy(req:NextRequest,{params}:{params:Promise<{path:string[]}>}){
 const {path}=await params;
 if(!['discovery','concierge','catalog','health','places','products','safety','itineraries','bookings','admin','hotspots','social','offers','reservations','routes'].includes(path[0]))return NextResponse.json({detail:'Not found'},{status:404,headers:{'Cache-Control':'no-store'}});
 const base=process.env.API_HOSTPORT?'http://'+process.env.API_HOSTPORT:process.env.API_INTERNAL_ORIGIN||'http://127.0.0.1:8000';
 const headers=new Headers();
 for(const name of ['content-type','authorization','idempotency-key']){const v=req.headers.get(name);if(v)headers.set(name,v)}
 headers.set('X-Internal-Token',process.env.INTERNAL_PROXY_TOKEN||'');
 headers.set('X-Client-Address',(req.headers.get('x-forwarded-for')||'local').split(',').at(-1)!.trim());
 try{
 let body:string|undefined;
 if(!['GET','HEAD'].includes(req.method)&&req.body){
  const reader=req.body.getReader();const chunks:Uint8Array[]=[];let size=0;
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>16384){await reader.cancel();return NextResponse.json({detail:'Too large'},{status:413,headers:{'Cache-Control':'no-store'}})}chunks.push(value)}
  const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength}body=new TextDecoder().decode(bytes);
 }
 const response=await fetch(base+'/'+path.map(encodeURIComponent).join('/')+req.nextUrl.search,{method:req.method,headers,body,cache:'no-store',signal:AbortSignal.timeout(40000),redirect:'error'});
 const retry=response.headers.get('Retry-After');
 return new NextResponse(await response.text(),{status:response.status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...(retry?{'Retry-After':retry}:{})}});
 }catch{return NextResponse.json({detail:'Service unavailable'},{status:502,headers:{'Cache-Control':'no-store'}})}
}
export {proxy as GET,proxy as POST,proxy as PATCH};

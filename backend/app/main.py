import os, secrets, hashlib, json
from datetime import date, datetime, timezone
from contextlib import asynccontextmanager
from typing import Literal
import httpx
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import create_engine, String, Text, Integer, select, update, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

database_url=os.getenv("DATABASE_URL","sqlite:///./travel.db")
if database_url.startswith('postgres://'): database_url=database_url.replace('postgres://','postgresql+psycopg://',1)
elif database_url.startswith('postgresql://'): database_url=database_url.replace('postgresql://','postgresql+psycopg://',1)
engine=create_engine(database_url, **({"connect_args":{"check_same_thread":False}} if os.getenv("DATABASE_URL","sqlite:").startswith("sqlite") else {}))
class Base(DeclarativeBase): pass
class Booking(Base):
    __tablename__="bookings"
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    key:Mapped[str]=mapped_column(String(64),unique=True)
    fingerprint:Mapped[str]=mapped_column(String(64))
    token_hash:Mapped[str]=mapped_column(String(64))
    payload:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(24),default="requested")
    version:Mapped[int]=mapped_column(Integer,default=1)
    created_at:Mapped[str]=mapped_column(String(40))
class RateBucket(Base):
    __tablename__='rate_buckets'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    count:Mapped[int]=mapped_column(Integer)
    expires:Mapped[int]=mapped_column(Integer)
class SocialVideo(Base):
    __tablename__='social_videos'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    payload:Mapped[str]=mapped_column(Text)
class Hotspot(Base):
    __tablename__='hotspots'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    payload:Mapped[str]=mapped_column(Text)
    created_at:Mapped[str]=mapped_column(String(40))
class Audit(Base):
    __tablename__="audit"
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    booking_id:Mapped[str]=mapped_column(String(64))
    action:Mapped[str]=mapped_column(String(24))
    created_at:Mapped[str]=mapped_column(String(40))
@asynccontextmanager
async def lifespan(app):
    if os.getenv('APP_ENV')=='production':
        for name in (('ADMIN_TOKEN','RECEIPT_SECRET','INTERNAL_PROXY_TOKEN') if os.getenv('REQUIRE_PROXY_TOKEN')=='true' else ('ADMIN_TOKEN','RECEIPT_SECRET')):
            value=os.getenv(name,'')
            if len(value)<32 or value.startswith('replace-'): raise RuntimeError(name+' must be a strong secret')
        if not database_url.startswith('postgresql'): raise RuntimeError('Production requires PostgreSQL')
        if any(not origin.startswith('https://') for origin in filter(None,os.getenv('CORS_ORIGINS','').split(','))): raise RuntimeError('Production requires HTTPS CORS origins')
    yield
app=FastAPI(title="Myanmar Journey API",version="1.0.0",lifespan=lifespan)
@app.middleware('http')
async def headers(request,call_next):
    from fastapi.responses import JSONResponse
    if os.getenv('REQUIRE_PROXY_TOKEN')=='true' and not secrets.compare_digest(request.headers.get('X-Internal-Token',''),os.getenv('INTERNAL_PROXY_TOKEN','!unconfigured')):
        return JSONResponse({'detail':'Unauthorized proxy'},status_code=401)
    if request.method in ('POST','PATCH') and os.getenv('RATE_LIMIT_ENABLED','true')=='true':
        import time
        now=int(time.time()); window=now//60
        address=request.headers.get('X-Client-Address','') if os.getenv('REQUIRE_PROXY_TOKEN')=='true' else (request.client.host if request.client else 'unknown')
        bucket=hashlib.sha256((address+':'+str(window)).encode()).hexdigest()
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        insert=sqlite_insert if engine.dialect.name=='sqlite' else pg_insert
        with Session(engine) as session:
            statement=insert(RateBucket).values(id=bucket,count=1,expires=now+120)
            statement=statement.on_conflict_do_update(index_elements=['id'],set_={'count':RateBucket.count+1}).returning(RateBucket.count)
            count=session.scalar(statement)
            session.execute(delete(RateBucket).where(RateBucket.expires<now));session.commit()
        if count>int(os.getenv('RATE_LIMIT_PER_MINUTE','15')):
            return JSONResponse({'detail':'Rate limit exceeded'},status_code=429,headers={'Retry-After':'60'})
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","http://localhost:3000").split(","),allow_methods=["GET","POST","PATCH"],allow_headers=["Content-Type","Authorization","Idempotency-Key"])
def db():
    with Session(engine) as s: yield s
def admin(authorization:str=Header(default="")):
    token=os.getenv("ADMIN_TOKEN","")
    if len(token)<32 or not secrets.compare_digest(authorization,"Bearer "+token): raise HTTPException(401,"Unauthorized")
PLACES=[
 {"id":"yangon","name":{"ko":"양곤","en":"Yangon","my":"ရန်ကုန်"},"lat":16.7983,"lng":96.1496,"region":"Yangon","source":"https://whc.unesco.org/en/tentativelists/6367/"},
 {"id":"bagan","name":{"ko":"바간","en":"Bagan","my":"ပုဂံ"},"lat":21.1717,"lng":94.8585,"region":"Mandalay","source":"https://whc.unesco.org/en/list/1588/"},
 {"id":"inle","name":{"ko":"인레호수","en":"Inle Lake","my":"အင်းလေးကန်"},"lat":20.55,"lng":96.9167,"region":"Shan","source":"https://www.unesco.org/en/mab/inlay-lake"}]
PRODUCTS=[{"id":kind,"kind":kind,"mode":"request_only","price":None,"availability":None,"verified_at":None,"name":{"ko":ko,"en":en,"my":my}} for kind,ko,en,my in [("stay","숙소 상담","Accommodation request","တည်းခိုရန် တောင်းဆိုမှု"),("transport","교통 상담","Transport request","သယ်ယူပို့ဆောင်ရေး တောင်းဆိုမှု"),("tour","투어 상담","Tour request","ခရီးစဉ် တောင်းဆိုမှု")]]
@app.get('/health')
def health(s:Session=Depends(db)):
    s.execute(select(Booking.id).limit(1)); return {"status":"ok"}
@app.get('/places')
def places(q:str=""):
    return [p for p in PLACES if q.casefold() in (" ".join(p['name'].values())+' '+p['region']).casefold()]
@app.get('/products')
def products(): return PRODUCTS
@app.get('/safety')
def safety():
    return {"level":"warning","live":False,"checked_at":"2026-10-21","source":"https://www.gov.uk/foreign-travel-advice/myanmar","message":{"ko":"미얀마 일부 지역 여행 금지·필수 목적 외 여행 자제 권고가 있습니다. 예약 전 공식 지역별 경보를 확인하세요. 이 표시는 실시간 안전 보장이 아닙니다.","en":"Official advice warns against travel to parts of Myanmar. Check regional advice before planning. This snapshot does not establish that any route is safe.","my":"မြန်မာနိုင်ငံ၏ အချို့ဒေသများသို့ ခရီးမသွားရန် သတိပေးထားသည်။ မစီစဉ်မီ တရားဝင် ဒေသအလိုက် သတိပေးချက်ကို စစ်ဆေးပါ။"}}
class PlanInput(BaseModel):
    destination_ids:list[Literal['yangon','bagan','inle']]=Field(min_length=1,max_length=3)
    days:int=Field(ge=1,le=14)
    language:Literal['ko','en','my']='ko'
class Day(BaseModel):
    day:int
    place_id:Literal['yangon','bagan','inle']
class Plan(BaseModel):
    days:list[Day]
@app.post('/itineraries')
def itinerary(body:PlanInput):
    key=os.getenv('OPENAI_API_KEY')
    if not key:
        return {"mode":"template","days":[{"day":i+1,"place_id":body.destination_ids[min(i*len(body.destination_ids)//body.days,len(body.destination_ids)-1)]} for i in range(body.days)],"requires_safety_review":True}
    schema={"type":"object","properties":{"days":{"type":"array","items":{"type":"object","properties":{"day":{"type":"integer"},"place_id":{"type":"string","enum":body.destination_ids}},"required":["day","place_id"],"additionalProperties":False}}},"required":["days"],"additionalProperties":False}
    try:
        response=httpx.post('https://api.openai.com/v1/responses',headers={"Authorization":"Bearer "+key},json={"model":os.getenv('OPENAI_MODEL','gpt-4o-mini'),"input":"Create a draft itinerary using only these place IDs. No prices, availability, transport assumptions or safety claims. Exactly consecutive days starting at 1. Request: "+body.model_dump_json(),"text":{"format":{"type":"json_schema","name":"itinerary","strict":True,"schema":schema}},"max_output_tokens":1200},timeout=30)
        response.raise_for_status()
        raw=''.join(c.get('text','') for o in response.json().get('output',[]) for c in o.get('content',[]) if c.get('type')=='output_text')
        plan=Plan.model_validate_json(raw)
        if len(plan.days)!=body.days or [d.day for d in plan.days]!=list(range(1,body.days+1)) or any(d.place_id not in body.destination_ids for d in plan.days): raise ValueError('Invalid itinerary')
        return {"mode":"ai","days":plan.model_dump()['days'],"requires_safety_review":True}
    except Exception:
        raise HTTPException(502,'AI unavailable or invalid response; please retry')
class Request(BaseModel):
    product_id:Literal['stay','transport','tour']
    place_id:Literal['yangon','bagan','inle']
    start_date:date
    guests:int=Field(ge=1,le=20)
    email:EmailStr
    language:Literal['ko','en','my']='ko'
    safety_ack:Literal[True]
@app.post('/bookings',status_code=201)
def create(body:Request,idempotency_key:str=Header(min_length=16,max_length=128),s:Session=Depends(db)):
    if body.start_date<date.today(): raise HTTPException(422,'Date is in the past')
    payload=body.model_dump_json(); fp=hashlib.sha256(payload.encode()).hexdigest(); key=hashlib.sha256(idempotency_key.encode()).hexdigest()
    # Derive the receipt secret so safe retries return the same receipt without storing it.
    secret=os.getenv('RECEIPT_SECRET','')
    if len(secret)<32: raise HTTPException(503,'Receipt secret not configured')
    import hmac
    token=hmac.new(secret.encode(),idempotency_key.encode(),hashlib.sha256).hexdigest()
    old=s.scalar(select(Booking).where(Booking.key==key))
    if old:
        if old.fingerprint!=fp: raise HTTPException(409,'Idempotency key reused with different request')
        return {"id":old.id,"token":token,"status":old.status}
    b=Booking(id=secrets.token_urlsafe(18),key=key,fingerprint=fp,token_hash=hashlib.sha256(token.encode()).hexdigest(),payload=payload,status='requested',created_at=datetime.now(timezone.utc).isoformat())
    s.add(b)
    from sqlalchemy.exc import IntegrityError
    try: s.commit()
    except IntegrityError:
        s.rollback(); raise HTTPException(409,'Concurrent retry; repeat the same request')
    return {"id":b.id,"token":token,"status":b.status}
@app.get('/bookings/{bid}')
def receipt(bid:str,authorization:str=Header(default=''),s:Session=Depends(db)):
    b=s.get(Booking,bid)
    if not b or not secrets.compare_digest(b.token_hash,hashlib.sha256(authorization.removeprefix('Bearer ').encode()).hexdigest()): raise HTTPException(404,'Not found')
    return {"id":b.id,"status":b.status,"version":b.version,"reservation_confirmed":False}
@app.get('/admin/bookings',dependencies=[Depends(admin)])
def queue(s:Session=Depends(db)):
    return [{"id":b.id,"status":b.status,"version":b.version,"request":json.loads(b.payload)} for b in s.scalars(select(Booking).order_by(Booking.created_at.desc()).limit(100))]
class Decision(BaseModel):
    status:Literal['approved','rejected']
    version:int=Field(ge=1)
@app.patch('/admin/bookings/{bid}',dependencies=[Depends(admin)])
def decide(bid:str,body:Decision,s:Session=Depends(db)):
    result=s.execute(update(Booking).where(Booking.id==bid,Booking.version==body.version,Booking.status=='requested').values(status=body.status,version=body.version+1))
    if result.rowcount!=1: raise HTTPException(409,'Request already processed or stale version')
    s.add(Audit(id=secrets.token_hex(16),booking_id=bid,action=body.status,created_at=datetime.now(timezone.utc).isoformat())); s.commit()
    return {"status":body.status,"reservation_confirmed":False}

# Official API metadata only. No scraping, guessed engagement, or inferred coordinates.
@app.get('/social/status')
def social_status():
    return {'youtube':'configured' if os.getenv('YOUTUBE_API_KEY') else 'not_configured','instagram':'not_integrated','tiktok':'not_integrated','ranking':'views_per_day_since_publication','scope':'Search sample, not nationwide popularity or footfall'}
class SyncInput(BaseModel):
    place_id:Literal['yangon','bagan','inle']
@app.post('/admin/social/sync',dependencies=[Depends(admin)])
def sync_social(body:SyncInput,s:Session=Depends(db)):
    from datetime import timedelta
    import re
    key=os.getenv('YOUTUBE_API_KEY')
    if not key: raise HTTPException(503,'YOUTUBE_API_KEY not configured')
    place=next(p for p in PLACES if p['id']==body.place_id)
    now=datetime.now(timezone.utc)
    try:
        search=httpx.get('https://www.googleapis.com/youtube/v3/search',params={'key':key,'part':'snippet','type':'video','q':place['name']['en']+' Myanmar travel','order':'relevance','publishedAfter':(now-timedelta(days=90)).isoformat(),'maxResults':10},timeout=20)
        search.raise_for_status()
        ids=[v['id']['videoId'] for v in search.json().get('items',[]) if re.fullmatch(r'[A-Za-z0-9_-]{11}',v.get('id',{}).get('videoId',''))]
        if not ids:return []
        result=httpx.get('https://www.googleapis.com/youtube/v3/videos',params={'key':key,'part':'snippet,statistics','id':','.join(ids)},timeout=20)
        result.raise_for_status()
        videos=[]
        for item in result.json().get('items',[]):
            if item['id'] not in ids:continue
            snippet=item['snippet'];published=datetime.fromisoformat(snippet['publishedAt'].replace('Z','+00:00'))
            stats=item.get('statistics',{});views=int(stats.get('viewCount',0))
            data={'id':item['id'],'title':snippet['title'],'url':'https://www.youtube.com/watch?v='+item['id'],'place_id':body.place_id,'views':views,'likes':int(stats['likeCount']) if 'likeCount' in stats else None,'published_at':snippet['publishedAt'],'collected_at':now.isoformat(),'score':round(views/max(1,(now-published).total_seconds()/86400),2)}
            old=s.get(SocialVideo,item['id'])
            if old:old.payload=json.dumps(data)
            else:s.add(SocialVideo(id=item['id'],payload=json.dumps(data)))
            videos.append(data)
        s.commit();return sorted(videos,key=lambda v:v.get('score') or 0,reverse=True)
    except (httpx.HTTPError,ValueError,KeyError):
        s.rollback();raise HTTPException(502,'YouTube unavailable or quota exceeded')
@app.get('/admin/social',dependencies=[Depends(admin)])
def social_queue(s:Session=Depends(db)):
    return sorted([json.loads(v.payload) for v in s.scalars(select(SocialVideo))],key=lambda v:v.get('score') or 0,reverse=True)
class Names(BaseModel):
    ko:str=Field(min_length=1,max_length=100)
    en:str=Field(min_length=1,max_length=100)
    my:str=Field(min_length=1,max_length=100)
class HotspotInput(BaseModel):
    video_id:str=Field(pattern=r'^[A-Za-z0-9_-]{11,64}$')
    name:Names
    place_id:Literal['yangon','bagan','inle']
    category:Literal['cafe','restaurant','heritage','viewpoint']
    lat:float=Field(ge=9,le=29)
    lng:float=Field(ge=92,le=102)
    location_source:str=Field(pattern=r'^https://[^\s]+$',max_length=1000)
    location_verified:Literal[True]
@app.post('/admin/hotspots',dependencies=[Depends(admin)],status_code=201)
def publish_hotspot(body:HotspotInput,s:Session=Depends(db)):
    from datetime import timedelta
    from sqlalchemy.exc import IntegrityError
    video=s.get(SocialVideo,body.video_id)
    if not video:raise HTTPException(422,'Sync the source video first')
    evidence=json.loads(video.payload)
    if evidence['place_id']!=body.place_id:raise HTTPException(422,'Source region mismatch')
    if datetime.fromisoformat(evidence['collected_at'])<datetime.now(timezone.utc)-timedelta(days=30):raise HTTPException(422,'Refresh source older than 30 days')
    data=body.model_dump();data['id']=body.video_id;data['source']=body.location_source
    s.add(Hotspot(id=body.video_id,payload=json.dumps(data),created_at=datetime.now(timezone.utc).isoformat()))
    s.add(Audit(id=secrets.token_hex(16),booking_id=body.video_id,action='hotspot_published',created_at=datetime.now(timezone.utc).isoformat()))
    try:s.commit()
    except IntegrityError:s.rollback();raise HTTPException(409,'Already published')
    return {'id':body.video_id}
@app.get('/hotspots')
def hotspots(q:str='',category:str='',s:Session=Depends(db)):
    from datetime import timedelta
    output=[]
    for h in s.scalars(select(Hotspot)):
        data=json.loads(h.payload);video=s.get(SocialVideo,data['video_id'])
        if not video:continue
        evidence=json.loads(video.payload)
        if datetime.fromisoformat(evidence['collected_at'])<datetime.now(timezone.utc)-timedelta(days=30):continue
        if q.casefold() not in ' '.join(data['name'].values()).casefold() or (category and data['category']!=category):continue
        data['evidence']=evidence;data['price']=None;data['availability']=None;data['mode']='request_only';output.append(data)
    return sorted(output,key=lambda v:v['evidence'].get('score') or 0,reverse=True)

from .commerce import router as commerce_router
app.include_router(commerce_router)

class SocialLink(BaseModel):
    url:str=Field(max_length=1000)
    title:str=Field(min_length=2,max_length=200)
    place_id:Literal['yangon','bagan','inle']
@app.post('/social/links',status_code=201)
def import_link(body:SocialLink,s:Session=Depends(db)):
    from urllib.parse import urlparse,urlunparse
    try:
        parsed=urlparse(body.url)
        port=parsed.port
    except ValueError:raise HTTPException(422,'Malformed URL')
    if parsed.scheme!='https' or parsed.username or parsed.password or port not in (None,443):raise HTTPException(422,'Use a public HTTPS post link')
    host=(parsed.hostname or '').lower()
    if host not in ('facebook.com','www.facebook.com','m.facebook.com','fb.watch','tiktok.com','www.tiktok.com','vm.tiktok.com','vt.tiktok.com'):raise HTTPException(422,'Only Facebook and TikTok links supported here')
    if not parsed.path.strip('/'):raise HTTPException(422,'Use a post or video link, not the home page')
    # Preserve Facebook story identifiers, strip fragments. Never fetch arbitrary URLs.
    url=urlunparse(('https',host,parsed.path,'',parsed.query,''))
    identifier=hashlib.sha256(url.encode()).hexdigest()[:32]
    old=s.get(SocialVideo,identifier)
    if old:return {'id':identifier,'status':'pending_review','automatic_analysis':False}
    data={'id':identifier,'title':body.title,'url':url,'place_id':body.place_id,'views':None,'likes':None,'score':None,'published_at':None,'collected_at':datetime.now(timezone.utc).isoformat(),'evidence_kind':'submitted_link','platform':'facebook' if host in ('facebook.com','www.facebook.com','m.facebook.com','fb.watch') else 'tiktok'}
    s.add(SocialVideo(id=identifier,payload=json.dumps(data)))
    from sqlalchemy.exc import IntegrityError
    try:s.commit()
    except IntegrityError:s.rollback()
    return {'id':identifier,'status':'pending_review','automatic_analysis':False}
class RouteInput(BaseModel):
    hotspot_ids:list[str]=Field(min_length=1,max_length=24)
    days:int=Field(ge=1,le=14)
    start_place:Literal['yangon','bagan','inle']='yangon'
@app.post('/routes')
def make_route(body:RouteInput,s:Session=Depends(db)):
    import math
    valid={p['id']:p for p in hotspots(s=s)}
    ids=list(dict.fromkeys(body.hotspot_ids))
    if any(identifier not in valid for identifier in ids):raise HTTPException(422,'Place is unavailable or source expired; refresh places')
    groups={}
    for identifier in ids:
        spot=valid[identifier];groups.setdefault(spot['place_id'],[]).append(spot)
    if body.days<len(groups):raise HTTPException(422,'Allow at least one day per region')
    if len(ids)>body.days*4:raise HTTPException(422,'Maximum four selected places per day')
    def distance(a,b):
        x=math.radians(a['lat']-b['lat']);y=math.radians(a['lng']-b['lng'])
        return math.sin(x/2)**2+math.cos(math.radians(a['lat']))*math.cos(math.radians(b['lat']))*math.sin(y/2)**2
    origin=next(p for p in PLACES if p['id']==body.start_place)
    ordered=[]
    while groups:
        region=min(groups,key=lambda k:distance(origin,next(p for p in PLACES if p['id']==k)))
        pending=groups.pop(region)
        while pending:
            stop=min(pending,key=lambda p:distance(origin,p));pending.remove(stop);ordered.append(stop);origin=stop
    output=[{'day':i+1,'stops':[]} for i in range(body.days)]
    # Never mix regions within one day; reserve enough days for subsequent regions.
    region_order=list(dict.fromkeys(p['place_id'] for p in ordered));day_index=0
    required=sum(math.ceil(sum(p['place_id']==region for p in ordered)/4) for region in region_order)
    if required>body.days:raise HTTPException(422,'More days required to keep regions separate')
    for region in region_order:
        region_spots=[p for p in ordered if p['place_id']==region]
        for i,spot in enumerate(region_spots):
            output[day_index+i//4]['stops'].append(spot)
        day_index+=math.ceil(len(region_spots)/4)
    return {'mode':'geographic_draft','days':output,'road_routing':False,'travel_times_verified':False,'requires_safety_review':True}

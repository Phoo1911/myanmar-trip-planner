"""Geoapify geocoding for automatically discovered venues and road-time estimates (free plan, server-side key)."""
import hashlib, logging, math, os, re, threading, unicodedata
from datetime import datetime, timezone
import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .main import app, db, RateBucket
from .discovery import router

BASE='https://api.geoapify.com'
MYANMAR=(9.5,28.6,92.1,101.2)
_cache={}
_lock=threading.Lock()

def daily_limit():
    try:return min(2000,max(0,int(os.getenv('GEOAPIFY_DAILY_LIMIT','300'))))
    except ValueError:return 0

def spend(s,n=1):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    now=datetime.now(timezone.utc)
    identifier=hashlib.sha256(('geoapify-'+now.strftime('%Y-%m-%d')).encode()).hexdigest()
    insert=sqlite_insert if s.bind.dialect.name=='sqlite' else pg_insert
    stmt=insert(RateBucket).values(id=identifier,count=n,expires=int(now.timestamp())+172800)
    count=s.scalar(stmt.on_conflict_do_update(index_elements=['id'],set_={'count':RateBucket.count+n}).returning(RateBucket.count));s.commit()
    if count>daily_limit():raise HTTPException(429,'Map lookup daily preview budget reached')

def call(path,params,key):
    try:response=httpx.get(BASE+path,params={**params,'apiKey':key},timeout=12,follow_redirects=False)
    except httpx.HTTPError as error:
        logging.getLogger(__name__).warning('Geoapify failure path=%s reason=%s',path,type(error).__name__)
        raise HTTPException(502,'Map provider unavailable')
    if response.status_code==429:raise HTTPException(429,'Map provider free quota reached')
    if response.is_error:
        # Never log the URL: it carries the key.
        logging.getLogger(__name__).warning('Geoapify failure path=%s status=%s',path,response.status_code)
        raise HTTPException(502,'Map provider rejected request (HTTP '+str(response.status_code)+')')
    return response.json()

def normalize(text):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text).casefold()).strip()

def in_myanmar(lat,lng):
    return isinstance(lat,(int,float)) and isinstance(lng,(int,float)) and MYANMAR[0]<=lat<=MYANMAR[1] and MYANMAR[2]<=lng<=MYANMAR[3]

def category(categories):
    joined=' '.join(categories or [])
    for key,value in (('catering.cafe','cafe'),('catering','restaurant'),('religion','heritage'),('heritage','heritage'),('tourism.sights','heritage'),('commercial.marketplace','market'),('tourism','viewpoint')):
        if key in joined:return value
    return 'other'

def geocode(name,s):
    """Return an unverified place for a confidently matched named venue in Myanmar, or None."""
    key=os.getenv('GEOAPIFY_API_KEY','')
    if not key:raise HTTPException(503,'GEOAPIFY_API_KEY is not configured')
    wanted=normalize(name)
    if len(wanted)<3:return None
    with _lock:
        if wanted in _cache:return _cache[wanted]
    spend(s)
    data=call('/v1/geocode/search',{'text':name+', Myanmar','filter':'countrycode:mm','format':'json','limit':3,'lang':'en'},key)
    found=None
    for r in data.get('results',[]):
        lat,lng=r.get('lat'),r.get('lon');label=r.get('name') or ''
        confidence=(r.get('rank') or {}).get('confidence',0)
        # Only a named point of interest whose name actually matches; never a street, city or region centroid.
        if r.get('result_type') not in ('amenity','building') or confidence<0.8 or not in_myanmar(lat,lng):continue
        got=normalize(label)
        if len(got)<3 or (wanted not in got and got not in wanted):continue
        raw=(r.get('datasource') or {}).get('raw') or {}
        osm=raw.get('osm_type'),raw.get('osm_id')
        source='https://www.openstreetmap.org/'+{'n':'node','w':'way','r':'relation'}.get(str(osm[0])[:1],'node')+'/'+str(osm[1]) if osm[1] else 'https://www.openstreetmap.org/#map=18/'+str(lat)+'/'+str(lng)
        display=label[:120]
        found={'id':'geo:'+hashlib.sha256(str(r.get('place_id') or (lat,lng)).encode()).hexdigest()[:24],'name':{'ko':display,'en':display,'my':display},'lat':round(lat,6),'lng':round(lng,6),'category':category(r.get('categories')),'source':source,'source_kind':'geoapify_auto','location_verified':False,'auto_located':True,'checked_at':datetime.now(timezone.utc).isoformat(),'price':None,'availability':None,'mode':'request_only','attribution':'© OpenStreetMap contributors, Geoapify'}
        break
    with _lock:
        if len(_cache)>=256:_cache.pop(next(iter(_cache)))
        _cache[wanted]=found
    return found

@router.get('/geo-status')
def geo_status():
    return {'configured':bool(os.getenv('GEOAPIFY_API_KEY')),'provider':'geoapify','daily_limit':daily_limit(),'road_times_verified':False}

class Point(BaseModel):
    id:str=Field(min_length=1,max_length=128)
    lat:float=Field(ge=9,le=29)
    lng:float=Field(ge=92,le=102)
class RoadDay(BaseModel):
    day:int=Field(ge=1,le=14)
    stops:list[Point]=Field(max_length=4)
class RoadInput(BaseModel):
    days:list[RoadDay]=Field(min_length=1,max_length=14)

@app.post('/routes/road')
def road(body:RoadInput,s:Session=Depends(db)):
    key=os.getenv('GEOAPIFY_API_KEY','')
    if not key:raise HTTPException(503,'GEOAPIFY_API_KEY is not configured')
    output=[]
    for d in body.days:
        if len(d.stops)<2:output.append({'day':d.day,'distance_m':0,'time_s':0,'legs':[]});continue
        spend(s)
        data=call('/v1/routing',{'waypoints':'|'.join(f'{p.lat},{p.lng}' for p in d.stops),'mode':'drive','format':'json'},key)
        try:
            route=data['results'][0];legs=route.get('legs') or []
            distance,time=float(route['distance']),float(route['time'])
            if not (math.isfinite(distance) and math.isfinite(time)) or distance<0 or time<0 or len(legs)!=len(d.stops)-1:raise ValueError()
            output.append({'day':d.day,'distance_m':round(distance),'time_s':round(time),'legs':[{'from':a.id,'to':b.id,'distance_m':round(float(l['distance'])),'time_s':round(float(l['time']))} for a,b,l in zip(d.stops,d.stops[1:],legs)]})
        except (KeyError,IndexError,TypeError,ValueError):
            logging.getLogger(__name__).warning('Geoapify routing response rejected')
            raise HTTPException(502,'Map provider returned an invalid route')
    return {'provider':'geoapify','mode':'drive','days':output,'traffic_included':False,'verified':False,'attribution':'© OpenStreetMap contributors, Geoapify'}

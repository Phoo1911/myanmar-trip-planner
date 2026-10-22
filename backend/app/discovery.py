"""Content-to-map candidates. Search snippets are evidence of mention, never reviews or popularity."""
import calendar, hashlib, html, json, os, re, threading, time, unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from .main import db, RateBucket, catalog_places
router=APIRouter(prefix='/discovery')
_cache={};_lock=threading.Lock()
@lru_cache(maxsize=1)
def national():return json.loads((Path(__file__).parent/'data'/'national-cities.json').read_text())
def city_places():
    output=[]
    for p in national()['places']:
        output.append({**p,'evidence':{'id':p['id'],'title':p['name']['en'],'url':p['source'],'place_id':p['place_id'],'views':None,'likes':None,'score':None,'collected_at':p['checked_at'],'published_at':None}})
    return output
@router.get('/regions')
def regions():return {'regions':national()['regions'],'cities':city_places(),'attribution':national()['attribution'],'license':national()['license'],'collected_at':national()['collected_at']}
@router.get('/status')
def status():return {'search':'configured' if os.getenv('TAVILY_API_KEY') else 'not_configured','provider':'tavily','scope':'indexed_public_content','photos_ocr':False,'full_reviews':False,'popularity_verified':False,'monthly_search_limit':limit()}
def limit():
    try:return min(500,max(0,int(os.getenv('DISCOVERY_MONTHLY_SEARCH_LIMIT','100'))))
    except ValueError:return 0

def public_url(value):
    if not value:return None
    try:
        p=urlparse(value);host=(p.hostname or '').lower()
        if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or not p.path or p.path=='/':raise ValueError()
        if not any(host==d or host.endswith('.'+d) for d in ('facebook.com','tiktok.com','youtube.com','youtu.be','instagram.com')):raise ValueError()
        if host=='shop.tiktok.com' or host.startswith('l.'):raise ValueError()
        query=parse_qs(p.query)
        if any(k.casefold() in ('access_token','token','api_key','password','key') for k in query):raise ValueError()
        return urlunparse(('https',host,p.path,'',urlencode({k:v[0] for k,v in query.items() if k in ('v','id','story_fbid')}),''))
    except ValueError:raise HTTPException(422,'Use a public social post HTTPS URL, without credentials or redirect links')
def normalize(text):
    return re.sub(r'[^\w\u1000-\u109f]+',' ',unicodedata.normalize('NFKC',text).casefold()).strip()
def resolve_text(text,source=None):
    normalized=' '+normalize(text)+' ';matches={};aliases={}
    for p in [*catalog_places(),*city_places()]:
        names=list(p['name'].values())+p.get('aliases',[])
        for name in names:
            n=normalize(name)
            if len(n)<4:continue
            aliases.setdefault(n,{})[p['id']]=p
    ambiguous=[]
    for name,places in aliases.items():
        if (name not in normalized if any('\u1000'<=c<='\u109f' for c in name) else ' '+name+' ' not in normalized):continue
        if len(places)!=1:ambiguous.append(name);continue
        p=next(iter(places.values()));matches[p['id']]={'place':p,'matched_name':name,'source_url':source,'confidence':'name_match_candidate','verified':False}
    return {'matches':list(matches.values())[:24],'ambiguous_names':sorted(set(ambiguous))[:24],'method':'catalog_name_match','unmatched_possible':True,'popularity_verified':False,'photos_ocr':False}
class Resolve(BaseModel):
    text:str=Field(default='',max_length=4000)
    source_url:str=Field(default='',max_length=1000)
    @field_validator('text')
    @classmethod
    def bounded_text(cls,value):
        if len(value.encode('utf-8'))>12000:raise ValueError('Content exceeds 12000 bytes')
        return value
@router.post('/resolve')
def resolve(body:Resolve):
    source=public_url(body.source_url);text=body.text.strip();method='supplied_text'
    if not text and source:
        parsed=urlparse(source)
        if parsed.hostname not in ('www.tiktok.com','tiktok.com') or not re.fullmatch(r'/@[^/]+/video/\d+/?',parsed.path):raise HTTPException(422,'Paste the caption text; automatic reading is only available for canonical TikTok video URLs')
        try:
            response=httpx.get('https://www.tiktok.com/oembed',params={'url':source},timeout=12,follow_redirects=False);response.raise_for_status();data=response.json()
            text=str(data.get('title',''))[:8000];method='tiktok_oembed_title'
            if not text:raise ValueError()
        except (httpx.HTTPError,ValueError,TypeError):raise HTTPException(502,'Could not read public video caption. Paste its text instead')
    if not text:raise HTTPException(422,'Paste content text or a canonical TikTok video URL')
    return {**resolve_text(text,source),'content_read_method':method}
class Search(BaseModel):
    query:str=Field(min_length=2,max_length=100)
    region_id:str=Field(default='',max_length=10)
@router.post('/search')
def search(body:Search,s:Session=Depends(db)):
    key=os.getenv('TAVILY_API_KEY','')
    if not key:raise HTTPException(503,'TAVILY_API_KEY is not configured')
    region=next((r for r in national()['regions'] if r['id']==body.region_id),None)
    if body.region_id and not region:raise HTTPException(422,'Unknown region')
    q='Myanmar travel '+(region['name']+' ' if region else '')+body.query.strip()
    digest=hashlib.sha256(q.encode()).hexdigest();now=time.time()
    with _lock:
        hit=_cache.get(digest)
        if hit and hit[0]>now:return {**hit[1],'cached':True}
    date=datetime.now(timezone.utc);end=datetime(date.year+date.month//12,date.month%12+1,1,tzinfo=timezone.utc)
    identifier=hashlib.sha256(('discovery-search-'+date.strftime('%Y-%m')).encode()).hexdigest()
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert=sqlite_insert if s.bind.dialect.name=='sqlite' else pg_insert
    statement=insert(RateBucket).values(id=identifier,count=1,expires=calendar.timegm(end.utctimetuple()))
    statement=statement.on_conflict_do_update(index_elements=['id'],set_={'count':RateBucket.count+1}).returning(RateBucket.count)
    count=s.scalar(statement);s.commit()
    if count>limit():raise HTTPException(429,'Monthly free-preview search budget reached; content paste remains available',headers={'Retry-After':'86400'})
    try:
        response=httpx.post('https://api.tavily.com/search',headers={'Authorization':'Bearer '+key},json={'query':q,'search_depth':'basic','max_results':8,'include_domains':['facebook.com','tiktok.com','youtube.com','instagram.com'],'include_answer':False,'include_raw_content':False,'include_images':False,'auto_parameters':False,'include_domains_mode':'restrict'},timeout=18,follow_redirects=False)
        response.raise_for_status();data=response.json();items=[];seen=set()
        for raw in data.get('results',[])[:8]:
            try:url=public_url(raw.get('url',''))
            except HTTPException:continue
            if not url or url in seen:continue
            seen.add(url);title=html.unescape(re.sub(r'<[^>]+>','',str(raw.get('title',''))))[:200];excerpt=html.unescape(re.sub(r'<[^>]+>','',str(raw.get('content',''))))[:450]
            items.append({'title':title,'excerpt':excerpt,'url':url,'places':resolve_text(title+' '+excerpt,url)['matches'],'evidence_kind':'search_index_excerpt','collected_at':datetime.now(timezone.utc).isoformat(),'rating':None,'review_count':None,'popularity_verified':False})
        result={'items':items,'cached':False,'scope':'indexed_public_content_not_full_social_feed','photos_ocr':False,'full_reviews':False,'popularity_verified':False}
    except (httpx.HTTPError,ValueError,TypeError,AttributeError):raise HTTPException(502,'Search provider unavailable or free quota exhausted; paste content instead')
    with _lock:
        if len(_cache)>=32:_cache.pop(next(iter(_cache)))
        _cache[digest]=(now+21600,result)
    return result

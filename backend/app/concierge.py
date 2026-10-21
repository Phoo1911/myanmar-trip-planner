"""Private travel desk and sourced local facts; no invented supplier inventory."""
import hashlib,hmac,json,os,secrets
from datetime import date,datetime,timezone,timedelta
from typing import Literal
from fastapi import APIRouter,Depends,Header,HTTPException
from pydantic import BaseModel,Field,EmailStr,AwareDatetime
from sqlalchemy import String,Text,Integer,select,update
from sqlalchemy.orm import Mapped,mapped_column,Session
from sqlalchemy.exc import IntegrityError
from .main import Base,db,admin,Audit
from .catalog import catalog_places
router=APIRouter(prefix='/concierge')
@router.get('/status')
def operations_status():
    return {'operations_enabled':os.getenv('SUPPLIER_OPERATIONS_ENABLED','false')=='true','supplier_delivery':'manual_operator','translation':'operator_reviewed','online_payment':False}
class JourneyRequest(Base):
    __tablename__='journey_requests'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    key:Mapped[str]=mapped_column(String(64),unique=True)
    fingerprint:Mapped[str]=mapped_column(String(64))
    token_hash:Mapped[str]=mapped_column(String(64))
    payload:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(32))
    version:Mapped[int]=mapped_column(Integer,default=1)
class LocalFact(Base):
    __tablename__='local_facts'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    place_id:Mapped[str]=mapped_column(String(64),index=True)
    payload:Mapped[str]=mapped_column(Text)
    version:Mapped[int]=mapped_column(Integer,default=1)
def now():return datetime.now(timezone.utc)
class Preferences(BaseModel):
    region:Literal['yangon','bagan','inle']
    start_date:date
    days:int=Field(ge=1,le=14)
    guests:int=Field(ge=1,le=20)
    interests:list[Literal['heritage','cafe','food','photo']]=Field(min_length=1,max_length=4)
    pace:Literal['relaxed','balanced']='relaxed'
    mobility_needs:str=Field(default='',max_length=500)
    services:list[Literal['stay','transport','guide']]=Field(default_factory=list,max_length=3)
    notes:str=Field(default='',max_length=1000)
    language:Literal['ko','en','my']='ko'
class TripRequest(Preferences):
    email:EmailStr
    safety_ack:Literal[True]
    privacy_ack:Literal[True]
def draft(body:Preferences,s:Session):
    if body.start_date<date.today():raise HTTPException(422,'Start date is in the past')
    all_facts=facts(s)
    places=[]
    for place in catalog_places(place_id=body.region):
        verified=[f for f in all_facts if f['place_id']==place['id'] and not f['expired']]
        blocked=any(f['value']=='no' and (f['field'] in ('opening','foreign_access') or (body.mobility_needs and f['field']=='accessibility')) for f in verified)
        if not blocked:places.append({**place,'local_facts':verified})
    categories={'heritage':'heritage','cafe':'cafe','food':'restaurant','photo':'viewpoint'}
    preferred={categories[i] for i in body.interests}
    ranked=sorted(places,key=lambda p:0 if p['category'] in preferred else 1)
    per_day=2 if body.pace=='relaxed' else 3
    days=[]
    for i in range(body.days):
        stops=ranked[i*per_day:(i+1)*per_day]
        days.append({'day':i+1,'date':(body.start_date+timedelta(days=i)).isoformat(),'stops':stops})
    return {'mode':'catalog_draft','days':days,'unmatched_interests':[i for i in body.interests if not any(p['category']==categories[i] for p in places)],'checks_required':['opening','foreign_access','accessibility','transport_duration','check_in'],'road_routing':False,'safety_verified':False,'services_requested':body.services,'mobility_needs':body.mobility_needs,'brief':{l:{'region':body.region,'guests':body.guests,'days':body.days,'start_date':body.start_date.isoformat(),'notes_original':body.notes,'mobility_original':body.mobility_needs} for l in ('ko','en','my')},'free_text_translated':False}
@router.post('/preview')
def preview(body:Preferences,s:Session=Depends(db)):return draft(body,s)
def audit(s,bid,action):s.add(Audit(id=secrets.token_hex(16),booking_id=bid,action=action,created_at=now().isoformat()))
def view(r):
    data=json.loads(r.payload)
    for quote in data['quotes']:quote.pop('source_reference',None)
    data.pop('confirmation_evidence',None)
    for quote in data['quotes']:quote['expired']=datetime.fromisoformat(quote['valid_until'])<=now()
    return {'id':r.id,'status':r.status,'version':r.version,**data,'automatic_supplier_delivery':False,'payment_status':'unpaid'}
def owned(s,bid,authorization):
    r=s.get(JourneyRequest,bid)
    token=authorization.removeprefix('Bearer ')
    if not r or not secrets.compare_digest(r.token_hash,hashlib.sha256(token.encode()).hexdigest()):raise HTTPException(404,'Not found')
    return r
def change(s,r,data,status,version,action):
    changed=s.execute(update(JourneyRequest).where(JourneyRequest.id==r.id,JourneyRequest.version==version).values(payload=json.dumps(data),status=status,version=version+1))
    if changed.rowcount!=1:raise HTTPException(409,'Request changed; refresh it')
    audit(s,r.id,action);s.commit();s.refresh(r);return view(r)
@router.post('/requests',status_code=201)
def create(body:TripRequest,idempotency_key:str=Header(min_length=16,max_length=128),s:Session=Depends(db)):
    plan=draft(body,s);secret=os.getenv('RECEIPT_SECRET','')
    if len(secret)<32:raise HTTPException(503,'Receipt secret not configured')
    key=hashlib.sha256(('journey:'+idempotency_key).encode()).hexdigest();fp=hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    token=hmac.new(secret.encode(),('journey:'+idempotency_key).encode(),hashlib.sha256).hexdigest()
    old=s.scalar(select(JourneyRequest).where(JourneyRequest.key==key))
    if old:
        if old.fingerprint!=fp:raise HTTPException(409,'Different request for this key')
        return {**view(old),'token':token}
    data={'preferences':body.model_dump(mode='json'),'draft':plan,'quotes':[],'messages':[],'created_at':now().isoformat()}
    r=JourneyRequest(id=secrets.token_hex(16),key=key,fingerprint=fp,token_hash=hashlib.sha256(token.encode()).hexdigest(),payload=json.dumps(data),status='requested',version=1)
    s.add(r);audit(s,r.id,'journey_requested')
    try:s.commit()
    except IntegrityError:s.rollback();raise HTTPException(409,'Concurrent retry; repeat same request')
    return {**view(r),'token':token}
@router.get('/requests/{bid}')
def lookup(bid:str,authorization:str=Header(default=''),s:Session=Depends(db)):return view(owned(s,bid,authorization))
@router.get('/admin/requests',dependencies=[Depends(admin)])
def queue(s:Session=Depends(db)):return [view(r) for r in s.scalars(select(JourneyRequest).limit(100))]
class QuoteInput(BaseModel):
    version:int=Field(ge=1)
    supplier:str=Field(min_length=2,max_length=120)
    service:Literal['stay','transport','guide','package']
    total_minor:int=Field(ge=1,le=1000000000)
    currency:Literal['USD','MMK']
    valid_until:AwareDatetime
    includes:str=Field(min_length=3,max_length=1000)
    exclusions:str=Field(min_length=3,max_length=1000)
    cancellation:str=Field(min_length=3,max_length=1000)
    source_reference:str=Field(min_length=8,max_length=500)
    supplier_verified:Literal[True]
    taxes_included:Literal[True]
@router.post('/admin/requests/{bid}/quotes',dependencies=[Depends(admin)])
def quote(bid:str,body:QuoteInput,s:Session=Depends(db)):
    r=s.get(JourneyRequest,bid)
    if not r:raise HTTPException(404,'Not found')
    if r.status not in ('requested','quoted'):raise HTTPException(409,'Request is not open for quotes')
    data=json.loads(r.payload)
    if data['preferences']['start_date']<=date.today().isoformat():raise HTTPException(409,'Travel date reached')
    if not now()<body.valid_until<=now()+timedelta(days=7):raise HTTPException(422,'Quote validity must be within seven days')
    if len(data['quotes'])>=5:raise HTTPException(409,'Maximum five quotes')
    q=body.model_dump(mode='json');q.pop('version');q.update(id=secrets.token_hex(12),verified_at=now().isoformat(),payment='arrange_with_supplier',unit='party_total',taxes_included=True)
    data['quotes'].append(q)
    return change(s,r,data,'quoted',body.version,'journey_quoted')
class Accept(BaseModel):
    version:int=Field(ge=1)
    quote_id:str=Field(min_length=1,max_length=64)
    terms_ack:Literal[True]
@router.post('/requests/{bid}/accept')
def accept(bid:str,body:Accept,authorization:str=Header(default=''),s:Session=Depends(db)):
    r=owned(s,bid,authorization);data=json.loads(r.payload)
    if data.get('selected_quote')==body.quote_id and r.status in ('quote_accepted','supplier_confirmed'):return view(r)
    if r.status!='quoted':raise HTTPException(409,'No open quote')
    q=next((q for q in data['quotes'] if q['id']==body.quote_id),None)
    if not q or datetime.fromisoformat(q['valid_until'])<=now() or data['preferences']['start_date']<=date.today().isoformat():raise HTTPException(409,'Quote unavailable or expired')
    data['selected_quote']=q['id'];data['accepted_at']=now().isoformat()
    return change(s,r,data,'quote_accepted',body.version,'quote_accepted')
class Confirmation(BaseModel):
    version:int=Field(ge=1)
    booking_reference:str=Field(min_length=3,max_length=120)
    source_reference:str=Field(min_length=8,max_length=500)
    confirmation_authority:Literal[True]
    written_supplier_confirmation:Literal[True]
@router.post('/admin/requests/{bid}/confirm',dependencies=[Depends(admin)])
def confirm(bid:str,body:Confirmation,s:Session=Depends(db)):
    r=s.get(JourneyRequest,bid)
    if not r:raise HTTPException(404,'Not found')
    if r.status!='quote_accepted':raise HTTPException(409,'Customer must accept a quote first')
    data=json.loads(r.payload)
    if data['preferences']['start_date']<=date.today().isoformat():raise HTTPException(409,'Travel date reached')
    data.update(booking_reference=body.booking_reference,confirmed_at=now().isoformat(),confirmation_scope='operator_recorded_supplier_confirmation',confirmation_evidence=body.source_reference)
    return change(s,r,data,'supplier_confirmed',body.version,'supplier_confirmed')
class Message(BaseModel):
    version:int=Field(ge=1)
    text:str=Field(min_length=1,max_length=1000)
    language:Literal['ko','en','my']
    translations:dict[Literal['ko','en','my'],str]=Field(default_factory=dict)
    translation_reviewed:bool=False
def append_message(s,r,body,role):
    if body.translations and (role!='operator' or not body.translation_reviewed or any(not t or len(t)>1000 for t in body.translations.values())):raise HTTPException(422,'Only operator-reviewed translations allowed')
    data=json.loads(r.payload)
    if len(data['messages'])>=50:raise HTTPException(409,'Thread limit reached')
    data['messages'].append({'role':role,'text':body.text,'language':body.language,'translations':body.translations,'translation_reviewed':bool(body.translations) and body.translation_reviewed,'created_at':now().isoformat()})
    return change(s,r,data,r.status,body.version,'journey_message')
@router.post('/requests/{bid}/messages')
def message(bid:str,body:Message,authorization:str=Header(default=''),s:Session=Depends(db)):return append_message(s,owned(s,bid,authorization),body,'traveler')
@router.post('/admin/requests/{bid}/messages',dependencies=[Depends(admin)])
def operator_message(bid:str,body:Message,s:Session=Depends(db)):
    r=s.get(JourneyRequest,bid)
    if not r:raise HTTPException(404,'Not found')
    return append_message(s,r,body,'operator')
class FactInput(BaseModel):
    place_id:str=Field(min_length=1,max_length=64)
    field:Literal['opening','foreign_access','cash_only','accessibility']
    value:Literal['yes','no','unknown']
    source:str=Field(pattern=r'^https://[^\s]+$',max_length=1000)
    checked_at:AwareDatetime
    valid_until:AwareDatetime
    version:int=Field(ge=0,default=0)
    locally_verified:Literal[True]
def facts(s,place_id=''):
    result=[]
    query=select(LocalFact)
    if place_id:query=query.where(LocalFact.place_id==place_id)
    for r in s.scalars(query):
        d=json.loads(r.payload);d['version']=r.version;d['expired']=datetime.fromisoformat(d['valid_until'])<=now()
        if d['expired']:d['value']='unknown'
        result.append(d)
    return result
@router.get('/facts')
def public_facts(place_id:str='',s:Session=Depends(db)):return facts(s,place_id)
@router.post('/admin/facts',dependencies=[Depends(admin)])
def publish_fact(body:FactInput,s:Session=Depends(db)):
    if body.place_id not in {p['id'] for p in catalog_places()}:raise HTTPException(422,'Unknown mapped place')
    if not now()-timedelta(days=7)<=body.checked_at<=now() or not now()<body.valid_until<=body.checked_at+timedelta(days=7):raise HTTPException(422,'Fact must be recently checked and expire within seven days')
    identifier=hashlib.sha256((body.place_id+':'+body.field).encode()).hexdigest();r=s.get(LocalFact,identifier)
    data=body.model_dump(mode='json');data.pop('version')
    if r:
        changed=s.execute(update(LocalFact).where(LocalFact.id==identifier,LocalFact.version==body.version).values(payload=json.dumps(data),version=body.version+1))
        if changed.rowcount!=1:raise HTTPException(409,'Fact changed; refresh it')
    else:
        if body.version!=0:raise HTTPException(409,'Fact not found; use version zero')
        s.add(LocalFact(id=identifier,place_id=body.place_id,payload=json.dumps(data),version=1))
    audit(s,identifier,'local_fact_checked')
    try:s.commit()
    except IntegrityError:s.rollback();raise HTTPException(409,'Concurrent fact update')
    return next(f for f in facts(s,body.place_id) if f['field']==body.field)

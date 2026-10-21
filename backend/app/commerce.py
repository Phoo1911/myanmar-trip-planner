import os, json, secrets, hashlib, hmac
from datetime import date, datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, EmailStr, AwareDatetime
from sqlalchemy import String, Text, Integer, select, update
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError
from .main import Base, db, admin, Audit, Names
router=APIRouter()
class Inventory(Base):
    __tablename__='inventory'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    payload:Mapped[str]=mapped_column(Text)
    remaining:Mapped[int]=mapped_column(Integer)
    version:Mapped[int]=mapped_column(Integer,default=1)
    valid_until:Mapped[str]=mapped_column(String(40))
class Reservation(Base):
    __tablename__='reservations'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    key:Mapped[str]=mapped_column(String(64),unique=True)
    fingerprint:Mapped[str]=mapped_column(String(64))
    token_hash:Mapped[str]=mapped_column(String(64))
    inventory_id:Mapped[str]=mapped_column(String(64))
    guests:Mapped[int]=mapped_column(Integer)
    payload:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(20))
class OfferInput(BaseModel):
    name:Names
    supplier:str=Field(min_length=2,max_length=120)
    contract_reference:str=Field(min_length=5,max_length=200)
    confirmation_authority:Literal[True]
    kind:Literal['stay','transport','tour']
    place_id:Literal['yangon','bagan','inle']
    service_date:date
    capacity:int=Field(ge=1,le=500)
    price_minor:int=Field(ge=1,le=1000000000)
    currency:Literal['USD','MMK']
    valid_until:AwareDatetime
    payment:Literal['pay_at_property']='pay_at_property'
    cancellation:Literal['free_before_service_date']='free_before_service_date'
def now():return datetime.now(timezone.utc)
def public(i):
    data=json.loads(i.payload)
    data.pop('contract_reference',None)
    data.update(valid_until=i.valid_until,id=i.id,remaining=i.remaining,version=i.version,mode='instant',unit='person',taxes_included=True)
    return data
@router.post('/admin/offers',status_code=201,dependencies=[Depends(admin)])
def publish(body:OfferInput,s:Session=Depends(db)):
    if body.service_date<=date.today():raise HTTPException(422,'Service must start after today')
    if not now()<body.valid_until<=now()+timedelta(days=7):raise HTTPException(422,'Verification validity must be within seven days')
    data=body.model_dump(mode='json');data['verified_at']=now().isoformat()
    i=Inventory(id=secrets.token_hex(16),payload=json.dumps(data),remaining=body.capacity,version=1,valid_until=body.valid_until.isoformat())
    s.add(i);s.add(Audit(id=secrets.token_hex(16),booking_id=i.id,action='inventory_verified',created_at=now().isoformat()));s.commit()
    return public(i)
@router.get('/offers')
def offers(s:Session=Depends(db)):
    return [public(i) for i in s.scalars(select(Inventory)) if i.remaining>0 and datetime.fromisoformat(i.valid_until)>now() and json.loads(i.payload)['service_date']>date.today().isoformat()]
class Purchase(BaseModel):
    inventory_id:str=Field(min_length=1,max_length=64)
    version:int=Field(ge=1)
    guests:int=Field(ge=1,le=20)
    email:EmailStr
    safety_ack:Literal[True]
    terms_ack:Literal[True]
def receipt(r,token):
    return {'id':r.id,'token':token,'status':r.status,'details':json.loads(r.payload)}
@router.post('/reservations',status_code=201)
def reserve(body:Purchase,idempotency_key:str=Header(min_length=16,max_length=128),s:Session=Depends(db)):
    secret=os.getenv('RECEIPT_SECRET','')
    if len(secret)<32:raise HTTPException(503,'Receipt secret not configured')
    key=hashlib.sha256(idempotency_key.encode()).hexdigest();fp=hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    token=hmac.new(secret.encode(),('reservation:'+idempotency_key).encode(),hashlib.sha256).hexdigest()
    old=s.scalar(select(Reservation).where(Reservation.key==key))
    if old:
        if old.fingerprint!=fp:raise HTTPException(409,'Different request for this key')
        return receipt(old,token)
    inventory=s.get(Inventory,body.inventory_id)
    if not inventory:raise HTTPException(404,'Offer not found')
    details=json.loads(inventory.payload)
    if datetime.fromisoformat(inventory.valid_until)<=now() or details['service_date']<=date.today().isoformat():raise HTTPException(409,'Verification expired')
    result=s.execute(update(Inventory).where(Inventory.id==body.inventory_id,Inventory.version==body.version,Inventory.remaining>=body.guests).values(remaining=Inventory.remaining-body.guests,version=Inventory.version+1))
    if result.rowcount!=1:raise HTTPException(409,'Inventory or price changed. Refresh offers')
    snapshot={**public(inventory),'email':str(body.email),'guests':body.guests,'total_minor':details['price_minor']*body.guests,'payment_status':'unpaid','confirmation_scope':'operator_allocated_inventory','booked_at':now().isoformat()}
    reservation=Reservation(id=secrets.token_hex(16),key=key,fingerprint=fp,token_hash=hashlib.sha256(token.encode()).hexdigest(),inventory_id=body.inventory_id,guests=body.guests,payload=json.dumps(snapshot),status='confirmed')
    s.add(reservation);s.add(Audit(id=secrets.token_hex(16),booking_id=reservation.id,action='reservation_confirmed',created_at=now().isoformat()))
    try:s.commit()
    except IntegrityError:s.rollback();raise HTTPException(409,'Concurrent retry; repeat same request')
    return receipt(reservation,token)
def owned(s,bid,authorization):
    r=s.get(Reservation,bid)
    if not r or not secrets.compare_digest(r.token_hash,hashlib.sha256(authorization.removeprefix('Bearer ').encode()).hexdigest()):raise HTTPException(404,'Not found')
    return r
@router.get('/reservations/{bid}')
def lookup(bid:str,authorization:str=Header(default=''),s:Session=Depends(db)):
    r=owned(s,bid,authorization);return {'id':r.id,'status':r.status,'details':json.loads(r.payload)}
@router.post('/reservations/{bid}/cancel')
def cancel(bid:str,authorization:str=Header(default=''),s:Session=Depends(db)):
    r=owned(s,bid,authorization)
    if r.status=='cancelled':return {'status':'cancelled'}
    if json.loads(r.payload)['service_date']<=date.today().isoformat():raise HTTPException(409,'Cancellation window closed')
    result=s.execute(update(Reservation).where(Reservation.id==bid,Reservation.status=='confirmed').values(status='cancelled'))
    if result.rowcount!=1:raise HTTPException(409,'Already modified')
    s.execute(update(Inventory).where(Inventory.id==r.inventory_id).values(remaining=Inventory.remaining+r.guests,version=Inventory.version+1))
    s.add(Audit(id=secrets.token_hex(16),booking_id=bid,action='reservation_cancelled',created_at=now().isoformat()));s.commit();return {'status':'cancelled'}
@router.get('/admin/reservations',dependencies=[Depends(admin)])
def reservations(s:Session=Depends(db)):
    return [{'id':r.id,'status':r.status,'details':json.loads(r.payload)} for r in s.scalars(select(Reservation).limit(100))]

@router.get('/admin/offers',dependencies=[Depends(admin)])
def inventory_admin(s:Session=Depends(db)):
    return [public(i) for i in s.scalars(select(Inventory).limit(200))]
@router.patch('/admin/offers/{bid}/close',dependencies=[Depends(admin)])
def close_offer(bid:str,s:Session=Depends(db)):
    changed=s.execute(update(Inventory).where(Inventory.id==bid).values(valid_until=now().isoformat(),version=Inventory.version+1))
    if changed.rowcount!=1:raise HTTPException(404,'Not found')
    s.add(Audit(id=secrets.token_hex(16),booking_id=bid,action='inventory_closed',created_at=now().isoformat()));s.commit();return {'status':'closed'}

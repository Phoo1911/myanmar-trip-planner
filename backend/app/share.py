"""Unlisted share links for a trip: public place data and a saved order only, no contact or account data."""
import json, secrets, time
from typing import Literal, Optional
from urllib.parse import urlparse, parse_qsl
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, Text, Integer, delete
from sqlalchemy.orm import Mapped, mapped_column, Session
from .main import Base, db

TTL=30*86400
HOSTS=('facebook.com','tiktok.com','youtube.com','youtu.be','instagram.com','openstreetmap.org','geonames.org')
router=APIRouter(prefix='/trips')

class SharedTrip(Base):
    __tablename__='shared_trips'
    id:Mapped[str]=mapped_column(String(32),primary_key=True)
    payload:Mapped[str]=mapped_column(Text)
    expires:Mapped[int]=mapped_column(Integer,index=True)

def safe_reference(url):
    # Mirrors the frontend storage allowlist: public HTTPS posts or map sources, no credentials or tokens.
    try:parsed=urlparse(url)
    except ValueError:return False
    host=(parsed.hostname or '').lower()
    return len(url)<=1000 and parsed.scheme=='https' and not parsed.username and not parsed.password and parsed.port in (None,443) and any(host==d or host.endswith('.'+d) for d in HOSTS) and not any(k.lower() in ('access_token','token','api_key','password','key') for k,_ in parse_qsl(parsed.query))

class Spot(BaseModel):
    id:str=Field(min_length=1,max_length=128)
    name:dict[Literal['ko','en','my'],str]
    lat:float=Field(ge=9,le=29)
    lng:float=Field(ge=92,le=102)
    references:list[str]=Field(default_factory=list,max_length=8)
    coordinate_scope:Optional[Literal['city_centre']]=None
    auto_located:Optional[Literal[True]]=None
    @field_validator('name')
    @classmethod
    def names(cls,value):
        if set(value)!={'ko','en','my'} or any(not 0<len(v)<=200 for v in value.values()):raise ValueError('Names required in ko, en and my')
        return value
class Day(BaseModel):
    day:int=Field(ge=1,le=14)
    stop_ids:list[str]=Field(max_length=4)
class Draft(BaseModel):
    days:int=Field(ge=1,le=14)
    route:list[Day]=Field(min_length=1,max_length=14)
class ShareInput(BaseModel):
    places:list[Spot]=Field(min_length=1,max_length=24)
    draft:Optional[Draft]=None

@router.post('')
def create(body:ShareInput,s:Session=Depends(db)):
    ids=[p.id for p in body.places]
    if len(set(ids))!=len(ids):raise HTTPException(422,'Duplicate places')
    if body.draft:
        stops=[i for d in body.draft.route for i in d.stop_ids]
        if [d.day for d in body.draft.route]!=list(range(1,body.draft.days+1)) or sorted(stops)!=sorted(ids):raise HTTPException(422,'Saved order must cover every place once')
    places=[{**p.model_dump(exclude_none=True),'references':[u for u in p.references if safe_reference(u)]} for p in body.places]
    now=int(time.time());identifier=secrets.token_urlsafe(16)
    s.execute(delete(SharedTrip).where(SharedTrip.expires<now))
    s.add(SharedTrip(id=identifier,payload=json.dumps({'places':places,'draft':body.draft.model_dump() if body.draft else None}),expires=now+TTL));s.commit()
    return {'id':identifier,'expires_at':now+TTL,'contains_personal_data':False}

@router.get('/{identifier}')
def read(identifier:str,s:Session=Depends(db)):
    if not 16<=len(identifier)<=32:raise HTTPException(404,'Shared trip not found')
    row=s.get(SharedTrip,identifier)
    if not row or row.expires<int(time.time()):raise HTTPException(404,'Shared trip not found or expired')
    return {**json.loads(row.payload),'expires_at':row.expires}

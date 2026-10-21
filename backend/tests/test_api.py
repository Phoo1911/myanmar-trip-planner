import os
os.environ['DATABASE_URL']='sqlite://'
os.environ['RATE_LIMIT_ENABLED']='false'
os.environ['ADMIN_TOKEN']='a'*40
os.environ['RECEIPT_SECRET']='b'*40
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app import main as m
m.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
m.Base.metadata.create_all(m.engine)
c=TestClient(m.app)
headers={'Authorization':'Bearer '+'a'*40}
def body(): return dict(product_id='stay',place_id='yangon',start_date='2099-01-01',guests=2,email='test@example.com',language='ko',safety_ack=True)
def test_request_flow():
    h={'Idempotency-Key':'request-test-0001'}
    a=c.post('/bookings',json=body(),headers=h);assert a.status_code==201
    b=a.json();assert c.post('/bookings',json=body(),headers=h).json()==b
    assert c.post('/bookings',json={**body(),'guests':3},headers=h).status_code==409
    assert c.get('/bookings/'+b['id']).status_code==404
    assert c.get('/bookings/'+b['id'],headers={'Authorization':'Bearer '+b['token']}).json()['reservation_confirmed'] is False
    assert c.get('/admin/bookings').status_code==401
    assert c.patch('/admin/bookings/'+b['id'],json={'status':'approved','version':1}).status_code==401
    assert c.patch('/admin/bookings/'+b['id'],json={'status':'approved','version':1},headers=headers).status_code==200
    assert c.patch('/admin/bookings/'+b['id'],json={'status':'rejected','version':1},headers=headers).status_code==409
    assert c.patch('/admin/bookings/'+b['id'],json={'status':'confirmed','version':2},headers=headers).status_code==422
    assert c.get('/admin/bookings',headers=headers).json()[0]['status']=='approved'
def test_invalid_requests():
    for delta in [{'guests':0},{'safety_ack':False},{'product_id':'fake'},{'start_date':'2000-01-01'},{'email':'bad'}]:
        assert c.post('/bookings',json={**body(),**delta},headers={'Idempotency-Key':'validation-test-01'}).status_code==422
    assert c.post('/bookings',json=body()).status_code==422
def test_public_contract():
    assert c.get('/health').status_code==200
    assert len(c.get('/places?q=양곤').json())==1
    assert c.get('/places?q=nonexistent').json()==[]
    assert all(p['price'] is None and p['availability'] is None and p['mode']=='request_only' for p in c.get('/products').json())
    assert c.get('/safety').json()['live'] is False
def test_plan_template_and_validation():
    with patch.dict(os.environ,{'OPENAI_API_KEY':''}):
        p=c.post('/itineraries',json={'destination_ids':['yangon'],'days':3}).json()
        assert p['mode']=='template' and len(p['days'])==3
    assert c.post('/itineraries',json={'destination_ids':['fake'],'days':2}).status_code==422
    assert c.post('/itineraries',json={'destination_ids':['yangon'],'days':15}).status_code==422
def test_ai_bounds():
    class Response:
        def raise_for_status(self): pass
        def json(self):return {'output':[{'content':[{'type':'output_text','text':'{"days":[{"day":1,"place_id":"bagan"}]}'}]}]}
    with patch.dict(os.environ,{'OPENAI_API_KEY':'test'}),patch('app.main.httpx.post',return_value=Response()):
        assert c.post('/itineraries',json={'destination_ids':['yangon'],'days':1}).status_code==502
    class Good(Response):
        def json(self):return {'output':[{'content':[{'type':'output_text','text':'{"days":[{"day":1,"place_id":"yangon"}]}'}]}]}
    with patch.dict(os.environ,{'OPENAI_API_KEY':'test'}),patch('app.main.httpx.post',return_value=Good()):
        assert c.post('/itineraries',json={'destination_ids':['yangon'],'days':1}).json()['mode']=='ai'

def test_shared_limiter_and_proxy():
    with patch.dict(os.environ,{'RATE_LIMIT_ENABLED':'true','RATE_LIMIT_PER_MINUTE':'1'}):
        assert c.post('/itineraries',json={'destination_ids':['yangon'],'days':1}).status_code==200
        assert c.post('/itineraries',json={'destination_ids':['yangon'],'days':1}).status_code==429
    with patch.dict(os.environ,{'REQUIRE_PROXY_TOKEN':'true','INTERNAL_PROXY_TOKEN':'proxy-test'}):
        assert c.get('/places').status_code==401
        assert c.get('/places',headers={'X-Internal-Token':'proxy-test'}).status_code==200
def test_social_curation():
    assert all(p.get('source_kind')=='openstreetmap' for p in c.get('/hotspots').json())
    with patch.dict(os.environ,{'YOUTUBE_API_KEY':''}):
        assert c.post('/admin/social/sync',headers=headers,json={'place_id':'yangon'}).status_code==503
    assert c.get('/admin/social').status_code==401
    from datetime import datetime,timezone,timedelta
    import json
    with m.Session(m.engine) as s:
        s.add(m.SocialVideo(id='abcdefghijk',payload=json.dumps({'id':'abcdefghijk','place_id':'yangon','title':'Synthetic test','url':'https://www.youtube.com/watch?v=abcdefghijk','views':100,'likes':3,'score':10,'collected_at':datetime.now(timezone.utc).isoformat(),'published_at':datetime.now(timezone.utc).isoformat()})));s.commit()
    data={'video_id':'abcdefghijk','name':{'ko':'테스트','en':'Test','my':'စမ်းသပ်'},'place_id':'yangon','category':'cafe','lat':16.8,'lng':96.1,'location_source':'https://example.com/location','location_verified':True}
    assert c.post('/admin/hotspots',json={**data,'location_verified':False},headers=headers).status_code==422
    assert c.post('/admin/hotspots',json={**data,'lat':0},headers=headers).status_code==422
    assert c.post('/admin/hotspots',json=data,headers=headers).status_code==201
    assert c.post('/admin/hotspots',json=data,headers=headers).status_code==409
    assert c.get('/hotspots?q=테스트&category=cafe').json()[0]['price'] is None
    assert not any(p['id']=='abcdefghijk' for p in c.get('/hotspots?category=heritage').json())
    with m.Session(m.engine) as s:
        v=s.get(m.SocialVideo,'abcdefghijk');old=json.loads(v.payload);old['collected_at']=(datetime.now(timezone.utc)-timedelta(days=31)).isoformat();v.payload=json.dumps(old);s.commit()
    assert all(p.get('source_kind')=='openstreetmap' for p in c.get('/hotspots').json())

def test_allocated_inventory_reservation_and_cancellation():
    from datetime import datetime,timezone,timedelta,date
    now=datetime.now(timezone.utc)
    offer={'name':{'ko':'합성 테스트 투어','en':'Synthetic test tour','my':'စမ်းသပ်'},'supplier':'Synthetic supplier','contract_reference':'TEST-CONTRACT-ONLY','confirmation_authority':True,'kind':'tour','place_id':'yangon','service_date':(date.today()+timedelta(days=10)).isoformat(),'capacity':2,'price_minor':1050,'currency':'USD','valid_until':(now+timedelta(hours=4)).isoformat()}
    assert c.post('/admin/offers',json=offer).status_code==401
    assert c.post('/admin/offers',headers=headers,json={**offer,'confirmation_authority':False}).status_code==422
    published=c.post('/admin/offers',headers=headers,json=offer);assert published.status_code==201
    item=published.json();assert 'contract_reference' not in item
    request={'inventory_id':item['id'],'version':1,'guests':2,'email':'synthetic@example.com','safety_ack':True,'terms_ack':True}
    h={'Idempotency-Key':'instant-reserve-test-01'}
    response=c.post('/reservations',json=request,headers=h);assert response.status_code==201
    receipt=response.json();assert receipt['status']=='confirmed' and receipt['details']['total_minor']==2100 and receipt['details']['payment_status']=='unpaid'
    assert c.post('/reservations',json=request,headers=h).json()==receipt
    assert c.post('/reservations',json={**request,'guests':1},headers={'Idempotency-Key':'another-reserve-test-02'}).status_code==409
    assert all(o['id']!=item['id'] for o in c.get('/offers').json())
    assert c.get('/reservations/'+receipt['id']).status_code==404
    auth={'Authorization':'Bearer '+receipt['token']}
    assert c.get('/reservations/'+receipt['id'],headers=auth).json()['status']=='confirmed'
    assert c.post('/reservations/'+receipt['id']+'/cancel',headers=auth).json()['status']=='cancelled'
    assert c.post('/reservations/'+receipt['id']+'/cancel',headers=auth).json()['status']=='cancelled'
    restored=next(o for o in c.get('/offers').json() if o['id']==item['id']);assert restored['remaining']==2
    assert c.post('/reservations',json={**request,'guests':1},headers={'Idempotency-Key':'stale-version-test-03'}).status_code==409
    assert c.get('/admin/reservations').status_code==401

def test_social_links_and_route():
    data={'url':'https://www.tiktok.com/@synthetic/video/123456789','title':'Synthetic candidate','place_id':'yangon'}
    for bad in ['https://evil.example/video','javascript:alert(1)','https://tiktok.com.evil.example/test','https://user:password@facebook.com/test']:
        assert c.post('/social/links',json={**data,'url':bad}).status_code==422
    response=c.post('/social/links',json=data);assert response.status_code==201
    identifier=response.json()['id'];assert response.json()['automatic_analysis'] is False
    assert c.post('/social/links',json=data).json()['id']==identifier
    candidate=next(v for v in c.get('/admin/social',headers=headers).json() if v['id']==identifier)
    assert candidate['views'] is None and candidate['score'] is None
    spot={'video_id':identifier,'name':{'ko':'합성 카페','en':'Synthetic cafe','my':'စမ်းသပ်'},'place_id':'yangon','category':'cafe','lat':16.8,'lng':96.1,'location_source':'https://example.com/verified-location','location_verified':True}
    assert c.post('/admin/hotspots',headers=headers,json=spot).status_code==201
    route=c.post('/routes',json={'hotspot_ids':[identifier],'days':1});assert route.status_code==200
    assert route.json()['road_routing'] is False and route.json()['days'][0]['stops'][0]['id']==identifier
    assert c.post('/routes',json={'hotspot_ids':['not-published'],'days':1}).status_code==422

def test_last_slot_concurrent_bookings(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime,timezone,timedelta,date
    engine=create_engine('sqlite:///'+str(tmp_path/'race.db'),connect_args={'check_same_thread':False})
    m.Base.metadata.create_all(engine);monkeypatch.setattr(m,'engine',engine)
    offer={'name':{'ko':'동시성 테스트','en':'Race test','my':'စမ်းသပ်'},'supplier':'Synthetic only','contract_reference':'TEST-RACE-ONLY','confirmation_authority':True,'kind':'tour','place_id':'yangon','service_date':(date.today()+timedelta(days=3)).isoformat(),'capacity':1,'price_minor':100,'currency':'USD','valid_until':(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()}
    item=c.post('/admin/offers',headers=headers,json=offer).json()
    payload={'inventory_id':item['id'],'version':1,'guests':1,'email':'race@example.com','safety_ack':True,'terms_ack':True}
    def book(n):return c.post('/reservations',json=payload,headers={'Idempotency-Key':'concurrent-request-'+str(n)}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(book,[1,2]))
    assert sorted(results)==[201,409]
    assert c.get('/offers').json()==[]
    assert c.patch('/admin/offers/'+item['id']+'/close',headers=headers).status_code==200
    engine.dispose()


def test_mapped_catalog_search_references_and_route():
    data=c.get('/catalog').json()
    assert data['license']=='https://opendatacommons.org/licenses/odbl/1-0/'
    places=data['places'];assert len(places)>=6
    assert len({p['id'] for p in places})==len(places)
    for p in places:
        assert 9<=p['lat']<=29 and 92<=p['lng']<=102
        assert p['source'].startswith('https://www.openstreetmap.org/')
        assert p['price'] is None and p['availability'] is None
        assert p['location_verified'] is False
    first=places[0]
    found=c.get('/hotspots',params={'q':first['name']['en'],'place_id':first['place_id'],'category':first['category']}).json()
    assert any(p['id']==first['id'] for p in found)
    assert all(p['evidence']['score'] is None for p in found if p.get('source_kind')=='openstreetmap')
    assert c.get('/hotspots?q=impossible-catalog-search-887799').json()==[]
    same_region=[p['id'] for p in places if p['place_id']==first['place_id']][:2]
    route=c.post('/routes',json={'hotspot_ids':same_region,'days':1})
    assert route.status_code==200
    assert {p['id'] for p in route.json()['days'][0]['stops']}==set(same_region)
    assert route.json()['road_routing'] is False

def test_concierge_private_quote_accept_and_confirmation():
    from datetime import date,timedelta,datetime,timezone
    preferences={'region':'yangon','start_date':(date.today()+timedelta(days=15)).isoformat(),'days':2,'guests':2,'interests':['heritage','cafe'],'pace':'relaxed','mobility_needs':'Synthetic low-walking request','services':['transport'],'notes':'Synthetic fixture','language':'ko'}
    preview=c.post('/concierge/preview',json=preferences)
    assert preview.status_code==200 and preview.json()['mode']=='catalog_draft'
    assert 'cafe' in preview.json()['unmatched_interests']
    assert preview.json()['road_routing'] is False
    body={**preferences,'email':'synthetic@example.com','safety_ack':True,'privacy_ack':True}
    key={'Idempotency-Key':'concierge-synthetic-0001'}
    created=c.post('/concierge/requests',json=body,headers=key);assert created.status_code==201
    receipt=created.json();bid=receipt['id'];owner={'Authorization':'Bearer '+receipt['token']}
    assert c.post('/concierge/requests',json=body,headers=key).json()['id']==bid
    assert c.post('/concierge/requests',json={**body,'guests':3},headers=key).status_code==409
    assert c.get('/concierge/requests/'+bid).status_code==404
    assert c.get('/concierge/admin/requests').status_code==401
    assert 'token' not in c.get('/concierge/admin/requests',headers=headers).json()[0]
    q={'version':1,'supplier':'Synthetic supplier','service':'transport','total_minor':10000,'currency':'USD','valid_until':(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(),'includes':'Synthetic car total','exclusions':'Meals excluded','cancellation':'Free before service date','source_reference':'synthetic-written-quote','supplier_verified':True,'taxes_included':True}
    assert c.post('/concierge/admin/requests/'+bid+'/quotes',json=q).status_code==401
    assert c.post('/concierge/admin/requests/'+bid+'/quotes',headers=headers,json={**q,'total_minor':0}).status_code==422
    quoted=c.post('/concierge/admin/requests/'+bid+'/quotes',headers=headers,json=q);assert quoted.status_code==200
    assert 'source_reference' not in quoted.json()['quotes'][0]
    assert c.post('/concierge/admin/requests/'+bid+'/quotes',headers=headers,json=q).status_code==409
    quote_id=quoted.json()['quotes'][0]['id'];accept={'version':2,'quote_id':quote_id,'terms_ack':True}
    assert c.post('/concierge/requests/'+bid+'/accept',json=accept).status_code==404
    accepted=c.post('/concierge/requests/'+bid+'/accept',headers=owner,json=accept);assert accepted.status_code==200 and accepted.json()['status']=='quote_accepted'
    assert c.post('/concierge/requests/'+bid+'/accept',headers=owner,json=accept).json()['version']==3
    confirmation={'version':3,'booking_reference':'SYNTHETIC-001','source_reference':'synthetic-written-confirmation','confirmation_authority':True,'written_supplier_confirmation':True}
    assert c.post('/concierge/admin/requests/'+bid+'/confirm',headers=headers,json={**confirmation,'confirmation_authority':False}).status_code==422
    confirmed=c.post('/concierge/admin/requests/'+bid+'/confirm',headers=headers,json=confirmation)
    assert confirmed.status_code==200 and confirmed.json()['status']=='supplier_confirmed'
    assert confirmed.json()['payment_status']=='unpaid' and confirmed.json()['automatic_supplier_delivery'] is False
    assert 'confirmation_evidence' not in confirmed.json()
    message={'version':4,'text':'Synthetic question','language':'ko'}
    assert c.post('/concierge/requests/'+bid+'/messages',headers=owner,json={**message,'translations':{'en':'unreviewed'}}).status_code==422
    assert c.post('/concierge/requests/'+bid+'/messages',headers=owner,json=message).status_code==200
    assert c.post('/concierge/requests/'+bid+'/messages',headers=owner,json=message).status_code==409
    reply={'version':5,'text':'Synthetic operator reply','language':'en','translations':{'ko':'합성 검증 답변'},'translation_reviewed':True}
    assert c.post('/concierge/admin/requests/'+bid+'/messages',headers=headers,json=reply).status_code==200
    assert c.get('/concierge/requests/'+bid,headers=owner).json()['messages'][-1]['translation_reviewed'] is True

def test_concierge_fact_expiry_and_expired_quote():
    from datetime import date,datetime,timezone,timedelta
    import json
    place=m.catalog_places()[0]['id'];now=datetime.now(timezone.utc)
    fact={'place_id':place,'field':'cash_only','value':'yes','source':'https://example.com/synthetic-evidence','checked_at':now.isoformat(),'valid_until':(now+timedelta(days=1)).isoformat(),'version':0,'locally_verified':True}
    assert c.post('/concierge/admin/facts',json=fact).status_code==401
    assert c.post('/concierge/admin/facts',headers=headers,json={**fact,'checked_at':(now+timedelta(days=1)).isoformat()}).status_code==422
    assert c.post('/concierge/admin/facts',headers=headers,json=fact).status_code==200
    assert c.post('/concierge/admin/facts',headers=headers,json=fact).status_code==409
    assert c.get('/hotspots').json()[0]['local_facts'][0]['value']=='yes'
    from app.concierge import LocalFact,JourneyRequest
    with m.Session(m.engine) as s:
        row=s.scalar(m.select(LocalFact));data=json.loads(row.payload);data['valid_until']=(now-timedelta(seconds=1)).isoformat();row.payload=json.dumps(data);s.commit()
    expired=c.get('/concierge/facts',params={'place_id':place}).json()[0]
    assert expired['expired'] is True and expired['value']=='unknown'
    body={'region':'bagan','start_date':(date.today()+timedelta(days=15)).isoformat(),'days':1,'guests':1,'interests':['heritage'],'email':'expiry@example.com','safety_ack':True,'privacy_ack':True}
    receipt=c.post('/concierge/requests',headers={'Idempotency-Key':'concierge-expiry-0001'},json=body).json();bid=receipt['id']
    q={'version':1,'supplier':'Synthetic only','service':'guide','total_minor':5000,'currency':'MMK','valid_until':(now+timedelta(hours=1)).isoformat(),'includes':'Guide total','exclusions':'Meals excluded','cancellation':'Synthetic terms','source_reference':'synthetic-source','supplier_verified':True,'taxes_included':True}
    quoted=c.post('/concierge/admin/requests/'+bid+'/quotes',headers=headers,json=q).json()
    with m.Session(m.engine) as s:
        row=s.get(JourneyRequest,bid);data=json.loads(row.payload);data['quotes'][0]['valid_until']=(now-timedelta(seconds=1)).isoformat();row.payload=json.dumps(data);s.commit()
    assert c.post('/concierge/requests/'+bid+'/accept',headers={'Authorization':'Bearer '+receipt['token']},json={'version':2,'quote_id':quoted['quotes'][0]['id'],'terms_ack':True}).status_code==409

def test_concierge_draft_excludes_verified_closed_places():
    from datetime import date,datetime,timezone,timedelta
    p=m.catalog_places()[0];now=datetime.now(timezone.utc)
    body={'place_id':p['id'],'field':'opening','value':'no','source':'https://example.com/synthetic-closure','checked_at':now.isoformat(),'valid_until':(now+timedelta(days=1)).isoformat(),'version':0,'locally_verified':True}
    assert c.post('/concierge/admin/facts',headers=headers,json=body).status_code==200
    preview=c.post('/concierge/preview',json={'region':p['place_id'],'start_date':(date.today()+timedelta(days=14)).isoformat(),'days':2,'guests':2,'interests':['heritage']}).json()
    assert all(stop['id']!=p['id'] for day in preview['days'] for stop in day['stops'])

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

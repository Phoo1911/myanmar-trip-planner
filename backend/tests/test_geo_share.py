import json, os, time
from unittest.mock import patch
import httpx, pytest
from test_api import c
from test_recommendations import fake_provider, PID
from app import geo, recommendations as ai
from app.main import Session, engine
from app.share import SharedTrip

def geo_result(name='Rangoon Tea House',kind='amenity',confidence=0.95,lat=16.7745,lng=96.1590):
    return {'results':[{'name':name,'lat':lat,'lon':lng,'result_type':kind,'rank':{'confidence':confidence},'place_id':'abc'+name,'categories':['catering.cafe'],'datasource':{'raw':{'osm_type':'n','osm_id':123}}}]}

def test_geocode_accepts_only_confident_named_venues():
    geo._cache.clear()
    with patch.dict(os.environ,{'GEOAPIFY_API_KEY':'synthetic'}),Session(engine) as s:
        with patch.object(geo.httpx,'get',return_value=httpx.Response(200,json=geo_result())) as get:
            place=geo.geocode('Rangoon Tea House',s)
            assert place['id'].startswith('geo:') and place['auto_located'] is True and place['location_verified'] is False
            assert place['category']=='cafe' and place['source']=='https://www.openstreetmap.org/node/123' and place['price'] is None
            assert get.call_args.kwargs['params']['filter']=='countrycode:mm'
            assert geo.geocode('rangoon tea house',s)==place and get.call_count==1
        for bad in [geo_result(kind='street'),geo_result(confidence=0.5),geo_result(name='Other Cafe'),geo_result(lat=1.0)]:
            geo._cache.clear()
            with patch.object(geo.httpx,'get',return_value=httpx.Response(200,json=bad)):
                assert geo.geocode('Rangoon Tea House',s) is None
    with patch.dict(os.environ,{'GEOAPIFY_API_KEY':''}),Session(engine) as s:
        with pytest.raises(geo.HTTPException) as error:geo.geocode('Rangoon Tea House',s)
        assert error.value.status_code==503
    geo._cache.clear()
    with patch.dict(os.environ,{'GEOAPIFY_API_KEY':'synthetic','GEOAPIFY_DAILY_LIMIT':'0'}),Session(engine) as s,patch.object(geo.httpx,'get') as get:
        with pytest.raises(geo.HTTPException) as error:geo.geocode('Rangoon Tea House',s)
        assert error.value.status_code==429;get.assert_not_called()

def test_road_times_validated():
    stops=[{'id':'a','lat':16.79,'lng':96.14},{'id':'b','lat':16.78,'lng':96.16}]
    good={'results':[{'distance':4200,'time':900,'legs':[{'distance':4200,'time':900}]}]}
    with patch.dict(os.environ,{'GEOAPIFY_API_KEY':''}):
        assert c.post('/routes/road',json={'days':[{'day':1,'stops':stops}]}).status_code==503
    with patch.dict(os.environ,{'GEOAPIFY_API_KEY':'synthetic'}):
        with patch.object(geo.httpx,'get',return_value=httpx.Response(200,json=good)) as get:
            r=c.post('/routes/road',json={'days':[{'day':1,'stops':stops},{'day':2,'stops':stops[:1]}]})
            assert r.status_code==200,r.text
            data=r.json();assert data['days'][0]['time_s']==900 and data['days'][0]['legs'][0]['to']=='b' and data['days'][1]['legs']==[]
            assert data['traffic_included'] is False and data['verified'] is False and get.call_count==1
        with patch.object(geo.httpx,'get',return_value=httpx.Response(200,json={'results':[{'distance':-1,'time':1,'legs':[{}]}]})):
            assert c.post('/routes/road',json={'days':[{'day':1,'stops':stops}]}).status_code==502
        with patch.object(geo.httpx,'get',return_value=httpx.Response(500,json={})):
            assert c.post('/routes/road',json={'days':[{'day':1,'stops':stops}]}).status_code==502
        assert c.post('/routes/road',json={'days':[{'day':1,'stops':stops*3}]}).status_code==422
        assert c.post('/routes/road',json={'days':[{'day':1,'stops':[{'id':'x','lat':40,'lng':96}]}]}).status_code==422

def test_new_places_must_be_named_in_cited_excerpt():
    excerpt={'title':'Yangon cafe tour','excerpt':'We loved tea at Rangoon Tea House near Sule.','url':'https://www.youtube.com/watch?v=abc','places':[]}
    def model(names):
        def provider(operation,payload,key,**_):
            if 'generateContent' in operation and 'Convert untrusted' in payload['systemInstruction']['parts'][0]['text']:
                return {'candidates':[{'content':{'parts':[{'text':'{"query":"Yangon cafes"}'}]}}]}
            data=fake_provider(operation,payload,key)
            if 'generateContent' in operation:
                value=json.loads(data['candidates'][0]['content']['parts'][0]['text'])
                value['new_places']=[{'name':n,'evidence_id':'content:0','reason':'Mentioned for tea.'} for n in names]
                data['candidates'][0]['content']['parts'][0]['text']=json.dumps(value)
            return data
        return provider
    env={'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':'synthetic'}
    located={'id':'geo:'+'a'*24,'name':{'ko':'Rangoon Tea House','en':'Rangoon Tea House','my':'Rangoon Tea House'},'lat':16.77,'lng':96.16,'auto_located':True,'location_verified':False}
    with patch.dict(os.environ,env),patch.object(ai,'consume'),patch.object(ai,'search',return_value={'items':[excerpt]}),patch.object(ai,'provider',side_effect=model(['Rangoon Tea House','Invented Rooftop Bar'])),patch.object(geo,'geocode',return_value=located) as lookup:
        ai._vectors.clear()
        r=c.post('/discovery/recommend',json={'query':'tea and cafes','language':'en'})
        assert r.status_code==200,r.text
        data=r.json();assert [a['place']['id'] for a in data['auto_places']]==[located['id']] and data['unlocated']==[]
        assert data['auto_places'][0]['sources'][0]['url']==excerpt['url'] and lookup.call_count==1
    with patch.dict(os.environ,env),patch.object(ai,'consume'),patch.object(ai,'search',return_value={'items':[excerpt]}),patch.object(ai,'provider',side_effect=model(['Rangoon Tea House'])),patch.object(geo,'geocode',side_effect=geo.HTTPException(503,'no key')):
        ai._vectors.clear()
        data=c.post('/discovery/recommend',json={'query':'tea and cafes','language':'en'}).json()
        assert data['auto_places']==[] and data['unlocated'][0]['name']=='Rangoon Tea House' and data['geocoding']=='unavailable'

def test_ai_failure_reports_fixed_reason_code():
    def cut(operation,payload,key,**_):
        data=fake_provider(operation,payload,key)
        if 'generateContent' in operation:data['candidates'][0]['finishReason']='MAX_TOKENS'
        return data
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':''}),patch.object(ai,'consume'),patch.object(ai,'provider',side_effect=cut):
        ai._vectors.clear()
        r=c.post('/discovery/recommend',json={'query':'temple travel'})
        assert r.status_code==502 and '(Truncated output)' in r.json()['detail']

def test_routes_accept_auto_located_places():
    auto={'id':'geo:'+'b'*24,'name':{'ko':'찻집','en':'Tea house','my':'လက်ဖက်ရည်ဆိုင်'},'lat':16.775,'lng':96.159}
    r=c.post('/routes',json={'hotspot_ids':[PID],'auto_places':[auto],'days':1})
    assert r.status_code==200,r.text
    stops=r.json()['days'][0]['stops'];assert {s['id'] for s in stops}=={PID,auto['id']}
    assert next(s for s in stops if s['id']==auto['id'])['location_verified'] is False
    assert c.post('/routes',json={'auto_places':[{**auto,'id':'geo:not-hex'}],'days':1}).status_code==422
    assert c.post('/routes',json={'auto_places':[{**auto,'lat':40}],'days':1}).status_code==422
    assert c.post('/routes',json={'days':1}).status_code==422

def test_share_links_store_only_public_trip_data():
    place={'id':PID,'name':{'ko':'술레','en':'Sule','my':'ဆူးလေ'},'lat':16.7745,'lng':96.1588,'references':['https://www.youtube.com/watch?v=x','https://evil.example/x','https://www.facebook.com/p?access_token=1']}
    auto={'id':'geo:'+'c'*24,'name':{'ko':'찻집','en':'Tea','my':'Tea'},'lat':16.77,'lng':96.16,'auto_located':True}
    r=c.post('/trips',json={'places':[place,auto],'draft':{'days':1,'route':[{'day':1,'stop_ids':[PID,auto['id']]}]}})
    assert r.status_code==200,r.text
    created=r.json();assert created['contains_personal_data'] is False and len(created['id'])>=20
    shared=c.get('/trips/'+created['id']).json()
    assert shared['places'][0]['references']==['https://www.youtube.com/watch?v=x'] and shared['places'][1]['auto_located'] is True
    assert shared['draft']['route'][0]['stop_ids']==[PID,auto['id']]
    assert c.post('/trips',json={'places':[place,place]}).status_code==422
    assert c.post('/trips',json={'places':[place],'draft':{'days':1,'route':[{'day':1,'stop_ids':['other']}]}}).status_code==422
    assert c.post('/trips',json={'places':[{**place,'email':'a@b.c'}]}).status_code==200
    assert 'email' not in json.dumps(c.get('/trips/'+c.post('/trips',json={'places':[{**place,'email':'a@b.c'}]}).json()['id']).json())
    assert c.get('/trips/does-not-exist-anywhere').status_code==404
    with Session(engine) as s:
        s.add(SharedTrip(id='expired-shared-trip-id',payload='{}',expires=int(time.time())-1));s.commit()
    assert c.get('/trips/expired-shared-trip-id').status_code==404

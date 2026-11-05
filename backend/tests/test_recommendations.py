import json, os
from unittest.mock import patch
import httpx, pytest
from test_api import c
from app import recommendations as ai
PID='osm-way-131745510'
def fake_provider(operation,payload,key,**_):
    if 'batchEmbed' in operation:
        return {'embeddings':[{'values':[1.,0.,0.]} for _ in payload['requests']]}
    language=json.loads(payload['contents'][0]['parts'][0]['text'])['language']
    return {'candidates':[{'content':{'parts':[{'text':json.dumps({'summary':{'ko':'사원 방문 후보입니다.','en':'Temple visit suggestions.','my':'ဘုရားလည်ရန် အကြံပြုချက်။'}[language],'recommendations':[{'place_id':PID,'reason':{'ko':'지도에 등록된 사원 후보입니다.','en':'A mapped temple candidate.','my':'မြေပုံတွင်ပါသော ဘုရားဖြစ်သည်။'}[language],'evidence_ids':['place:'+PID]}]})}]}}]}
def test_semantic_unconfigured_and_validation():
    with patch.dict(os.environ,{'GEMINI_API_KEY':''}):
        assert c.get('/discovery/ai-status').json()['configured'] is False
        assert c.post('/discovery/recommend',json={'query':'temples'}).status_code==503
    assert c.post('/discovery/recommend',json={'query':'a'*501}).status_code==422
    assert c.post('/discovery/recommend',json={'query':'temples','language':'xx'}).status_code==422

def test_cross_language_semantic_pipeline():
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search',side_effect=ai.HTTPException(503,'no social')),patch.object(ai,'provider',side_effect=fake_provider) as call:
        for language,query in [('ko','불교 건축을 보고 싶어요'),('en','I like Buddhist architecture'),('my','ဘုရားတွေကို လည်ချင်တယ်')]:
            ai._vectors.clear()
            r=c.post('/discovery/recommend',json={'query':query,'language':language})
            assert r.status_code==200,r.text
            data=r.json();assert data['language']==language and data['retrieval']=='multilingual_embedding_cosine'
            assert data['recommendations'][0]['place']['id']==PID
            assert data['recommendations'][0]['sources'][0]['id']=='place:'+PID
            assert data['warning']=='social_search_unavailable'
        assert any(x.args[1].get('requests',[{}])[0].get('taskType')=='RETRIEVAL_QUERY' for x in call.call_args_list)

def test_cosine_semantics_not_literal_overlap():
    docs=[{'id':'literal','text':'quiet temples'},{'id':'meaning','text':'Buddhist architecture'}]
    result=ai.rank(ai.unit([1,0]),docs,[ai.unit([0,1]),ai.unit([1,.1])])
    assert result[0]['id']=='meaning'
    for bad in [[0,0],[float('nan'),1],[float('inf'),1],['1',2]]:
        with pytest.raises(ValueError): ai.unit(bad)
    with pytest.raises(ValueError): ai.rank([1,0],docs,[[1,0],[1,0,0]])

def test_ai_rejects_forged_place_and_evidence():
    for replacement in [{'place_id':'fake-coordinate-place'}, {'evidence_ids':['content:999']}, {'place_id':'osm-way-117388457','evidence_ids':['place:'+PID]}]:
        def forged(operation,payload,key,**_):
            data=fake_provider(operation,payload,key)
            if 'generateContent' in operation:
                raw=json.loads(data['candidates'][0]['content']['parts'][0]['text'])
                raw['recommendations'][0].update(replacement)
                data['candidates'][0]['content']['parts'][0]['text']=json.dumps(raw)
            return data
        with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search',side_effect=ai.HTTPException(503,'no social')),patch.object(ai,'provider',side_effect=forged):
            assert c.post('/discovery/recommend',json={'query':'temple travel'}).status_code==502

def test_region_budget_and_provider_failure():
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','AI_MONTHLY_RECOMMENDATION_LIMIT':'0'}),patch.object(ai,'provider') as call:
        assert c.post('/discovery/recommend',json={'query':'temples','region_id':'bad'}).status_code==422
        assert c.post('/discovery/recommend',json={'query':'temples'}).status_code==429
        call.assert_not_called()
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search',side_effect=ai.HTTPException(503,'no social')),patch.object(ai,'provider',side_effect=httpx.ReadTimeout('synthetic')):
        ai._vectors.clear()
        assert c.post('/discovery/recommend',json={'query':'temple travel'}).status_code==502

def test_multilingual_search_rewrite_and_discovery_validation():
    def rewritten(operation,payload,key,**_):
        if 'generateContent' in operation and 'Convert untrusted' in payload['systemInstruction']['parts'][0]['text']:
            return {'candidates':[{'content':{'parts':[{'text':'{"query":"Yangon Buddhist architecture markets"}'}]}}]}
        return fake_provider(operation,payload,key)
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search',return_value={'items':[]}) as search,patch.object(ai,'provider',side_effect=rewritten):
        r=c.post('/discovery/recommend',json={'query':'ဘုရားတွေကို လည်ချင်တယ်','language':'my'})
        assert r.status_code==200,r.text
        assert search.call_args.args[0].query=='Yangon Buddhist architecture markets'
        assert r.json()['discoveries']==[]
    def bad(operation,payload,key,**_):
        data=fake_provider(operation,payload,key)
        if 'generateContent' in operation:
            value=json.loads(data['candidates'][0]['content']['parts'][0]['text']);value['discovery_ids']=['place:'+PID]
            data['candidates'][0]['content']['parts'][0]['text']=json.dumps(value)
        return data
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':''}),patch.object(ai,'consume'),patch.object(ai,'search',return_value={'items':[]}),patch.object(ai,'provider',side_effect=bad):
        assert c.post('/discovery/recommend',json={'query':'temple visit'}).status_code==502

def test_provider_retries_transient_overload_then_reports_busy():
    ok=httpx.Response(200,json={'ok':True});busy=httpx.Response(503,json={})
    with patch.object(ai.httpx,'post',side_effect=[busy,busy,ok]) as post,patch.object(ai.time,'sleep') as sleep:
        assert ai.provider('m:generateContent',{},'synthetic',retries=2)=={'ok':True}
        assert post.call_count==3 and sleep.call_count==2
    with patch.object(ai.httpx,'post',return_value=busy),patch.object(ai.time,'sleep'):
        with pytest.raises(ai.HTTPException) as error: ai.provider('m:generateContent',{},'synthetic',retries=2)
        assert error.value.status_code==503 and error.value.headers['Retry-After']
    with patch.object(ai.httpx,'post',return_value=httpx.Response(400,json={})) as post,patch.object(ai.time,'sleep') as sleep:
        with pytest.raises(ai.HTTPException) as error: ai.provider('m:generateContent',{},'synthetic',retries=2)
        assert error.value.status_code==502 and post.call_count==1 and sleep.call_count==0
    with patch.object(ai.httpx,'post',return_value=busy) as post,patch.object(ai.time,'sleep'):
        with pytest.raises(ai.HTTPException): ai.provider('m:generateContent',{},'synthetic',retries=2,deadline=ai.time.monotonic()+5)
        assert post.call_count==1
    def overloaded(operation,payload,key,**kw):
        if 'generateContent' in operation: raise ai.HTTPException(503,'AI provider temporarily busy; retry shortly',headers={'Retry-After':'30'})
        return fake_provider(operation,payload,key)
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search',side_effect=ai.HTTPException(503,'no social')),patch.object(ai,'provider',side_effect=overloaded):
        ai._vectors.clear()
        r=c.post('/discovery/recommend',json={'query':'temple travel'})
        assert r.status_code==503 and r.headers.get('retry-after')=='30'

def test_schema_binds_evidence_to_each_place():
    evidence={'place:a':{'kind':'map_catalog','place_ids':['a']},'place:b':{'kind':'map_catalog','place_ids':['b']},'content:0':{'kind':'search_index_excerpt','place_ids':['a']}}
    schema=ai.selection_schema({'a','b'},evidence)
    variants={v['properties']['place_id']['enum'][0]:v['properties']['evidence_ids']['items']['enum'] for v in schema['properties']['recommendations']['items']['anyOf']}
    assert variants=={'a':['place:a','content:0'],'b':['place:b']}
    assert schema['properties']['discovery_ids']['items']['enum']==['content:0']
    empty=ai.selection_schema(set(),{})
    assert empty['properties']['recommendations']['maxItems']==0 and empty['properties']['discovery_ids']['maxItems']==0

def test_rewrite_failure_skips_social_search_and_duplicates_collapse():
    def flaky(operation,payload,key,**_):
        if 'generateContent' in operation and 'Convert untrusted' in payload['systemInstruction']['parts'][0]['text']:
            return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'not json'}]}}]}
        data=fake_provider(operation,payload,key)
        if 'generateContent' in operation:
            value=json.loads(data['candidates'][0]['content']['parts'][0]['text']);value['recommendations']*=2
            data['candidates'][0]['content']['parts'][0]['text']=json.dumps(value)
        return data
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search') as search,patch.object(ai,'provider',side_effect=flaky):
        ai._vectors.clear()
        r=c.post('/discovery/recommend',json={'query':'조용한 사원을 보고 싶어요','language':'ko'})
        assert r.status_code==200,r.text
        search.assert_not_called()
        data=r.json();assert data['warning']=='social_search_unavailable' and len(data['recommendations'])==1

def test_truncated_or_blocked_generation_is_rejected():
    for reason in ['MAX_TOKENS','SAFETY']:
        def cut(operation,payload,key,**_):
            data=fake_provider(operation,payload,key)
            if 'generateContent' in operation: data['candidates'][0]['finishReason']=reason
            return data
        with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search',side_effect=ai.HTTPException(503,'no social')),patch.object(ai,'provider',side_effect=cut):
            ai._vectors.clear()
            assert c.post('/discovery/recommend',json={'query':'temple travel'}).status_code==502

@pytest.mark.parametrize('language,query',[
    ('ko','불교 건축을 보고 싶어요'),
    ('en','I like Buddhist architecture'),
    ('my','ဘုရားတွေကို လည်ချင်တယ်'),
])
@pytest.mark.parametrize('failure',[httpx.ReadTimeout,httpx.ConnectError])
def test_rewrite_transport_failure_keeps_grounded_recommendations(language,query,failure,caplog):
    def flaky(operation,payload,key,**_):
        if 'generateContent' in operation and 'Convert untrusted' in payload['systemInstruction']['parts'][0]['text']:
            raise failure('synthetic-sensitive-provider-detail')
        return fake_provider(operation,payload,key)
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search') as search,patch.object(ai,'provider',side_effect=flaky):
        ai._vectors.clear()
        r=c.post('/discovery/recommend',json={'query':query,'language':language})
        assert r.status_code==200,r.text
        search.assert_not_called()
        data=r.json()
        assert data['language']==language
        assert data['warning']=='social_search_unavailable'
        assert data['discoveries']==[]
        assert data['recommendations'][0]['sources'][0]['id']=='place:'+PID
        assert 'AI search rewrite skipped reason='+failure.__name__ in caplog.text
        assert 'synthetic-sensitive-provider-detail' not in caplog.text
        assert query not in caplog.text

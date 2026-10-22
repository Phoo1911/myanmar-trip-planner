import json, os
from unittest.mock import patch
import httpx, pytest
from test_api import c
from app import recommendations as ai
PID='osm-way-131745510'
def fake_provider(operation,payload,key):
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
        def forged(operation,payload,key):
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
    def rewritten(operation,payload,key):
        if 'generateContent' in operation and 'Convert untrusted' in payload['systemInstruction']['parts'][0]['text']:
            return {'candidates':[{'content':{'parts':[{'text':'{"query":"Yangon Buddhist architecture markets"}'}]}}]}
        return fake_provider(operation,payload,key)
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':'synthetic'}),patch.object(ai,'consume'),patch.object(ai,'search',return_value={'items':[]}) as search,patch.object(ai,'provider',side_effect=rewritten):
        r=c.post('/discovery/recommend',json={'query':'ဘုရားတွေကို လည်ချင်တယ်','language':'my'})
        assert r.status_code==200,r.text
        assert search.call_args.args[0].query=='Yangon Buddhist architecture markets'
        assert r.json()['discoveries']==[]
    def bad(operation,payload,key):
        data=fake_provider(operation,payload,key)
        if 'generateContent' in operation:
            value=json.loads(data['candidates'][0]['content']['parts'][0]['text']);value['discovery_ids']=['place:'+PID]
            data['candidates'][0]['content']['parts'][0]['text']=json.dumps(value)
        return data
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic','TAVILY_API_KEY':''}),patch.object(ai,'consume'),patch.object(ai,'search',return_value={'items':[]}),patch.object(ai,'provider',side_effect=bad):
        assert c.post('/discovery/recommend',json={'query':'temple visit'}).status_code==502

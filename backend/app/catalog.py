"""Attributed, dated OSM snapshot; no public-provider call on visitor requests."""
import json
from pathlib import Path


def snapshot():
    return json.loads((Path(__file__).parent/'data'/'places.json').read_text())


def catalog_places(q='', category='', place_id=''):
    output=[]
    for record in snapshot()['places']:
        if category and record['category']!=category:continue
        if place_id and record['place_id']!=place_id:continue
        if q.casefold() not in (' '.join(record['name'].values())+' '+record['place_id']).casefold():continue
        data={**record}
        data['evidence']={'id':data['id'],'title':data['name']['en'],'url':data['source'],'place_id':data['place_id'],'views':None,'likes':None,'score':None,'published_at':None,'collected_at':data['checked_at'],'evidence_kind':'map_snapshot'}
        output.append(data)
    return output

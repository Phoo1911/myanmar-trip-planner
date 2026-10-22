"""Import capital city centres only; never promote all gazetteer entries as attractions."""
import zipfile,json,io,hashlib,httpx
from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parents[1]
response=httpx.get('https://download.geonames.org/export/dump/MM.zip',timeout=60);response.raise_for_status()
rows=[x.split('\t') for x in zipfile.ZipFile(io.BytesIO(response.content)).read('MM.txt').decode().splitlines()]
regions={f[10]:{'id':'MM.'+f[10],'name':f[1],'source':'https://www.geonames.org/'+f[0]+'/'} for f in rows if f[7]=='ADM1'}
now=datetime.now(timezone.utc).isoformat();cities=[]
for f in rows:
 if f[7] not in ['PPLA','PPLC']:continue
 names={'ko':next((a for a in f[3].split(',') if any('\uac00'<=c<='\ud7a3' for c in a)),f[1]),'en':f[1],'my':next((a for a in f[3].split(',') if any('\u1000'<=c<='\u109f' for c in a)),f[1])}
 cities.append({'id':'gn-'+f[0],'name':names,'aliases':list(dict.fromkeys([f[1],f[2],*f[3].split(',')])), 'place_id':'yangon' if f[1]=='Yangon' else 'city-'+f[0], 'region_id':'MM.'+f[10], 'region_name':regions[f[10]]['name'],'category':'city','lat':float(f[4]),'lng':float(f[5]),'source':'https://www.geonames.org/'+f[0]+'/', 'source_kind':'geonames','location_verified':False,'checked_at':now,'source_modified_at':f[18], 'price':None,'availability':None,'mode':'request_only','coordinate_scope':'city_centre'})
(r/'backend/app/data/national-cities.json').write_text(json.dumps({'source_sha256':hashlib.sha256(response.content).hexdigest(),'attribution':'GeoNames','license':'https://creativecommons.org/licenses/by/4.0/','source':'https://download.geonames.org/export/dump/MM.zip','collected_at':now,'regions':list(regions.values()),'places':cities},ensure_ascii=False,indent=2)+'\n')

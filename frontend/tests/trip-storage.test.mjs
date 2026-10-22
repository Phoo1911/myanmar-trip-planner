import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const source=readFileSync(new URL('../app/trip-storage.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const {parsePlaces,parseDraft,signature}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const place={id:'fixture-one',name:{ko:'검증 장소',en:'Fixture place',my:'စမ်းသပ်နေရာ'},lat:16.8,lng:96.15};
const draft=(cart=[place])=>({version:1,signature:signature(cart,2),days:2,savedAt:'2026-10-22T12:00:00Z',route:{days:[{day:1,stops:cart},{day:2,stops:[]}]}});
test('public place allowlist strips credentials and rejects malformed storage',()=>{
 assert.deepEqual(parsePlaces(JSON.stringify([{...place,token:'never-persist'}])),[place]);
 for(const value of ['{','null','{}',JSON.stringify([place,place]),JSON.stringify([{...place,lat:0}]),JSON.stringify([{...place,name:{en:'only'}}]),' '.repeat(40001)])assert.deepEqual(parsePlaces(value),[]);
});
test('saved route round-trip; cart and days changes cannot restore stale route',()=>{
 assert.equal(parseDraft(JSON.stringify(draft()),[place]).route.days[0].stops[0].id,place.id);
 assert.equal(parseDraft(JSON.stringify(draft()),[]),null);
 assert.equal(parseDraft(JSON.stringify({...draft(),days:3}),[place]),null);
 assert.equal(parseDraft(JSON.stringify({...draft(),version:2}),[place]),null);
});
test('tampered or incomplete routes cannot inject stops or omit selected places',()=>{
 for(const route of [{days:[{day:1,stops:[]},{day:2,stops:[]}]},{days:[{day:1,stops:[{id:'other'}]},{day:2,stops:[]}]},{days:[{day:1,stops:[place]},{day:2,stops:[place]}]}])assert.equal(parseDraft(JSON.stringify({...draft(),route}),[place]),null);
 assert.equal(parseDraft('{',[place]),null);
});

test('content references and city scope survive restore; unsafe references are stripped',()=>{
 const result=parsePlaces(JSON.stringify([{...place,coordinate_scope:'city_centre',references:['https://www.facebook.com/example/posts/1','javascript:alert(1)','https://evil.test/a','https://www.facebook.com/posts/2?access_token=unsafe']}]))[0];
 assert.equal(result.coordinate_scope,'city_centre');
 assert.deepEqual(result.references,['https://www.facebook.com/example/posts/1']);
});

test("AI map evidence survives device storage without allowing arbitrary hosts",()=>{
 const p={id:"evidence",name:{ko:"장소",en:"Place",my:"နေရာ"},lat:16,lng:96,references:["https://www.openstreetmap.org/way/1","https://www.geonames.org/1298824/","https://evil.test/place"]};
 assert.deepEqual(parsePlaces(JSON.stringify([p]))[0].references,p.references.slice(0,2));
});
test('automatically located places keep only a strict true marker',()=>{
 const auto={...place,id:'geo:'+'a'.repeat(24),auto_located:true};
 assert.deepEqual(parsePlaces(JSON.stringify([auto])),[auto]);
 assert.deepEqual(parsePlaces(JSON.stringify([{...auto,auto_located:'yes'}])),[{...place,id:auto.id}]);
});

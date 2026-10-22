"use client";
import {useEffect,useRef,useState} from 'react';
import type {Map as LeafletMap,LayerGroup} from 'leaflet';
type Place={id:string;lat:number;lng:number;name:Record<string,string>};
export default function Map({places,selectedId,onSelect,lang='en',labels}:{places:Place[];selectedId?:string;onSelect?:(id:string)=>void;lang?:string;labels?:Record<string,string>}){
 const el=useRef<HTMLDivElement>(null),map=useRef<LeafletMap|null>(null),markers=useRef<LayerGroup|null>(null),select=useRef(onSelect);
 const[ready,READY]=useState(false),[tileError,ERROR]=useState(false);select.current=onSelect;
 useEffect(()=>{let alive=true;let observer:ResizeObserver|undefined;
 import('leaflet').then(L=>{if(!alive||!el.current)return;const instance=L.map(el.current,{scrollWheelZoom:false}).setView([19.5,95.7],6);map.current=instance;markers.current=L.layerGroup().addTo(instance);
 L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',maxZoom:18}).on('tileerror',()=>ERROR(true)).on('tileload',()=>ERROR(false)).addTo(instance);
 observer=new ResizeObserver(()=>instance.invalidateSize());observer.observe(el.current);READY(true);
 }).catch(()=>ERROR(true));return()=>{alive=false;observer?.disconnect();map.current?.remove();map.current=null;markers.current=null}
 },[]);
 useEffect(()=>{if(!ready||!map.current||!markers.current)return;let active=true;
 import('leaflet').then(L=>{if(!active||!map.current||!markers.current)return;markers.current.clearLayers();places.forEach(p=>{const label=document.createElement('span');label.textContent=labels?.[p.id]||p.name[lang]||p.name.en;L.circleMarker([p.lat,p.lng],{radius:p.id===selectedId?12:8,color:p.id===selectedId?'#a65a08':'#195c48',fillOpacity:.8}).addTo(markers.current!).bindTooltip(label,{permanent:!!labels?.[p.id],direction:'top'}).on('click',()=>select.current?.(p.id))});
 const chosen=places.find(p=>p.id===selectedId);if(chosen)map.current.setView([chosen.lat,chosen.lng],13);else if(places.length)map.current.fitBounds(L.latLngBounds(places.map(p=>[p.lat,p.lng])),{padding:[40,40],maxZoom:13});
 });return()=>{active=false}
 },[places,selectedId,ready,lang,labels]);
 return <><div ref={el} className="h-[480px] rounded-2xl" aria-label="Destination map"/>{tileError&&<p role="status" className="map-tile-error">Map tiles unavailable · 목록은 계속 사용할 수 있습니다 / Place list remains available.</p>}</>
}

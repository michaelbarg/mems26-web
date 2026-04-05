"use client";
import { useEffect, useRef, useCallback } from "react";
export interface CandleVP { ts:number;o?:number;h?:number;l?:number;c?:number;open?:number;high?:number;low?:number;close?:number;volume?:number;buy?:number;sell?:number;[k:string]:any; }
interface Props { chart:any; candles:CandleVP[]; tickSize?:number; profileWidth?:number; }
function _h(c:CandleVP){return c.h??c.high??0;}function _l(c:CandleVP){return c.l??c.low??0;}function _c(c:CandleVP){return c.c??c.close??0;}function _v(c:CandleVP){return (c.volume??((c.buy||0)+(c.sell||0)))||100;}
function calcDelta(c:CandleVP){if(c.buy!==undefined&&c.sell!==undefined&&c.buy+c.sell>0)return{buy:c.buy,sell:c.sell};const v=_v(c);const s=_h(c)-_l(c);if(s===0)return{buy:v/2,sell:v/2};return{buy:v*(_c(c)-_l(c))/s,sell:v*(_h(c)-_c(c))/s};}
export function VolumeProfile({chart,candles,tickSize=0.25,profileWidth=100}:Props){
const canvasRef=useRef<HTMLCanvasElement>(null);
const draw=useCallback(()=>{
const canvas=canvasRef.current;if(!canvas||!chart||!candles.length)return;
const container=canvas.parentElement;if(!container)return;
canvas.width=container.clientWidth*devicePixelRatio;canvas.height=container.clientHeight*devicePixelRatio;
canvas.style.width=container.clientWidth+"px";canvas.style.height=container.clientHeight+"px";
const ctx=canvas.getContext("2d");if(!ctx)return;ctx.scale(devicePixelRatio,devicePixelRatio);ctx.clearRect(0,0,container.clientWidth,container.clientHeight);
const W=container.clientWidth,H=container.clientHeight;
const priceMap=new Map<number,{buy:number;sell:number}>();
const round=(p:number)=>Math.round(p/tickSize)*tickSize;
for(const c of candles){const{buy,sell}=calcDelta(c);const hi=_h(c),lo=_l(c);const levels=Math.max(1,Math.round((hi-lo)/tickSize));const bpl=buy/levels,spl=sell/levels;for(let i=0;i<=levels;i++){const price=round(lo+i*tickSize);const ex=priceMap.get(price)??{buy:0,sell:0};ex.buy+=bpl;ex.sell+=spl;priceMap.set(price,ex);}}
if(!priceMap.size)return;
let maxVol=0,pocPrice=0;priceMap.forEach((v,p)=>{const t=v.buy+v.sell;if(t>maxVol){maxVol=t;pocPrice=p;}});
const p2y=(price:number):number|null=>{try{return chart.priceScale("right").priceToCoordinate(price);}catch{return null;}};
const scaleW=72,xRight=W-scaleW-2;
const barH=Math.max(2,Math.abs((p2y(0)??0)-(p2y(tickSize)??tickSize))-1);
priceMap.forEach((vol,price)=>{
const y=p2y(price);if(y===null||y<0||y>H)return;
const total=vol.buy+vol.sell;const tw=(total/maxVol)*profileWidth;const bw=(vol.buy/total)*tw;const sw=tw-bw;
const yTop=y-barH/2;
ctx.fillStyle="rgba(0,188,212,0.7)";ctx.fillRect(xRight-bw,yTop,bw,barH);
ctx.fillStyle="rgba(233,30,99,0.7)";ctx.fillRect(xRight-bw-sw,yTop,sw,barH);
if(price===pocPrice){ctx.strokeStyle="rgba(255,235,59,0.9)";ctx.lineWidth=1.5;ctx.setLineDash([3,2]);ctx.beginPath();ctx.moveTo(xRight-profileWidth,y);ctx.lineTo(xRight,y);ctx.stroke();ctx.setLineDash([]);}
});
ctx.fillStyle="rgba(0,188,212,0.8)";ctx.font="bold 9px monospace";ctx.textAlign="right";ctx.fillText("■BUY",xRight-50,12);
ctx.fillStyle="rgba(233,30,99,0.8)";ctx.fillText("■SELL",xRight-2,12);
},[chart,candles,tickSize,profileWidth]);
useEffect(()=>{if(!chart)return;draw();const u=chart.timeScale().subscribeVisibleTimeRangeChange(draw);const ro=new ResizeObserver(draw);const c=canvasRef.current?.parentElement;if(c)ro.observe(c);const iv=setInterval(draw,3000);return()=>{u();ro.disconnect();clearInterval(iv);};},[chart,draw]);
return <canvas ref={canvasRef} style={{position:"absolute",top:0,left:0,width:"100%",height:"100%",pointerEvents:"none",zIndex:5}} />;
}

const canvas=document.getElementById("watchCanvas");
const ctx=canvas.getContext("2d",{alpha:false});
const loader=document.getElementById("loader");
const bar=document.getElementById("loaderBar");
const frameCount=window.FRAME_COUNT;
const ext=window.FRAME_EXT;
const images=new Array(frameCount);
let loaded=0, current=0, target=0, raf=0;

function resize(){
  const dpr=Math.min(window.devicePixelRatio||1,2);
  canvas.width=Math.round(innerWidth*dpr);
  canvas.height=Math.round(innerHeight*dpr);
  canvas.style.width=innerWidth+"px";
  canvas.style.height=innerHeight+"px";
  ctx.setTransform(dpr,0,0,dpr,0,0);
  drawFrame(current);
}
function loadImage(i){
  return new Promise(resolve=>{
    const img=new Image();
    img.decoding="async";
    img.src=`frames/frame_${String(i+1).padStart(4,"0")}${ext}`;
    img.onload=()=>{images[i]=img;loaded++;bar.style.width=(loaded/frameCount*100)+"%";resolve(img)};
    img.onerror=()=>resolve(null);
  });
}
async function preload(){
  // First frame immediately, then load the rest in parallel.
  await loadImage(0);
  resize();
  const jobs=[];
  for(let i=1;i<frameCount;i++) jobs.push(loadImage(i));
  await Promise.all(jobs);
  loader.classList.add("done");
  requestAnimationFrame(animate);
}
function drawFrame(index){
  const img=images[Math.max(0,Math.min(frameCount-1,Math.round(index)))];
  if(!img)return;
  const cw=innerWidth,ch=innerHeight;
  ctx.fillStyle="#050504";ctx.fillRect(0,0,cw,ch);
  const scale=Math.min(cw/img.naturalWidth,ch/img.naturalHeight);
  const w=img.naturalWidth*scale,h=img.naturalHeight*scale;
  const x=(cw-w)/2,y=(ch-h)/2;
  ctx.drawImage(img,x,y,w,h);
}
function animate(){
  target=(window.scrollY/(Math.max(1,document.documentElement.scrollHeight-innerHeight)))*(frameCount-1);
  current+=(target-current)*0.13;
  if(Math.abs(target-current)<.01)current=target;
  drawFrame(current);
  raf=requestAnimationFrame(animate);
}
window.addEventListener("resize",resize,{passive:true});
preload();

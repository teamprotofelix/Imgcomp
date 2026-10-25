export const IMAGE=/\.(jpe?g|png|webp|bmp|gif|avif|heic|heif|tiff?)$/i;
export const VIDEO=/\.(mp4|webm|mov|m4v|mkv|avi|wmv|flv|mpe?g|3gp)$/i;
export const classify=name=>IMAGE.test(name)?'image':VIDEO.test(name)?'video':null;
export const unchanged=(r,f)=>r.size===f.size&&r.modified===f.lastModified;
export function keepCompare(policy){return(a,b)=>{let d=0;if(policy==='newest')d=b.modified-a.modified;else if(policy==='largest')d=b.size-a.size;else if(policy==='shortest')d=a.path.length-b.path.length;else d=a.modified-b.modified;return d||a.path.localeCompare(b.path);};}
export function distance(a,b){if(a.length!==b.length) return Infinity;let n=0;for(let i=0;i<a.length;i++)if(a[i]!==b[i])n++;return n;}
export function visualMatch(a,b,threshold,tolerance){if(!a.visual||!b.visual||a.kind!==b.kind)return false;if(a.digest===b.digest)return false;if(Math.abs(a.visual.aspect/b.visual.aspect-1)>.12)return false;if(a.kind==='video'&&Math.abs(a.visual.duration-b.visual.duration)>Math.max(2,Math.max(a.visual.duration,b.visual.duration)*tolerance/100))return false;const x=a.visual.frames,y=b.visual.frames;if(x.length!==y.length)return false;return x.every((f,i)=>f.spread>8&&y[i].spread>8&&distance(f.bits,y[i].bits)<=threshold&&f.color.reduce((s,v,k)=>s+Math.abs(v-y[i].color[k]),0)<100);}
// Anchor groups avoid transitive A≈B≈C being presented as A≈C.
export async function makeGroups(records,{threshold=6,tolerance=5,policy='oldest',check=()=>{}}={}){
 const groups=[],buckets=new Map(),sort=keepCompare(policy);for(const r of records){if(!r.digest)continue;const key=r.kind+':'+r.size+':'+r.digest;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(r);}for(const files of buckets.values())if(files.length>1)groups.push({type:'exact',files:[...files].sort(sort)});
 const pool=records.filter(r=>r.visual).sort(sort),claimed=new Set();let comparisons=0;
 for(let i=0;i<pool.length;i++){check();const a=pool[i];if(claimed.has(a.id))continue;const files=[a];for(let j=i+1;j<pool.length;j++){if(++comparisons%2000===0){await new Promise(r=>setTimeout(r,0));check();}const b=pool[j];if(!claimed.has(b.id)&&visualMatch(a,b,threshold,tolerance))files.push(b);}if(files.length>1){files.forEach(r=>claimed.add(r.id));groups.push({type:'similar',files});}}
 return groups.map((g,i)=>({...g,id:i,keep:g.files[0].id,threshold,tolerance}));
}
export function selectionValid(groups,selected){return groups.every(g=>g.files.some(r=>!selected.has(r.id)));}
export function autoSelect(groups){const s=new Set();for(const g of groups)if(g.type==='exact')for(const r of g.files)if(r.id!==g.keep)s.add(r.id);for(const g of groups){s.delete(g.keep);if(g.type==='similar')for(const r of g.files)if(!matchesKeep(g,r))s.delete(r.id);if(g.files.every(r=>s.has(r.id)))s.delete(g.files[0].id);}return s;}
export function deletionPlan(groups,selected){if(!selectionValid(groups,selected))throw Error('각 그룹에는 최소 한 파일을 남겨야 합니다.');const map=new Map();for(const g of groups)for(const r of g.files)if(selected.has(r.id))map.set(r.id,r);if(groups.some(g=>selected.has(g.keep)))throw Error('남길 원본은 삭제할 수 없습니다.');if(map.size!==selected.size)throw Error('검색 결과에 없는 선택입니다.');for(const r of map.values())if(!r.handle||!r.parent)throw Error('읽기 전용 모드에서는 삭제할 수 없습니다.');return [...map.values()];}
// Injected read/remove helpers keep all safety checks independently testable.
export async function executeDeletion({groups,selected,verify,remove,check=()=>{},onResult=()=>{}}){
 const planned=new Set(selected),targets=deletionPlan(groups,planned),results=[];
 for(const target of targets){
  check();
  try{
   await verify(target);
   for(const g of groups.filter(g=>g.files.some(r=>r.id===target.id))){
    const keep=g.files.find(r=>r.id===g.keep);
    if(!keep||planned.has(keep.id))throw Error('지정한 보존 원본이 없습니다. 다시 분석하거나 원본을 재지정하세요.');
    try{await verify(keep);}
    catch(e){
     if(e.name==='AbortError')throw e;
     throw Error('지정한 보존 원본 검증 실패. 다시 분석하거나 원본을 재지정하세요. '+e.message);
    }
   }
   check();await remove(target);
   const result={id:target.id,path:target.path,ok:true};results.push(result);onResult(result);
  }catch(e){
   if(e.name==='AbortError')throw e;
   const result={id:target.id,path:target.path,ok:false,error:e.message};results.push(result);onResult(result);
  }
 }
 return results;
}

// Compare directly with the designated keep, never infer transitive similarity.
export function matchesKeep(g,r){const keep=g.files.find(f=>f.id===g.keep);return !!keep&&(r.id===keep.id||r.digest===keep.digest||visualMatch(keep,r,g.threshold??6,g.tolerance??5));}
export function snapshotPlan(groups,selected){
 const targets=deletionPlan(groups,selected);
 for(const g of groups)if(g.type==='similar'&&g.files.some(r=>selected.has(r.id)&&!matchesKeep(g,r)))throw Error('지정 원본과 직접 유사하지 않은 선택입니다. 다시 비교하세요.');
 const copy=r=>Object.freeze({...r});
 return Object.freeze({groups:Object.freeze(groups.map(g=>Object.freeze({...g,files:Object.freeze(g.files.map(copy))}))),targets:Object.freeze(targets.map(copy)),ids:Object.freeze(targets.map(r=>r.id))});
}
export function planSignature(groups,selected){return JSON.stringify({ids:[...selected].sort((a,b)=>a-b),groups:groups.map(g=>({id:g.id,type:g.type,keep:g.keep,files:g.files.map(r=>[r.id,r.path,r.name,r.size,r.modified,r.digest])}))});}

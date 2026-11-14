'use strict';
// V1.1 extends the app. Photos only come from authenticated user uploads.
Object.assign(KM, {
 room:'\u1794\u1793\u17d2\u1791\u1794\u17cb',roomPlan:'\u1794\u17d2\u179b\u1784\u17cb\u1794\u1793\u17d2\u1791\u1794\u17cb',
 back:'\u178f\u17d2\u179a\u17a1\u1794\u17cb',next:'\u1794\u1793\u17d2\u1791\u17b6\u1794\u17cb',
 width:'\u1791\u1791\u17b9\u1784',height:'\u1780\u1798\u17d2\u1796\u179f\u17cb',depth:'\u1787\u1798\u17d2\u179a\u17c5',length:'\u1794\u178e\u17d2\u178f\u17c4\u1799',
 move:'\u1795\u17d2\u179b\u17b6\u179f\u17cb\u1791\u17b8',detail:'\u1796\u17d0\u178f\u17cc\u1798\u17b6\u1793\u179b\u1798\u17d2\u17a2\u17b7\u178f',
 realPhotos:'\u179a\u17bc\u1794\u1790\u178f\u1781\u17c4\u17a2\u17b6\u179c\u1796\u17b7\u178f',
 noPhoto:'\u1798\u17b7\u1793\u1791\u17b6\u1793\u17cb\u1798\u17b6\u1793\u179a\u17bc\u1794\u1790\u178f',
 editPlan:'\u1780\u17c2\u1794\u17d2\u179b\u1784\u17cb',savePlan:'\u179a\u1780\u17d2\u179f\u17b6\u1791\u17bb\u1780\u1794\u17d2\u179b\u1784\u17cb',
 box:'\u1794\u17d2\u179a\u17a2\u1794\u17cb',camera:'\u1790\u178f\u179a\u17bc\u1794',
 door:'\u1791\u17d2\u179c\u17b6\u179a',window:'\u1794\u1784\u17d2\u17a2\u17bd\u1785',
 split:'\u1794\u17c2\u1784\u1785\u17c2\u1780',position:'\u1791\u17b8\u178f\u17b6\u17c6\u1784',zoom:'\u1796\u1784\u17d2\u179a\u17b8\u1780\u179a\u17bc\u1794'
});
const plannerUI={view:'room',editing:false,step:1,draft:null,selected:0,query:'',category:'all',detailIds:[],detailIndex:0};
const clonePlan=()=>JSON.parse(JSON.stringify(state.bootstrap.planner));
const num=v=>Math.round(v*10)/10;
const plButton=(action,label,extra='',cls='btn btn-light')=>`<button type="button" class="${cls}" data-plan="${action}" ${extra}>${label}</button>`;
const kinds=['hanger','shelf','drawer','box'];
function roomPoints(r){return r.shape==='l'?[[0,0],[r.width,0],[r.width,r.depth-r.cut_depth],[r.width-r.cut_width,r.depth-r.cut_depth],[r.width-r.cut_width,r.depth],[0,r.depth]]:[[0,0],[r.width,0],[r.width,r.depth],[0,r.depth]];}
function roomMap(plan,editable=false,showWalls=false){
 const r=plan.room,w=plan.cabinet,points=roomPoints(r),scale=Math.min(480/r.width,350/r.depth),ox=68,oy=62;
 const P=([x,y])=>`${num(ox+x*scale)},${num(oy+y*scale)}`;
 const fw=w.rotation===90?w.depth:w.width,fd=w.rotation===90?w.width:w.depth;
 const openings=r.openings.map(o=>{const a=points[o.wall],b=points[(o.wall+1)%points.length];if(!a||!b)return '';const length=Math.hypot(b[0]-a[0],b[1]-a[1]);const at=d=>[a[0]+(b[0]-a[0])*d/length,a[1]+(b[1]-a[1])*d/length];const p=at(o.offset),q=at(o.offset+o.width);return `<line x1="${ox+p[0]*scale}" y1="${oy+p[1]*scale}" x2="${ox+q[0]*scale}" y2="${oy+q[1]*scale}" stroke="${o.kind==='door'?'#e3a85f':'#5aabd1'}" stroke-width="10"/><text x="${ox+(p[0]+q[0])/2*scale}" y="${oy+(p[1]+q[1])/2*scale-13}" class="opening-label">${t(o.kind)}</text>`;}).join('');
 const walls=(editable||showWalls)?points.map((a,i)=>{const b=points[(i+1)%points.length];return `<text x="${ox+(a[0]+b[0])*scale/2}" y="${oy+(a[1]+b[1])*scale/2+22}" class="wall-label">${i+1}</text>`;}).join(''):'';
 return `<svg class="room-map" id="room-map" viewBox="0 0 620 470" role="img" aria-label="${e(t('roomPlan'))}" data-scale="${scale}"><defs><pattern id="floor-lines" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M0 32H32" stroke="#ede6dd" fill="none"/></pattern></defs><polygon points="${points.map(P).join(' ')}" fill="#faf7f2" stroke="#b5aa9c" stroke-width="9" stroke-linejoin="round"/><polygon points="${points.map(P).join(' ')}" fill="url(#floor-lines)"/>${openings}${walls}<path d="M${ox} 28H${ox+r.width*scale}" stroke="#84959b"/><text x="${ox+r.width*scale/2}" y="19" class="dimension-label">${num(r.width)} mm</text><text x="21" y="${oy+r.depth*scale/2}" transform="rotate(-90 21 ${oy+r.depth*scale/2})" class="dimension-label">${num(r.depth)} mm</text><g ${editable?'data-wardrobe-drag="true"':'data-plan="wardrobe" tabindex="0" role="button" aria-label="Open W01"'} class="map-cabinet" transform="translate(${ox+w.x*scale} ${oy+w.y*scale})"><rect width="${fw*scale}" height="${fd*scale}" rx="5" fill="#d9c8f5" stroke="#7753b5" stroke-width="3"/><path d="M${fw*scale/2} 3V${fd*scale-3}" stroke="#a28bbf"/><text x="${fw*scale/2}" y="${fd*scale/2}" text-anchor="middle" dominant-baseline="middle" class="cabinet-label">W01</text></g><text x="${ox+r.width*scale/2}" y="${oy+r.depth*scale+37}" class="dimension-label">2D / ${e(r.name)} / mm</text></svg>`;
}
function planCrumbs(){return `<div class="plan-crumbs">${plButton('room',t('roomPlan'))}<span>/</span>${plButton('wardrobe','W01')}<span>/</span><span>${plannerUI.view==='gallery'?e(state.bootstrap.compartments.find(c=>c.id===state.selectedCompartment)?.code||''):t('compartments')}</span></div>`;}
function frontMap(plan,editable=false){
 return `<div class="front-map" style="aspect-ratio:${plan.cabinet.width}/${plan.cabinet.height}" role="group" aria-label="W01 compartments">${plan.compartments.map((c,i)=>{const items=state.garments.filter(g=>g.compartment_id===c.id),photos=items.filter(g=>g.photo_filename).slice(0,3);return `<button type="button" class="front-cell ${editable&&plannerUI.selected===i?'active':''}" data-plan="${editable?'cell':'gallery'}" data-index="${i}" data-id="${c.id||''}" style="left:${c.x}%;top:${c.y}%;width:${c.w}%;height:${c.h}%" aria-label="${e(c.code)} ${items.length} items"><span class="cell-title">${e(c.code)}<b>${items.length}</b></span><div class="cell-photos">${photos.map(g=>`<img src="/media/${e(g.photo_filename)}" alt="${e(g.name)}" loading="lazy"/>`).join('')||`<span class="cell-kind">${svg(c.kind==='hanger'?'hanger':'box')}${t(c.kind)}</span>`}</div>${editable?`<small class="cell-size">${num(c.w*plan.cabinet.width/100)} &times; ${num(c.h*plan.cabinet.height/100)}</small>`:''}</button>`;}).join('')}</div>`;
}
const baseRenderLayout=renderLayout;
renderLayout=function(){
 const p=state.bootstrap.planner;if(!p)return baseRenderLayout();
 if(plannerUI.editing)return editorView();
 if(plannerUI.view==='gallery')return galleryView();
 const head=heading(t('roomPlan')+' / '+t('layout'),'Room / W01 / Compartment / Real photos');
 if(plannerUI.view==='room')return head+`<div class="plan-toolbar">${plButton('edit',svg('pencil')+t('editPlan'),'','btn btn-primary')}<span class="pill">1 ${t('room')} / 1 ${t('wardrobe')}</span></div><div class="plan-overview"><section class="surface room-surface"><div class="section-head"><h2 class="section-title">${e(p.room.name)}</h2><span class="pill">2D TOP VIEW</span></div>${roomMap(p)}</section><aside class="surface plan-summary"><h2>${e(state.bootstrap.wardrobe.name)}</h2><p class="subtext">${e(p.room.name)} / W01</p><div class="dimension-cards"><div>${t('width')}<strong>${num(p.cabinet.width)}</strong>mm</div><div>${t('height')}<strong>${num(p.cabinet.height)}</strong>mm</div><div>${t('depth')}<strong>${num(p.cabinet.depth)}</strong>mm</div></div><div class="plan-total"><strong>${state.bootstrap.total}</strong><span>${t('garments')}</span></div>${plButton('wardrobe',svg('cabinet')+t('compartments'),'','btn btn-primary')}<p class="soft-note">${t('clickHint')}</p></aside></div>`;
 return head+planCrumbs()+`<div class="plan-toolbar">${plButton('edit',svg('pencil')+t('editPlan'),'data-step="3"')}<span class="pill">W01 / ${p.compartments.length} ${t('compartments')}</span></div><div class="front-surface surface"><div class="section-head"><h2 class="section-title">${t('front')}</h2><span>${num(p.cabinet.width)} &times; ${num(p.cabinet.height)} mm</span></div>${frontMap(p)}<p class="soft-note">${t('clickHint')} / ${t('realPhotos')}</p></div>`;
};
function realPhoto(g){return g.photo_filename?`<img loading="lazy" src="/media/${e(g.photo_filename)}" alt="${e(g.name)}"/>`:`<div class="no-photo">${svg('shirt')}<span>${t('noPhoto')}</span></div>`;}
function galleryItems(){return state.garments.filter(g=>g.compartment_id===state.selectedCompartment).filter(g=>plannerUI.category==='all'||g.category===plannerUI.category).filter(g=>[g.name,g.color,g.tag_id].join(' ').toLowerCase().includes(plannerUI.query.toLowerCase()));}
function photoGrid(items){return items.length?`<div class="real-gallery">${items.map(g=>`<button class="photo-card" data-plan="detail" data-id="${g.id}"><div class="real-photo">${realPhoto(g)}</div><div class="photo-caption"><strong>${e(g.name)}</strong><span>${e(g.color||t(g.category))} &bull; ${e(g.size||'--')}</span></div></button>`).join('')}</div>`:`<div class="empty-state"><b>${t('emptyFilter')}</b>${plButton('add',svg('plus')+t('addHere'),'','btn btn-primary')}</div>`;}
function galleryView(){const c=state.bootstrap.compartments.find(c=>c.id===state.selectedCompartment);if(!c){plannerUI.view='wardrobe';return renderLayout();}const count=state.garments.filter(g=>g.compartment_id===c.id).length;return heading(t('compartment')+' '+e(c.code),t('realPhotos'))+planCrumbs()+`<div class="plan-toolbar"><span class="pill">W01 / ${e(c.code)} / ${count} ${t('garments')}</span>${plButton('add',svg('plus')+t('addHere'),'','btn btn-primary')}</div><p class="subtext">${e(c.label)}</p><div class="gallery-filters"><input class="field" id="gallery-search" type="search" placeholder="${t('search')}" value="${e(plannerUI.query)}" aria-label="Search compartment photos"/><select class="field" id="gallery-category" aria-label="Category"><option value="all">${t('allCategories')}</option>${categoryKeys.map(k=>`<option value="${k}" ${plannerUI.category===k?'selected':''}>${t(k)}</option>`).join('')}</select></div><div id="gallery-results">${photoGrid(galleryItems())}</div>`;}
function showDetail(id,ids){
 const g=state.garments.find(g=>g.id===Number(id));if(!g)return;
 if(ids)plannerUI.detailIds=ids;plannerUI.detailIndex=plannerUI.detailIds.indexOf(g.id);
 const n=plannerUI.detailIds.length,idx=plannerUI.detailIndex;
 modal(`<div class="modal-head"><h2>${t('detail')}</h2><button class="icon-button" data-action="close-modal" aria-label="Close">${svg('x')}</button></div><div class="detail-photo"><button type="button" class="image-zoom" data-plan="zoom" data-id="${g.id}" aria-label="${t('zoom')}">${realPhoto(g)}</button>${n>1?`<button class="photo-prev" data-plan="prev" aria-label="Previous garment">&#8249;</button><button class="photo-next" data-plan="next-photo" aria-label="Next garment">&#8250;</button><span class="photo-index">${idx+1} / ${n}</span>`:''}</div><h2 class="detail-name">${e(g.name)}</h2><dl class="detail-fields">${[[t('category'),t(g.category)],[t('color'),g.color||'--'],[t('size'),g.size||'--'],[t('count'),'1'],[t('position'),'W01 / '+(g.compartment_code||t('unassigned'))],[t('date'),formatDate(g.created_at)]].map(([k,v])=>`<div><dt>${k}</dt><dd>${e(v)}</dd></div>`).join('')}</dl>${g.notes?`<p class="detail-notes">${e(g.notes)}</p>`:''}<div class="detail-actions">${plButton('edit-item',svg('pencil')+t('edit'),`data-id="${g.id}"`)}${plButton('move-item',svg('pin')+t('move'),`data-id="${g.id}"`)}${plButton('remove-item',t('remove'),`data-id="${g.id}"`,'btn btn-danger')}</div>`);
 document.querySelector('.modal').classList.add('garment-detail');
}
function inputField(label,path,val,type='number'){return `<label class="planner-field"><span>${label}</span><input class="field" type="${type}" data-field="${path}" value="${e(val)}" ${type==='number'?'step="1" min="0"':'maxlength="100"'} required/></label>`;}
function selectField(label,path,val,options){return `<label class="planner-field"><span>${label}</span><select class="field" data-field="${path}">${options.map(([k,v])=>`<option value="${k}" ${String(k)===String(val)?'selected':''}>${v}</option>`).join('')}</select></label>`;}
function editorView(){
 const d=plannerUI.draft,r=d.room,w=d.cabinet,c=d.compartments[plannerUI.selected]||d.compartments[0];
 const steps=[t('room'),t('wardrobe'),t('compartments')];let fields='';
 if(plannerUI.step===1){fields=`${inputField(t('room')+' / Name','room.name',r.name,'text')}${selectField('Shape','room.shape',r.shape,[['rectangle','Rectangle / Square'],['l','L-shape']])}<div class="planner-pair">${inputField(t('width')+' (mm)','room.width',r.width)}${inputField(t('length')+' (mm)','room.depth',r.depth)}${inputField(t('height')+' (mm)','room.height',r.height)}</div>${r.shape==='l'?`<div class="planner-pair">${inputField('Cut-out width (mm)','room.cut_width',r.cut_width)}${inputField('Cut-out depth (mm)','room.cut_depth',r.cut_depth)}</div><p class="soft-note">L-shape: cut-out at bottom right.</p>`:''}<h3>${t('door')} / ${t('window')}</h3><div class="openings-list">${r.openings.map((o,i)=>`<div class="opening-row">${selectField('Type',`opening.${i}.kind`,o.kind,[['door',t('door')],['window',t('window')]])}${selectField('Wall',`opening.${i}.wall`,o.wall,roomPoints(r).map((_,j)=>[j,j+1]))}${inputField('Offset mm',`opening.${i}.offset`,o.offset)}${inputField('Width mm',`opening.${i}.width`,o.width)}${plButton('remove-opening','&times;',`data-index="${i}"`,'icon-button')}</div>`).join('')}</div>${plButton('add-opening',svg('plus')+t('door')+' / '+t('window'))}`;
 }else if(plannerUI.step===2){fields=`<p class="soft-note">W01 / ${t('wardrobe')}<br/>Drag the wardrobe on the plan, or enter X / Y in mm from the top-left corner.</p><div class="planner-pair">${inputField(t('width')+' (mm)','cabinet.width',w.width)}${inputField(t('height')+' (mm)','cabinet.height',w.height)}${inputField(t('depth')+' (mm)','cabinet.depth',w.depth)}${selectField('Rotation','cabinet.rotation',w.rotation,[[0,'0 degrees'],[90,'90 degrees']])}${inputField('X (mm)','cabinet.x',w.x)}${inputField('Y (mm)','cabinet.y',w.y)}</div>`;
 }else{fields=`<h3>${t('compartment')} ${e(c.code)}</h3><p class="soft-note">${t('clickHint')}<br/>X/Y: top-left. Sizes in mm. Split keeps existing clothes in the selected half.</p><div class="planner-pair">${inputField('Code','cell.code',c.code,'text')}${inputField(t('compartmentName'),'cell.label',c.label,'text')}${selectField(t('compartmentType'),'cell.kind',c.kind,kinds.map(k=>[k,t(k)]))}${inputField('X (mm)','cell.x',num(c.x*w.width/100))}${inputField('Y (mm)','cell.y',num(c.y*w.height/100))}${inputField(t('width')+' (mm)','cell.w',num(c.w*w.width/100))}${inputField(t('height')+' (mm)','cell.h',num(c.h*w.height/100))}</div><div class="split-actions">${plButton('split-v',t('split')+' |')}${plButton('split-h',t('split')+' &mdash;')}${plButton('remove-cell',t('remove'),'','btn btn-danger')}</div><p class="soft-note">${d.compartments.length} ${t('compartments')} / max 80</p>`;}
 return heading(t('editPlan'),'W01 / Room & wardrobe planner / V1.1')+`<div class="planner-steps">${steps.map((s,i)=>plButton('step',`<b>${i+1}</b> ${s}`,`data-step="${i+1}"`,plannerUI.step===i+1?'step active':'step')).join('')}</div><div class="planner-editor"><section class="surface editor-canvas"><div id="editor-preview">${plannerUI.step===3?frontMap(d,true):roomMap(d,plannerUI.step===2,true)}</div><div class="editor-warning" id="plan-warning" role="status"></div></section><section class="surface editor-fields">${fields}</section></div><div class="planner-footer">${plButton('cancel-edit',t('cancel'))}${plannerUI.step<3?plButton('step',t('next')+' &rarr;',`data-step="${plannerUI.step+1}"`,'btn btn-primary'):plButton('save',svg('check')+t('savePlan'),'','btn btn-primary')}</div>`;
}
function previewDraft(){const preview=document.getElementById('editor-preview');if(preview)preview.innerHTML=plannerUI.step===3?frontMap(plannerUI.draft,true):roomMap(plannerUI.draft,plannerUI.step===2,true);}
function beginEditor(step=1){plannerUI.draft=clonePlan();plannerUI.editing=true;plannerUI.step=step;plannerUI.selected=0;render();}
async function handlePlan(button){
 const action=button.dataset.plan;
 if(action==='room'||action==='wardrobe'){plannerUI.view=action;render();}
 else if(action==='edit')beginEditor(Number(button.dataset.step||1));
 else if(action==='step'){plannerUI.step=Number(button.dataset.step);render();}
 else if(action==='cancel-edit'){if(!confirm('Discard unsaved plan changes?'))return;plannerUI.editing=false;plannerUI.draft=null;render();}
 else if(action==='save'){button.disabled=true;try{await api('/api/planner',jsonOptions('PUT',plannerUI.draft));plannerUI.editing=false;plannerUI.view='wardrobe';await refresh();flash(t('saved'));}finally{button.disabled=false;}}
 else if(action==='cell'){plannerUI.selected=Number(button.dataset.index);render();}
 else if(action==='split-v'||action==='split-h'){
  const d=plannerUI.draft,c=d.compartments[plannerUI.selected];if(d.compartments.length>=80)throw new Error('Maximum 80 compartments.');
  const axis=action==='split-v'?'w':'h',pos=axis==='w'?'x':'y';if(c[axis]<2)throw new Error('This compartment is too small to split.');
  c[axis]/=2;const n={...c,id:null,[pos]:c[pos]+c[axis]};let k=1;while(d.compartments.some(x=>x.code.toUpperCase()==='N'+k))k++;n.code='N'+k;n.label=t('compartment')+' '+n.code;d.compartments.push(n);render();
 }else if(action==='remove-cell'){
  const d=plannerUI.draft,c=d.compartments[plannerUI.selected];if(d.compartments.length<2)throw new Error('Keep at least one compartment.');
  if(c.id&&state.garments.some(g=>g.compartment_id===c.id))throw new Error('Move the clothes before removing this compartment.');
  if(!confirm('Remove this compartment from the plan? History-linked compartments cannot be removed.'))return;d.compartments.splice(plannerUI.selected,1);plannerUI.selected=0;render();
 }else if(action==='add-opening'){if(plannerUI.draft.room.openings.length>=16)throw new Error('Maximum 16 openings.');plannerUI.draft.room.openings.push({kind:'window',wall:0,offset:0,width:600});render();}
 else if(action==='remove-opening'){plannerUI.draft.room.openings.splice(Number(button.dataset.index),1);render();}
 else if(action==='gallery'){state.selectedCompartment=Number(button.dataset.id);plannerUI.view='gallery';plannerUI.query='';plannerUI.category='all';render();window.scrollTo(0,0);}
 else if(action==='add')openGarmentModal(null,state.selectedCompartment);
 else if(action==='detail')showDetail(Number(button.dataset.id),(button.dataset.scope==='all'?state.garments:galleryItems()).map(g=>g.id));
 else if(action==='prev'||action==='next-photo'){const ids=plannerUI.detailIds,delta=action==='prev'?-1:1;showDetail(ids[(plannerUI.detailIndex+delta+ids.length)%ids.length]);}
 else if(action==='edit-item'){openGarmentModal(Number(button.dataset.id));}
 else if(action==='remove-item'){if(!confirm(t('deleteConfirm')))return;await api('/api/garments/'+button.dataset.id,{method:'DELETE'});closeModal();await refresh();flash(t('saved'));}
 else if(action==='move-item'){const g=state.garments.find(g=>g.id===Number(button.dataset.id));modal(`<div class="modal-head"><h2>${t('move')} / ${e(g.name)}</h2><button class="icon-button" data-action="close-modal">${svg('x')}</button></div><form id="move-garment-form" data-id="${g.id}"><label class="planner-field">${t('compartment')}<select class="field" name="compartment_id">${optionsForComp(g.compartment_id)}</select></label><div class="modal-actions"><button class="btn btn-primary" type="submit">${t('save')}</button></div></form>`);}
 else if(action==='zoom'){const g=state.garments.find(g=>g.id===Number(button.dataset.id));if(!g?.photo_filename)return;modal(`<div class="modal-head"><h2>${e(g.name)}</h2>${plButton('return-detail',t('back'),`data-id="${g.id}"`)}</div><div class="zoom-photo">${realPhoto(g)}</div>`);document.querySelector('.modal').classList.add('zoom-modal');}
 else if(action==='return-detail')showDetail(Number(button.dataset.id));
 else if(action==='take-photo'){const input=document.getElementById('garment-photo');input.setAttribute('capture','environment');input.click();}
}
document.addEventListener('click',ev=>{const b=ev.target.closest('[data-plan]');if(!b)return;ev.preventDefault();ev.stopImmediatePropagation();handlePlan(b).catch(err=>flash(err.message));},true);
document.addEventListener('keydown',ev=>{const el=ev.target.closest('[data-plan]');if(el?.tagName.toLowerCase()==='g'&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();handlePlan(el).catch(err=>flash(err.message));}});
document.addEventListener('input',ev=>{
 if(ev.target.id==='gallery-search'){plannerUI.query=ev.target.value;document.getElementById('gallery-results').innerHTML=photoGrid(galleryItems());}
 const field=ev.target.dataset.field;if(!field||!plannerUI.editing)return;
 const parts=field.split('.'),d=plannerUI.draft;let obj,key=parts.at(-1),val=ev.target.type==='number'?Number(ev.target.value):ev.target.value;
 if(parts[0]==='opening'){obj=d.room.openings[Number(parts[1])];if(key==='wall')val=Number(val);}
 else if(parts[0]==='cell'){obj=d.compartments[plannerUI.selected];if(['x','w'].includes(key))val=val*100/d.cabinet.width;if(['y','h'].includes(key))val=val*100/d.cabinet.height;}
 else{obj=d[parts[0]];if(key==='rotation')val=Number(val);}
 obj[key]=val;previewDraft();
});
document.addEventListener('change',ev=>{
 if(ev.target.id==='gallery-category'){plannerUI.category=ev.target.value;document.getElementById('gallery-results').innerHTML=photoGrid(galleryItems());}
 if(ev.target.dataset.field==='room.shape'){const r=plannerUI.draft.room;r.openings=r.openings.filter(o=>o.wall<roomPoints(r).length);render();}
 if(ev.target.id==='garment-photo'){
  const file=ev.target.files?.[0];if(!file)return;const old=document.getElementById('new-photo-preview');if(old){URL.revokeObjectURL(old.src);old.remove();}
  const img=document.createElement('img');img.id='new-photo-preview';img.className='upload-preview';img.alt=t('photo');img.src=URL.createObjectURL(file);ev.target.parentElement.after(img);
 }
});
document.addEventListener('submit',async ev=>{if(ev.target.id!=='move-garment-form')return;ev.preventDefault();const form=ev.target,button=form.querySelector('button[type="submit"]');button.disabled=true;try{const cid=new FormData(form).get('compartment_id');await api('/api/garments/'+form.dataset.id+'/move',jsonOptions('PATCH',{compartment_id:cid?Number(cid):null}));closeModal();await refresh();flash(t('saved'));}catch(err){flash(err.message);}finally{button.disabled=false;}});
let dragging=null;
document.addEventListener('pointerdown',ev=>{if(!ev.target.closest('[data-wardrobe-drag]'))return;const map=document.getElementById('room-map');const point=map.createSVGPoint();point.x=ev.clientX;point.y=ev.clientY;const p=point.matrixTransform(map.getScreenCTM().inverse());dragging={pointer:ev.pointerId,x:p.x,y:p.y,startX:plannerUI.draft.cabinet.x,startY:plannerUI.draft.cabinet.y,scale:Number(map.dataset.scale)};ev.preventDefault();});
document.addEventListener('pointermove',ev=>{if(!dragging||ev.pointerId!==dragging.pointer)return;const map=document.getElementById('room-map');if(!map)return;const pt=map.createSVGPoint();pt.x=ev.clientX;pt.y=ev.clientY;const p=pt.matrixTransform(map.getScreenCTM().inverse()),r=plannerUI.draft.room,w=plannerUI.draft.cabinet;const fw=w.rotation===90?w.depth:w.width,fd=w.rotation===90?w.width:w.depth;
 w.x=Math.round(Math.max(0,Math.min(r.width-fw,dragging.startX+(p.x-dragging.x)/dragging.scale))/10)*10;w.y=Math.round(Math.max(0,Math.min(r.depth-fd,dragging.startY+(p.y-dragging.y)/dragging.scale))/10)*10;
 previewDraft();for(const k of ['x','y']){const f=document.querySelector(`[data-field="cabinet.${k}"]`);if(f)f.value=w[k];}
});
for(const name of ['pointerup','pointercancel'])document.addEventListener(name,()=>dragging=null);
const oldOpenGarment=openGarmentModal;
openGarmentModal=function(id=null,compId=null){oldOpenGarment(id,compId);const input=document.getElementById('garment-photo');if(input)input.insertAdjacentHTML('afterend',plButton('take-photo',t('camera')));};
const oldAct=act;
act=async function(button){if(button.dataset.action==='edit-garment'&&button.classList.contains('recent-tile')){showDetail(Number(button.dataset.id),state.garments.map(g=>g.id));return;}return oldAct(button);};
const oldPhoto=photoMarkup;photoMarkup=g=>g.photo_filename?oldPhoto(g):`<span class="no-photo-mini">${svg('shirt')}<small>${t('noPhoto')}</small></span>`;
const oldChrome=appChrome;appChrome=inner=>oldChrome(inner).replace('ERP / Version 1','ERP / Version 1.1').replace('PHASE 01 / MVP','ROOM PLANNER / V1.1');
const oldSettings=renderSettings;renderSettings=()=>oldSettings().replace('One wardrobe / Nine editable compartments','W01 / Room planner & editable compartments').replace('Physical positions A1-C3 remain fixed in Phase 1. Edit names and compartment types here.','Change positions, sizes and splits in the room planner.');
window.addEventListener('beforeunload',ev=>{if(plannerUI.editing){ev.preventDefault();ev.returnValue='';}});

const oldOpenCompartment=openCompartmentModal;
openCompartmentModal=function(id){oldOpenCompartment(id);const select=document.getElementById('compartment-kind'),c=state.bootstrap.compartments.find(c=>c.id===Number(id));if(select){select.insertAdjacentHTML('beforeend',`<option value="box">${t('box')}</option>`);select.value=c.kind;}};
const oldGarmentCard=renderGarmentCard;
renderGarmentCard=function(g){return oldGarmentCard(g).replace('<div class="garment-thumb">',`<button type="button" class="garment-thumb garment-photo-button" data-plan="detail" data-scope="all" data-id="${g.id}" aria-label="${e(g.name)}">`).replace('</div></div><div class="garment-body">','</div></button><div class="garment-body">');};

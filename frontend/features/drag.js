export const driverDragType = 'application/x-f1-driver';


export function parseDriverDrag(value) {
  try {
    const payload=JSON.parse(value);
    if (!payload || !Number.isSafeInteger(payload.driverId) || payload.driverId<=0 || !['entry','seat','academy'].includes(payload.source)) return null;
    if (payload.source!=='entry' && (!Number.isSafeInteger(payload.teamId)||payload.teamId<=0)) return null;
    if (payload.source==='seat' && ![1,2].includes(payload.seat)) return null;
    return payload;
  } catch {return null;}
}

export function bindDriverDrag(root, {select, dropSeat, dropAcademy, dropEntry}) {
  const zone = target=>target.closest('[data-seat-drop],[data-academy-drop],[data-entry-drop]');
  const clear=()=>root.querySelectorAll('.drag-over,.dragging').forEach(element=>element.classList.remove('drag-over','dragging'));
  root.querySelectorAll('[data-drag-driver]').forEach(element=>{
    element.draggable=true;
    element.addEventListener('dragstart',event=>{
      const payload={driverId:Number(element.dataset.dragDriver),source:element.dataset.dragSource??'entry'};
      if(payload.source!=='entry')payload.teamId=Number(element.dataset.dragTeam);
      if(payload.source==='seat')payload.seat=Number(element.dataset.dragSeat);
      event.dataTransfer.setData(driverDragType,JSON.stringify(payload));
      event.dataTransfer.effectAllowed='move';
      select(payload.driverId);
      element.classList.add('dragging');
    });
    element.addEventListener('dragend',clear);
  });
  root.addEventListener('dragover',event=>{
    const target=zone(event.target);
    if(!target||!Array.from(event.dataTransfer.types).includes(driverDragType))return;
    event.preventDefault();
    event.dataTransfer.dropEffect='move';
    root.querySelectorAll('.drag-over').forEach(element=>{if(element!==target)element.classList.remove('drag-over');});
    target.classList.add('drag-over');
  });
  root.addEventListener('dragleave',event=>{
    const target=zone(event.target);
    if(target&&!target.contains(event.relatedTarget))target.classList.remove('drag-over');
  });
  root.addEventListener('drop',event=>{
    const target=zone(event.target);
    if(!target)return;
    const payload=parseDriverDrag(event.dataTransfer.getData(driverDragType));
    if(!payload)return;
    event.preventDefault();
    clear();
    select(payload.driverId);
    if(target.hasAttribute('data-seat-drop'))dropSeat(Number(target.dataset.dropTeam),Number(target.dataset.seatDrop),payload);
    else if(target.hasAttribute('data-academy-drop'))dropAcademy(Number(target.dataset.academyDrop),payload);
    else dropEntry(payload);
  });
}

import {api, patch, session, escape as esc} from '../api.js';
import {driverGroups, driverGroup, driverSubtitle, sortedDrivers, sortControl} from '../drivers.js';
import {bindDriverDrag} from './drag.js';
import {openContractHub} from './contract-hub.js';


export function gridFeature(context) {
  const {state, heading, field, openDialog, mutate, navigate} = context;
  let gridData;
  let selected = null;
  let search = '';
  let preview = null;

  const category = driver => driverSubtitle(driver,state.teams);
  const driverChip = (driver, slot, year, teamId) => {
    if (!driver) return `<button class="seat empty-seat" data-seat="${slot.seat}" data-seat-drop="${slot.seat}" data-drop-team="${teamId}">Carro ${slot.seat} <b>Vaga aberta · solte aqui</b></button>`;
    const future = slot.future;
    const target = state.teams.find(team => team.TeamID === future?.TeamID);
    const dot = future ? `<i class="contract-dot" title="Contrato futuro: ${esc(target?.name ?? future.TeamName)} até ${future.EndSeason}"></i>` : '';
    return `<button class="seat" data-seat="${slot.seat}" data-seat-drop="${slot.seat}" data-drop-team="${teamId}" draggable="true" data-drag-driver="${driver.StaffID}" data-drag-source="seat" data-drag-team="${teamId}" data-drag-seat="${slot.seat}" title="Arraste ${esc(driver.name)} ou solte outro piloto aqui"><small>CARRO ${slot.seat}</small><b>${esc(driver.name)}</b>${dot}</button>`;
  };
  const slotButtons = (slot, teamId, year) => `<div data-target-team="${teamId}">${driverChip(slot.driver,slot,year,teamId)}${slot.contract?`<div class="seat-contracts"><button data-edit-contract="${slot.contract.contract_id}" data-contract-driver="${slot.driver.StaffID}" data-is-future="${slot.contract.ContractType===3}">Contrato · ${slot.contract.EndSeason}</button>${slot.future&&slot.contract.ContractType!==3?`<button data-edit-contract="${slot.future.contract_id}" data-contract-driver="${slot.driver.StaffID}" data-is-future="true">● Próximo contrato</button>`:''}</div>`:''}</div>`;
  function academyMarkup(entry) {
    const members=entry.academy??entry.reserves.map(driver=>({driver,contract:driver.affiliations.find(contract=>contract.TeamID===entry.team.TeamID&&contract.PosInTeam>2)}));
    return `<div class="academy-block" data-academy-drop="${entry.team.TeamID}"><div class="academy-toolbar"><small>ACADEMIA · ${members.length} PILOTOS · ARRASTE UM NOME PARA CÁ</small><button data-add-academy="${entry.team.TeamID}">＋ Adicionar à academia</button></div><div class="reserves">${members.map(member=>`<span class="academy-member"><button data-reserve="${member.driver.StaffID}" draggable="true" data-drag-driver="${member.driver.StaffID}" data-drag-source="academy" data-drag-team="${entry.team.TeamID}" title="Arraste para promover, mudar de academia ou desligar">${esc(member.driver.name)}</button>${member.contract?`<button class="academy-edit" data-edit-contract="${member.contract.contract_id}" data-contract-driver="${member.driver.StaffID}" data-is-future="${member.contract.ContractType===3}" title="Editar contrato">✎</button><button class="academy-remove" data-remove-academy="${member.driver.StaffID}" data-academy-team="${entry.team.TeamID}" data-academy-timing="${state.gridYear&&state.gridYear!==session.meta.season?'next':'now'}" title="Desligar da academia">×</button>`:''}</span>`).join('')||'<small>Solte um piloto aqui para contratar para a academia.</small>'}</div></div>`;
  }

  async function view() {
    const year = state.gridYear || session.meta.season;
    gridData = await api(`/grid?year=${year}`);
    state.driverSort ||= 'category';
    const choices = sortedDrivers(gridData.drivers,state.driverSort).filter(driver => `${driver.name} ${category(driver)}`.toLowerCase().includes(search.toLowerCase()));
    if (!choices.some(driver=>driver.StaffID===selected)) selected=choices[0]?.StaffID;
    let previousGroup=-1;
    const candidateRows=choices.map(driver=>{
      const group=driverGroup(driver);
      const divider=state.driverSort==='category'&&group!==previousGroup?`<div class="driver-group">${esc(driverGroups[group])}</div>`:'';
      previousGroup=group;
      return `${divider}<button class="candidate ${selected===driver.StaffID?'selected':''}" data-candidate="${driver.StaffID}" draggable="true" data-drag-driver="${driver.StaffID}" data-drag-source="entry" style="--color:${driver.team?.color??'#b2a1ff'}"><b>${esc(driver.name)}</b><span>${esc(category(driver))}</span><small>${driver.average??'—'}</small></button>`;
    }).join('');
    const cards = gridData.teams.map((entry, index) => {
      const angle = -Math.PI / 2 + index / gridData.teams.length * Math.PI * 2;
      return `<article class="lineup-card" style="--color:${entry.team.color};--x:${50 + 38 * Math.cos(angle)}%;--y:${50 + 39 * Math.sin(angle)}%"><div class="grid-team"><span class="team-emblem">${esc(entry.team.code)}</span><b>${esc(entry.team.name)}</b></div><div class="seats">${entry.slots.map(slot => slotButtons(slot,entry.team.TeamID,year)).join('')}</div></article>`;
    }).join('');
    const rows = gridData.teams.map(entry => `<article class="roster-row" style="--color:${entry.team.color}"><div class="grid-team"><span class="team-emblem">${esc(entry.team.code)}</span><b>${esc(entry.team.name)}</b></div><div class="seats">${entry.slots.map(slot => slotButtons(slot,entry.team.TeamID,year)).join('')}</div>${academyMarkup(entry)}</article>`).join('');
    return heading('GRID & CONTRACTS', 'Seu grid. Suas decisões.', 'Clique em qualquer piloto para abrir o hub de contratos atuais e futuros. Arraste os nomes para transferir entre carro 1, carro 2 e academia.') +
      `<div class="toolbar grid-toolbar"><div class="segmented"><button data-grid-year="${session.meta.season}" class="${year===session.meta.season?'active':''}">Temporada atual</button><button data-grid-year="${session.meta.season+1}" class="${year!==session.meta.season?'active':''}">Próxima temporada</button></div><button id="toggle-lineup" class="button ghost">${state.lineup?'☷ Contratos':'◉ Line-ups'}</button><span class="contract-key"><i class="contract-dot"></i> Contrato futuro assinado</span><small>Vaga projetada respeita duração e contratos futuros.</small></div>` +
      (state.lineup ? `<section class="lineup-board">${cards}<div class="lineup-center"><strong>${year===session.meta.season?'Atual':'Próxima'}</strong><b>DRIVER<br>LINE-UPS</b></div></section>` : `<div class="grid-workspace"><aside class="panel candidate-panel" data-entry-drop><h3>Piloto de entrada</h3><input id="candidate-search" class="search" placeholder="Piloto, equipe ou categoria…" value="${esc(search)}">${sortControl('candidate-sort',state.driverSort)}<small class="drop-instruction">Solte um titular ou integrante aqui para liberar o vínculo.</small><div class="candidate-list">${candidateRows}</div></aside><section class="roster-list">${rows}</section></div>`);
  }

  async function transferDialog(teamId,seat,preferSwap=false) {
    if (!selected) return;
    const driver = gridData.drivers.find(driver=>driver.StaffID===selected);
    const entry = gridData.teams.find(entry=>entry.team.TeamID===teamId);
    const slot = entry.slots[seat-1];
    const next = state.gridYear && state.gridYear !== session.meta.season;
    preview = null;
    openDialog(`${driver.name} → ${entry.team.name}`,`<div class="transfer-summary"><span>ENTRA <b>${esc(driver.name)}</b></span><span>SAI <b>${esc(slot.driver?.name??'Vaga aberta')}</b></span></div><div class="form-grid">${field('salary','Salário anual ($)',driver.contract?.Salary??1000000,'number','required min="0" max="1000000000"')}${field('end_season','Contrato até',Math.max(session.meta.season+1,driver.contract?.EndSeason??0),'number',`required min="${session.meta.season+(next?1:0)}" max="9999"`)}<label class="form-field">Destino de quem sai<select name="displaced" ${next?'disabled':''}><option value="release">Sem contrato nesta categoria</option>${next?'':'<option value="swap">Trocar para a vaga de quem entra</option><option value="reserve">Manter como reserva na equipe</option>'}</select></label></div><div class="notice">${next?'Contrato para a próxima temporada. O grid atual permanece. Contratos atuais conflitantes terminam neste ano.':'Transferência imediata. Vínculos atuais e ofertas dos pilotos envolvidos serão encerrados; pontos e resultados anteriores ficam preservados. A licença de F1 é habilitada para o novo titular.'}</div><button type="button" id="transfer-preview" class="button secondary">Conferir transferência</button><div id="preview-result"></div>`,async data=>{
      const edit = readTransfer(data,teamId,seat,next);
      if (!preview || JSON.stringify(edit)!==preview.signature) throw new Error('Confira a transferência novamente antes de aplicar.');
      await api('/transfers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...edit,expected_outgoing:preview.outgoing})});
    });
    document.querySelector('#transfer-preview').onclick=async()=>{
      const result=document.querySelector('#preview-result');
      try {
        const edit=readTransfer(new FormData(document.querySelector('#modal-form')),teamId,seat,next);
        const response=await api('/transfers/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(edit)});
        preview={signature:JSON.stringify(edit),outgoing:response.outgoing?.StaffID??null};
        result.innerHTML=`<div class="notice"><b>${esc(response.incoming.name)}</b> assume ${esc(response.team.name)} / carro ${seat} em ${response.year}.<br>Saída: ${esc(response.outgoing?.name??'ninguém')} · destino: ${esc(edit.displaced)}.<br>${esc(response.message)}</div>`;
      } catch(error){result.innerHTML=`<div class="notice warning">${esc(error.message)}</div>`;}
    };
    if(preferSwap&&!next)document.querySelector('#modal-form [name="displaced"]').value='swap';
  }

  function readTransfer(data,teamId,seat,next) {
    return {driver_id:selected,team_id:teamId,seat,timing:next?'next':'now',displaced:data.get('displaced')??'release',salary:Number(data.get('salary')),end_season:Number(data.get('end_season'))};
  }

  function academyDialog(teamId) {
    const driver=gridData.drivers.find(driver=>driver.StaffID===selected);
    if(!driver)return;
    const team=gridData.teams.find(entry=>entry.team.TeamID===teamId).team;
    const next=!!(state.gridYear&&state.gridYear!==session.meta.season);
    openDialog(`${driver.name} → academia ${team.name}`,`<div class="notice">Academia ${next?'da próxima temporada':'atual'}, sem ocupar carro 1 ou carro 2. ${driver.contract?.Formula===1&&driver.contract?.PosInTeam<=2?'O piloto deixará sua vaga de titular na F1 '+(next?'ao fim deste ano.':'agora.'):'Os titulares da equipe não mudam.'} A academia não tem limite fixo no editor.</div><div class="form-grid">${field('salary','Salário anual ($)',driver.contract?.Salary??100000,'number','required min="0" max="1000000000"')}${field('end_season','Contrato até',Math.max(session.meta.season+1,driver.contract?.EndSeason??0),'number',`required min="${session.meta.season+(next?1:0)}" max="9999"`)}</div><label class="filter-line"><input type="checkbox" name="keep_feeder_seat" checked> Manter vaga e contrato de F2/F3, se houver</label><p>Vínculos de academia com outra equipe de F1 nesta temporada são substituídos. Resultados anteriores permanecem.</p>`,data=>api(`/teams/${teamId}/academy`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({driver_id:selected,salary:Number(data.get('salary')),end_season:Number(data.get('end_season')),keep_feeder_seat:data.has('keep_feeder_seat'),timing:next?'next':'now'})}));
  }

  async function contractDialog(contractId,driverId,isFuture) {
    const driver=gridData.drivers.find(driver=>driver.StaffID===driverId);
    const contract=[...driver.affiliations,...driver.future_contracts].find(contract=>contract.contract_id===contractId);
    if(!contract)return;
    const team=state.teams.find(team=>team.TeamID===contract.TeamID);
    openDialog(`${driver.name} · ${isFuture?'contrato futuro':'contrato atual'}`,`<div class="notice">${esc(team?.name??contract.TeamName)} / ${contract.PosInTeam>2?'academia':'carro '+contract.PosInTeam}</div><div class="form-grid">${field('salary','Salário anual ($)',contract.Salary,'number','required min="0" max="1000000000"')}${field('end_season','Válido até',contract.EndSeason,'number',`required min="${session.meta.season+(isFuture?1:0)}" max="9999"`)}${field('race_bonus','Bônus por corrida ($)',contract.RaceBonus,'number','required min="0" max="100000000"')}</div>${isFuture?'<div class="notice warning">Cancelar o contrato futuro não prolonga contratos atuais que tenham sido encurtados pela transferência.</div><button type="button" id="cancel-future" class="button ghost">Cancelar contrato futuro</button>':''}`,data=>patch(`/contracts/${contractId}`,{salary:Number(data.get('salary')),end_season:Number(data.get('end_season')),race_bonus:Number(data.get('race_bonus'))}));
    const cancel=document.querySelector('#cancel-future');
    if(cancel)cancel.onclick=()=>mutate(()=>api(`/drivers/${driverId}/future-contract`,{method:'DELETE'}),document.querySelector('#modal-form'));
  }

  function bind() {
    document.querySelectorAll('[data-grid-year]').forEach(button=>button.onclick=()=>{state.gridYear=Number(button.dataset.gridYear);navigate();});
    document.querySelector('#toggle-lineup').onclick=()=>{state.lineup=!state.lineup;navigate();};
    const input=document.querySelector('#candidate-search');
    const sort=document.querySelector('#candidate-sort');
    if(sort)sort.onchange=event=>{state.driverSort=event.target.value;navigate();};
    if(input)input.oninput=()=>{search=input.value;clearTimeout(state.candidateTimer);state.candidateTimer=setTimeout(async()=>{await navigate();const searchInput=document.querySelector('#candidate-search');searchInput?.focus();searchInput?.setSelectionRange(search.length,search.length);},220);};
    const hub=driverId=>{selected=driverId;const driver=gridData.drivers.find(driver=>driver.StaffID===driverId);if(driver)openContractHub(driver,context,contractDialog);};
    document.querySelectorAll('[data-candidate]').forEach(button=>button.onclick=()=>hub(Number(button.dataset.candidate)));
    document.querySelectorAll('[data-target-team] [data-seat]').forEach(button=>button.onclick=()=>button.dataset.dragDriver?hub(Number(button.dataset.dragDriver)):transferDialog(Number(button.closest('[data-target-team]').dataset.targetTeam),Number(button.dataset.seat)));
    document.querySelectorAll('[data-reserve]').forEach(button=>button.onclick=()=>hub(Number(button.dataset.reserve)));
    document.querySelectorAll('[data-edit-contract]').forEach(button=>button.onclick=()=>contractDialog(Number(button.dataset.editContract),Number(button.dataset.contractDriver),button.dataset.isFuture==='true'));
    document.querySelectorAll('[data-add-academy]').forEach(button=>button.onclick=()=>academyDialog(Number(button.dataset.addAcademy)));
    document.querySelectorAll('[data-remove-academy]').forEach(button=>button.onclick=()=>{
      const driver=gridData.drivers.find(driver=>driver.StaffID===Number(button.dataset.removeAcademy));
      openDialog(`Desligar ${driver.name} da academia`,`<p>Remove somente o vínculo de academia selecionado. Vagas em F2/F3 e contratos de outras temporadas permanecem. Você pode desfazer depois.</p>`,()=>api(`/teams/${button.dataset.academyTeam}/academy/${driver.StaffID}?timing=${button.dataset.academyTiming}`,{method:'DELETE'}));
    });
    const root=document.querySelector('.grid-workspace,.lineup-board');
    if(root)bindDriverDrag(root,{
      select:driverId=>{if(gridData.drivers.some(driver=>driver.StaffID===driverId))selected=driverId;},
      dropSeat:(teamId,seat,payload)=>{
        if(!gridData.drivers.some(driver=>driver.StaffID===payload.driverId))return;
        if(payload.source==='seat'&&payload.teamId===teamId&&payload.seat===seat)return;
        transferDialog(teamId,seat,payload.source==='seat');
      },
      dropAcademy:(teamId,payload)=>{
        if(!gridData.drivers.some(driver=>driver.StaffID===payload.driverId))return;
        if(payload.source==='academy'&&payload.teamId===teamId)return;
        academyDialog(teamId);
      },
      dropEntry:payload=>{
        const driver=gridData.drivers.find(driver=>driver.StaffID===payload.driverId);
        if(!driver)return;
        if(payload.source==='entry'){navigate();return;}
        const timing=state.gridYear&&state.gridYear!==session.meta.season?'next':'now';
        const endpoint=payload.source==='academy'?`/teams/${payload.teamId}/academy/${driver.StaffID}?timing=${timing}`:`/teams/${payload.teamId}/seats/${payload.seat}?expected_driver=${driver.StaffID}&timing=${timing}`;
        openDialog(`Liberar ${driver.name}`,`<p>Libera somente este vínculo ${timing==='next'?'na próxima temporada':'atual'}. Os pontos, resultados e vínculos de outras categorias são preservados. A vaga correspondente ficará aberta.</p>`,()=>api(endpoint,{method:'DELETE'}));
      },
    });
  }
  return {view,bind};
}

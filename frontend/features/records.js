import {api, session, escape as esc, number} from '../api.js';


export function recordsFeature(context) {
  const {state,heading,navigate} = context;
  async function view() {
    const years=await api('/records/seasons');
    state.recordsYear ||= session.meta.season;
    const data=await api(`/records?season=${state.recordsYear}`);
    const points=state.recordsMode==='points';
    const display=result=>result ? result.DNF?'DNF':points?result.Points:result.FinishingPos : '—';
    const cell=result=>result?`<span class="finish pos-${result.FinishingPos} ${result.DNF?'dnf':''}">${display(result)}</span>`:'<span class="missing">—</span>';
    const leader=data.drivers[0];
    return heading('CAREER ARCHIVE','Records Hub','A história da sua carreira, corrida por corrida. GPs e sprints aparecem separados na mesma coluna.') +
      `<div class="toolbar"><label>Temporada <select id="records-year">${years.map(year=>`<option ${year===state.recordsYear?'selected':''}>${year}</option>`).join('')}</select></label><div class="segmented"><button data-records-mode="positions" class="${!points?'active':''}">Posições</button><button data-records-mode="points" class="${points?'active':''}">Pontos</button></div><span class="badge">F1 · ${data.races.length} ETAPAS</span><span class="muted">GP <b>12</b> · sprint <small>(S 3)</small></span></div><div class="archive-summary"><div><small>LÍDER DA TEMPORADA</small><b style="color:${leader?.team?.color??'#b2a1ff'}">${esc(leader?.name??'Sem resultados')}</b></div><div><small>PONTOS</small><b>${leader?.points??0}</b></div><div><small>VITÓRIAS / GPs</small><b>${leader?.wins??0}</b></div><div><small>PÓDIOS / GPs</small><b>${leader?.podiums??0}</b></div></div><div class="records-table"><table><thead><tr><th>#</th><th class="sticky-driver">Piloto</th>${data.races.map((race,index)=>`<th title="${esc(race.name)}"><small>${String(index+1).padStart(2,'0')}</small><b>${esc(race.code)}</b>${race.WeekendType===1?'<i>SPRINT</i>':''}</th>`).join('')}<th>VIT</th><th>PÓD</th><th>DNF</th><th>PTS</th></tr></thead><tbody>${data.drivers.map((driver,index)=>`<tr><td>${driver.position??index+1}</td><td class="sticky-driver"><span class="driver-color" style="background:${driver.team?.color??'#8793a7'}"></span><b style="color:${driver.team?.color??'#d8ddec'}">${esc(driver.name)}</b><small>${esc(driver.team?.name??'')}</small></td>${driver.cells.map(item=>`<td>${cell(item.race)}${item.sprint?`<small class="sprint-result" title="Sprint: P${item.sprint.FinishingPos} · ${item.sprint.Points} pontos">(S ${display(item.sprint)})</small>`:''}</td>`).join('')}<td>${driver.wins}</td><td>${driver.podiums}</td><td>${driver.dnfs}</td><td class="total-points">${number(driver.points)}</td></tr>`).join('')}</tbody></table></div><p>${esc(data.note)}</p><div class="chart-legend"><span><i style="background:#e7ca6e"></i>1º lugar</span><span><i style="background:#bbc4d3"></i>2º lugar</span><span><i style="background:#c58f61"></i>3º lugar</span><span>DNF · abandono</span><span>— · sem registro</span></div>`;
  }
  function bind() {
    document.querySelector('#records-year').onchange=event=>{state.recordsYear=Number(event.target.value);navigate();};
    document.querySelectorAll('[data-records-mode]').forEach(button=>button.onclick=()=>{state.recordsMode=button.dataset.recordsMode;navigate();});
  }
  return {view,bind};
}

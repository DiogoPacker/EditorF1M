import {api, request, patch, session, escape as esc, money, number, toast} from './api.js';
import {radar} from './charts.js';
import {gridFeature} from './features/grid.js';
import {comparisonFeature} from './features/comparison.js';
import {recordsFeature} from './features/records.js';
import {engineeringFeature} from './features/engineering.js';
import {driverGroup, driverSubtitle, sortedDrivers, sortControl} from './drivers.js';
import {installFontControls} from './preferences.js';
import {installNumberControls} from './controls.js';

const pages = [['overview','◈','Visão geral'],['grid','◉','Grid e transferências'],['drivers','♙','Pilotos e contratos'],['comparison','⇄','Comparar pilotos'],['performance','⌁','Desempenho'],['engines','⏣','Motores'],['records','♜','Records Hub'],['calendar','▦','Calendário'],['teams','⚑','Equipes e finanças'],['projects','⬡','Projetos e pesquisa'],['changes','↺','Alterações']];
const state = {page: 'overview', teams: [], drivers: [], team: Number(localStorage.getItem('f1-team')) || 3, driver: null, driverFilter: '', onlyGrid: false, driverSort: 'category', opponent: 4, all: true, metric: 'points', car: 1, generation: 0};
const main = document.querySelector('#main');
installFontControls();
localStorage.removeItem('f1-session');
const weatherNames = {1:'Ensolarado',2:'Parcialmente nublado',4:'Nublado',8:'Chuva leve',16:'Chuva',32:'Chuva forte'};
let pending = false;
main.addEventListener('input',event=>{if(event.target.closest('form'))pending=true;});
const nav = document.querySelector('#navigation');
nav.innerHTML = pages.map(([id, icon, label]) => `<button data-page="${id}"><span class="nav-icon">${icon}</span><span class="nav-text">${label}</span>${id === 'changes' ? '<small id="change-count">0</small>' : ''}</button>`).join('');
nav.addEventListener('click', event => {const button = event.target.closest('[data-page]'); if (button) navigate(button.dataset.page);});
const currentTeam = () => state.teams.find(team => team.TeamID === state.team) || state.teams[0];
const teamOptions = selected => state.teams.map(team => `<option value="${team.TeamID}" ${team.TeamID === selected ? 'selected' : ''}>${esc(team.name)}</option>`).join('');
const heading = (eyebrow, title, text, right = '') => `<div class="page-head"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(text)}</p></div>${right}</div>`;
const kpi = (label, value, note) => `<div class="kpi"><small>${esc(label)}</small><strong>${esc(value)}</strong><span>${esc(note)}</span></div>`;
const field = (name, label, value, type = 'number', extra = '') => `<label class="form-field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const table = (headers, rows) => `<div class="table-wrap"><table><thead><tr>${headers.map(header => `<th>${esc(header)}</th>`).join('')}</tr></thead><tbody>${rows.join('') || `<tr><td colspan="${headers.length}">Nenhum registro disponível.</td></tr>`}</tbody></table></div>`;

async function refreshState() {
  session.meta = await api();
  [state.teams, state.drivers] = await Promise.all([api('/teams'), api('/drivers')]);
  if (!state.teams.some(team => team.TeamID === state.team)) state.team = state.teams[0]?.TeamID;
  document.querySelector('#team-select').innerHTML = teamOptions(state.team);
  const team = currentTeam();
  if (team) {
    document.documentElement.style.setProperty('--team',team.color);
    document.querySelector('#team-identity').textContent = `${team.code} / ${team.name} · P${team.Position ?? '—'} · ${team.Points ?? 0} pts`;
  }
  const count = session.meta.changes.length;
  const status = document.querySelector('#save-status');
  status.textContent = `${session.meta.filename} · ${count ? count + ' alterações' : 'sem alterações'}`;
  status.classList.toggle('dirty',count > 0);
  document.querySelector('#change-count').textContent = count;
  document.querySelector('#undo').disabled = !session.meta.undo_available;
  document.querySelector('#export').disabled = false;
  document.querySelector('#export').textContent = session.meta.can_export_save ? '↓ Exportar novo save' : '↓ Exportar SQLite';
  document.querySelector('#footer-info').textContent = `${session.meta.season} · ${session.meta.modded ? 'SECTOR33 DETECTADO' : 'BASE ORIGINAL'} · ${count} ALTERAÇÕES NA CÓPIA`;
}

async function navigate(page = state.page) {
  if (pending && !confirm('Há campos ainda não aplicados. Deseja descartar essas edições e trocar de tela?')) return false;
  pending = false;
  state.page = page;
  state.generation++;
  const generation = state.generation;
  for (const button of nav.querySelectorAll('button')) button.classList.toggle('active',button.dataset.page === page);
  document.querySelector('#breadcrumb').textContent = pages.find(item => item[0] === page)?.[2] || page;
  if (!session.id) {welcome(); return true;}
  main.innerHTML = '<div class="loading">Carregando dados do save…</div>';
  try {
    const html = await views[page]();
    if (generation !== state.generation) return false;
    main.innerHTML = html;
    bindPage();
    return true;
  } catch (error) {if (generation === state.generation) main.innerHTML = `<div class="notice warning">${esc(error.message)}</div>`; toast(error.message,true);return false;}
}

function welcome() {
  main.innerHTML = `<div class="empty"><div class="big-logo">F1</div><div class="eyebrow">SEU SAVE. SEU GRID. SUAS REGRAS.</div><h1>O pit wall da sua carreira.</h1><p>Abra um save do F1 Manager 2024 para explorar pilotos, comparar os carros e editar sua temporada em uma cópia independente.</p><div class="features"><span>Pilotos e atributos</span><span>Calendário</span><span>Desempenho</span></div><label class="button primary" for="file">↥ Abrir meu save</label><div class="welcome-author"><small>Desenvolvido por</small><div class="author-links"><span>Diogo Packer Elias</span><a href="https://www.linkedin.com/in/diogo-packer-elias-11a3b7b6/" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn de Diogo Packer Elias" title="LinkedIn"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="3" fill="currentColor"/><path d="M6 10h3v9H6zm1.5-4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3M11 10h3v1c1-2 6-2 6 3v5h-3v-5c0-2-3-2-3 0v5h-3z" fill="#10141c"/></svg></a><a href="https://github.com/DiogoPacker" target="_blank" rel="noopener noreferrer" aria-label="GitHub de Diogo Packer" title="GitHub"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.86c-2.78.6-3.37-1.18-3.37-1.18-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.64-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02A9.6 9.6 0 0 1 12 6.82c.85 0 1.71.11 2.51.34 1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/></svg></a></div></div><p>Seu arquivo original é preservado. Exporte uma nova cópia ao terminar.</p></div>`;
}

const views = {
  async overview() {
    const team = currentTeam(), projects = await api(`/teams/${state.team}/projects`);
    return heading(`COMMAND CENTER / ${session.meta.season}`, 'Seu grid, em detalhe.', 'Acompanhe a carreira e entre em qualquer equipe para explorar seus dados.', `<span class="badge accent">${session.meta.modded ? 'SECTOR33' : 'F1 MANAGER 24'}</span>`) +
      `<div class="kpis">${kpi('Equipe em foco',team.name, 'Clique em um cartão para trocar')}${kpi('Caixa disponível',money(team.Balance),'Saldo atual, não é teto de gastos')}${kpi('Campeonato',`P${team.Position ?? '—'} / ${team.Points ?? 0} pts`,'Classificação registrada no save')}${kpi('Desenvolvimento',projects.length,`${projects.filter(item=>item.kind==='Pesquisa').length} pesquisas para a próxima temporada`)}</div>` +
      `<div class="section-head"><h2>Current grid <span class="muted">/ ${session.meta.season}</span></h2><small>${state.teams.length} EQUIPES · DADOS DO SAVE</small></div><div class="team-grid">${state.teams.map(item => {
        const pair = state.drivers.filter(driver => driver.team?.TeamID === item.TeamID && driver.contract?.PosInTeam <= 2).sort((first, second) => first.contract.PosInTeam-second.contract.PosInTeam);
        return `<button class="team-card ${item.TeamID===state.team?'selected':''}" style="--color:${item.color}" data-team="${item.TeamID}"><span class="rank">${String(item.Position ?? '—').padStart(2,'0')}</span><span class="team-code">${esc(item.code)}</span><h3>${esc(item.name)}</h3><div class="card-stats"><span><b>${item.Points ?? 0}</b> PTS</span><span>${money(item.Balance)}</span></div><div class="driver-pair">${pair.map(driver=>`<span>${esc(driver.name)}</span>`).join('') || '<span>Sem titulares identificados</span>'}</div></button>`;
      }).join('')}</div>`;
  },
  async drivers() {
    let list = sortedDrivers(state.drivers,state.driverSort).filter(driver => !state.onlyGrid || driverGroup(driver)===0);
    list = list.filter(driver => `${driver.name} ${driverSubtitle(driver,state.teams)}`.toLowerCase().includes(state.driverFilter.toLowerCase()));
    if (!list.some(driver => driver.StaffID === state.driver)) state.driver = list[0]?.StaffID;
    const detail = state.driver ? await api(`/drivers/${state.driver}`) : null;
    state.driverRaw = detail;
    return heading('DRIVER DATABASE', 'Pilotos e contratos', 'Selecione um piloto, conheça seus atributos e aplique as alterações à cópia de trabalho.') +
      `<div class="split"><aside class="panel"><h3>Selecionar piloto</h3><input class="search" id="driver-search" placeholder="Buscar piloto ou equipe…" value="${esc(state.driverFilter)}">${sortControl('driver-sort',state.driverSort)}<label class="filter-line"><input type="checkbox" id="only-grid" ${state.onlyGrid?'checked':''}> Apenas titulares da F1</label><div class="driver-list">${list.map(driver=>`<button class="driver-row ${driver.StaffID===state.driver?'selected':''}" style="--color:${driver.team?.color ?? '#98a7c5'}" data-driver="${driver.StaffID}"><span class="initials">${esc(driver.name.split(' ').map(word=>word[0]).slice(0,2).join(''))}</span><span><span class="driver-name">${esc(driver.name)}</span><small>${esc(driverSubtitle(driver,state.teams))}</small></span><span class="rating">${number(driver.average)}</span></button>`).join('')}</div></aside><section>${detail ? driverPanel(detail) : '<div class="panel">Nenhum piloto corresponde à busca.</div>'}</section></div>`;
  },
  async calendar() {
    const races = await api('/calendar');
    return heading(`SEASON PLANNER / ${session.meta.season}`, 'Calendário da temporada', 'Veja as etapas e edite chuva e temperatura das próximas corridas.', `<span class="badge">${races.length} ETAPAS</span>`) + `<div class="calendar-grid">${races.map(race=>`<div class="race-card ${race.completed?'completed':''}"><span class="round">ROUND ${String(race.round).padStart(2,'0')}</span><span class="badge ${race.completed?'green':'accent'}">${race.completed?'CONCLUÍDO':race.WeekendType?'SPRINT':'GRAND PRIX'}</span><h3>${esc(race.track)}</h3><span class="date">${new Date(race.date+'T12:00:00').toLocaleDateString('pt-BR')} · ${race.Laps} voltas</span><div class="weather"><span>${race.WeatherStateRace>=8?'☂':'☀'} ${esc(weatherNames[race.WeatherStateRace]??'Variável')}</span><span>${number(race.TemperatureRace,1)} °C</span></div><button class="button ghost" data-race="${race.RaceID}" ${race.completed?'disabled':''}>${race.completed?'Etapa realizada':'Editar clima →'}</button></div>`).join('')}</div><div class="notice">A data é lida do contador de dias do jogo. Esta versão não remove, adiciona ou reordena etapas; preserva o calendário e as regras Sector33.</div>`;
  },
  async teams() {
    const team=currentTeam();
    return heading('TEAM MANAGEMENT', team.name, 'Finanças da equipe selecionada. O saldo não é o teto de gastos.') + `<div class="kpis">${kpi('Caixa atual',money(team.Balance),'Disponibilidade registrada no banco')}${kpi('Construtores',`P${team.Position}`,'Posição atual')}${kpi('Pontos',team.Points,'Classificação oficial')}${kpi('Equipe',team.code,'Identidade de apresentação')}</div><form id="finance-form" class="panel"><div class="panel-title"><h2>Editar caixa</h2><span class="badge accent">CÓPIA DE TRABALHO</span></div><div class="form-grid">${field('balance','Saldo ($)',team.Balance,'number','required step="1" min="-1000000000" max="10000000000"')}</div><div class="form-actions"><button class="button primary">Aplicar alteração</button><small>Não altera despesas históricas nem orçamento projetado.</small></div></form><div class="section-head"><h2>Classificação das equipes</h2></div>${table(['Posição','Equipe','Pontos','Caixa'],state.teams.map(item=>`<tr><td>P${item.Position}</td><td><span class="team-name" style="--color:${item.color}">${esc(item.name)}</span></td><td>${item.Points}</td><td>${money(item.Balance)}</td></tr>`))}`;
  },
  async projects() {
    const [projects,expertise] = await Promise.all([api(`/teams/${state.team}/projects`), api(`/teams/${state.team}/expertise`)]);
    return heading('DEVELOPMENT CENTER', 'Projetos e pesquisa', `${currentTeam().name} · acompanhe o trabalho atual e a expertise para a próxima temporada.`) + table(['Projeto','Peça','Tipo','Temporada','Trabalho','Custo registrado','CFD','Túnel'],projects.map(project=>`<tr><td>#${project.ProjectID}</td><td>${esc(project.part)}</td><td><span class="badge ${project.kind==='Pesquisa'?'accent':''}">${project.kind}</span></td><td>${project.ValidFrom}</td><td>${project.progress==null?'—':number(project.progress,1)+'%'}<div class="progress"><span style="width:${project.progress??0}%"></span></div></td><td>${money(project.DesignCost)}</td><td>${project.CFD}</td><td>${project.WindTunnelTime}</td></tr>`)) + `<div class="section-head"><h2>Expertise · atual e próxima temporada</h2><small>EDITE UM ATRIBUTO POR VEZ</small></div>` + table(['Peça','Atributo','Expertise atual','Próxima temporada',''],expertise.map(item=>`<tr><td>${esc(item.part)}</td><td>${esc(item.label)}</td><td>${number(item.Expertise,3)}</td><td>${number(item.NextSeasonExpertise,3)}</td><td><button class="button ghost" data-expertise="${item.PartType},${item.PartStat}">Editar</button></td></tr>`)) + '<div class="notice">Expertise não é o atributo da peça instalada. Alterá-la influencia desenvolvimento; não substitui automaticamente os designs existentes.</div>';
  },
  async changes() {
    const changes=session.meta.changes;
    return heading('CHANGE JOURNAL','Tudo que você alterou.','As alterações ficam na cópia de trabalho e são incluídas juntas ao exportar o novo save.',`<span class="badge accent">${changes.length} ALTERAÇÕES</span>`) + `<div class="notice">As cópias de trabalho são guardadas localmente e podem ser retomadas após reiniciar o servidor. Desfazer funciona para alterações feitas desde a inicialização atual.</div><div class="change-list">${changes.map((change,index)=>`<div class="change"><span><b class="muted">${String(index+1).padStart(2,'0')} / </b>${esc(change.description)}</span><small>${new Date(change.time).toLocaleString('pt-BR')}</small></div>`).join('')||'<div class="panel"><p>Nenhuma alteração aplicada. Explore o banco ou edite um piloto para começar.</p></div>'}</div><div class="form-actions"><button id="page-export" class="button primary">↓ Exportar todas as alterações</button></div>`;
  }
};

const featureContext = {state,heading,field,table,teamOptions,currentTeam,openDialog,mutate,navigate,selectTeam};
const gridScreen = gridFeature(featureContext);
const comparisonScreen = comparisonFeature(featureContext);
const recordsScreen = recordsFeature(featureContext);
const engineeringScreen = engineeringFeature(featureContext);
const teamFinanceView = views.teams;
Object.assign(views, {
  grid:gridScreen.view,
  comparison:comparisonScreen.view,
  records:recordsScreen.view,
  engines:engineeringScreen.engines,
  performance:engineeringScreen.performance,
  teams:async()=>await teamFinanceView()+await engineeringScreen.teamSupplier(),
});
const featureBindings = {
  grid:gridScreen.bind,
  comparison:comparisonScreen.bind,
  records:recordsScreen.bind,
  engines:engineeringScreen.bindEngines,
  performance:engineeringScreen.bindPerformance,
  teams:engineeringScreen.bindSuppliers,
};

function driverPanel(driver) {
  const color=driver.team?.color??'#ad9eec';
  return `<div style="--team:${color}"><div class="driver-hero"><div><small>${esc(driver.team?.name??'SEM EQUIPE F1')} / DRIVER PROFILE</small><h2>${esc(driver.name)}</h2><p>Média simples dos atributos: <b>${number(driver.average,1)}</b> · não é o overall oficial do jogo</p></div><div class="number">${esc(driver.code_display)}</div></div><form id="driver-form"><div class="detail-grid"><div class="panel"><div class="panel-title"><h2>Atributos de pilotagem</h2><span class="badge">0–100</span></div><div class="stat-grid">${driver.stats.map(stat=>`<div class="stat-input"><label for="stat-${stat.StatID}">${esc(stat.label)}<input id="stat-${stat.StatID}" name="stat-${stat.StatID}" type="number" min="0" max="${Math.min(100,stat.Max)}" value="${stat.Val}" required></label><input type="range" data-range="stat-${stat.StatID}" min="0" max="${Math.min(100,stat.Max)}" value="${stat.Val}" aria-label="${esc(stat.label)}"></div>`).join('')}</div></div><div class="panel radar-panel"><h3>Perfil de pilotagem</h3>${radar(driver.stats)}<p>Atributos atuais. O radar é atualizado após aplicar a edição.</p></div></div><div class="panel" style="margin-top:18px"><div class="panel-title"><h2>Perfil do piloto</h2></div><div class="form-grid">${field('first_name','Nome',driver.first_name_display,'text','required maxlength="80"')}${field('last_name','Sobrenome',driver.last_name_display,'text','required maxlength="80"')}${field('aggression','Agressividade',driver.Aggression,'number','min="0" max="100" required')}${field('marketability','Valor de mercado',driver.Marketability,'number','min="0" max="100" required')}</div><div class="form-actions"><button class="button primary">Aplicar atributos e perfil</button><small>O original não será alterado.</small></div></div></form>${driver.contract?`<form id="contract-form" class="panel" style="margin-top:18px" data-contract="${driver.contract.contract_id}"><div class="panel-title"><h2>Contrato atual</h2><span class="badge">${esc(driver.team?.name??'OUTRA CATEGORIA')}</span></div><div class="form-grid">${field('salary','Salário anual ($)',driver.contract.Salary,'number','min="0" max="1000000000" required')}${field('end_season','Válido até',driver.contract.EndSeason,'number',`min="${session.meta.season}" max="2100" required`)}${field('race_bonus','Bônus por corrida ($)',driver.contract.RaceBonus,'number','min="0" max="100000000" required')}</div><div class="form-actions"><button class="button secondary">Aplicar contrato</button></div></form>`:''}<div class="section-head"><h2>Resultados · ${session.meta.season}</h2></div>${table(['Grande Prêmio','Largada','Chegada','Pontos','DNF'],driver.results.map(result=>`<tr><td>${esc(result.Name)}</td><td>${result.StartingPos}</td><td>${result.FinishingPos}</td><td>${result.Points}</td><td>${result.DNF?'Sim':'—'}</td></tr>`))}</div>`;
}

function bindPage() {
  main.querySelectorAll('[data-team]').forEach(button=>button.onclick=()=>selectTeam(Number(button.dataset.team)));
  main.querySelectorAll('[data-driver]').forEach(button=>button.onclick=()=>{state.driver=Number(button.dataset.driver);navigate();});
  const search=main.querySelector('#driver-search');
  if(search) search.oninput=()=>{clearTimeout(state.searchTimer);state.searchTimer=setTimeout(async()=>{state.driverFilter=search.value;await navigate();const replacement=main.querySelector('#driver-search');replacement?.focus();replacement?.setSelectionRange(state.driverFilter.length,state.driverFilter.length);},280);};
  bindChange('#only-grid',element=>state.onlyGrid=element.checked);
  bindChange('#driver-sort',element=>state.driverSort=element.value);
  bindChange('#metric',element=>state.metric=element.value);
  bindChange('#opponent',element=>state.opponent=Number(element.value));
  bindChange('#car',element=>state.car=Number(element.value));
  bindChange('#all-teams',element=>state.all=element.checked);
  main.querySelectorAll('[data-range]').forEach(range=>{range.oninput=()=>{document.getElementById(range.dataset.range).value=range.value;};document.getElementById(range.dataset.range).oninput=event=>range.value=event.target.value;});
  bindSubmit('#driver-form',async form=>{const data=new FormData(form), stats={}; for(const [key,value] of data) if(key.startsWith('stat-')) stats[key.slice(5)]=Number(value); const edit={aggression:Number(data.get('aggression')),marketability:Number(data.get('marketability')),stats}; const raw=state.driverRaw; const first=raw.first_name_display; const last=raw.last_name_display; if(data.get('first_name')!==first)edit.first_name=data.get('first_name'); if(data.get('last_name')!==last)edit.last_name=data.get('last_name'); await patch(`/drivers/${state.driver}`,edit);});
  bindSubmit('#contract-form',async form=>{const data=new FormData(form);await patch(`/contracts/${form.dataset.contract}`,{salary:Number(data.get('salary')),end_season:Number(data.get('end_season')),race_bonus:Number(data.get('race_bonus'))});});
  bindSubmit('#finance-form',async form=>patch(`/teams/${state.team}`,{balance:Number(new FormData(form).get('balance'))}));
  main.querySelectorAll('[data-race]').forEach(button=>button.onclick=()=>editRace(Number(button.dataset.race)));
  main.querySelectorAll('[data-expertise]').forEach(button=>button.onclick=()=>editExpertise(...button.dataset.expertise.split(',').map(Number)));
  const exportButton=main.querySelector('#page-export');if(exportButton)exportButton.onclick=exportSave;
  featureBindings[state.page]?.();
  installNumberControls(main);
}

function bindChange(selector,operation) {const element=main.querySelector(selector);if(element)element.onchange=()=>{operation(element);navigate();};}
function bindSubmit(selector,operation) {const form=main.querySelector(selector);if(form)form.onsubmit=async event=>{event.preventDefault();await mutate(()=>operation(form),form);};}
async function mutate(operation,form) {
  const button=form?.querySelector('button[type=submit],button:not([type])');
  if(button)button.disabled=true;
  try {await operation();pending=false;await refreshState();document.querySelector('#dialog').close();await navigate();toast('Alteração aplicada à cópia de trabalho.');}
  catch(error){toast(error.message,true);} finally {if(button)button.disabled=false;}
}

function openDialog(title,html,operation) {
  document.querySelector('#dialog-title').textContent=title;
  document.querySelector('#dialog-body').innerHTML=`<form id="modal-form">${html}<div class="form-actions"><button class="button primary">Aplicar à cópia</button></div></form>`;
  const form=document.querySelector('#modal-form');form.onsubmit=event=>{event.preventDefault();mutate(()=>operation(new FormData(form)),form);};
  installNumberControls(form);
  document.querySelector('#dialog').showModal();
}

async function editRace(id) {
  try {const race=(await api('/calendar')).find(item=>item.RaceID===id);openDialog(`Clima · ${race.track}`,`<div class="form-grid"><label class="form-field">Condição da corrida<select name="weather">${Object.entries(weatherNames).map(([key,label])=>`<option value="${key}" ${Number(key)===race.WeatherStateRace?'selected':''}>${label}</option>`).join('')}</select></label>${field('temperature','Temperatura (°C)',race.TemperatureRace,'number','min="-10" max="65" step="0.1" required')}</div><p>Atualiza a condição climática e o indicador de chuva juntos. Não altera treinos ou classificação.</p>`,data=>patch(`/calendar/${id}`,{weather:Number(data.get('weather')),temperature:Number(data.get('temperature'))}));} catch(error){toast(error.message,true);}
}
async function editExpertise(part,stat) {
  try {const item=(await api(`/teams/${state.team}/expertise`)).find(item=>item.PartType===part&&item.PartStat===stat);openDialog(`${item.part} · ${item.label}`,`<div class="form-grid">${field('expertise','Expertise atual',item.Expertise,'number','min="0" max="1000" step="any" required')}${field('next_season','Próxima temporada',item.NextSeasonExpertise,'number','min="0" max="1000" step="any" required')}</div>`,data=>patch(`/teams/${state.team}/expertise/${part}/${stat}`,{expertise:Number(data.get('expertise')),next_season:Number(data.get('next_season'))}));} catch(error){toast(error.message,true);}
}

async function selectTeam(id) {state.team=id;localStorage.setItem('f1-team',id);await refreshState();await navigate();}
document.querySelector('#team-select').onchange=event=>selectTeam(Number(event.target.value));
document.querySelector('#close-dialog').onclick=()=>document.querySelector('#dialog').close();
document.querySelector('#file').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  if((pending||session.meta?.changes.length)&&!confirm('Abrir outro save? Exporte o save atual antes de sair para manter suas alterações em um arquivo.')){event.target.value='';return;}
  const data=new FormData();data.append('file',file);document.body.classList.add('busy');
  try {const result=await request('/api/saves',{method:'POST',body:data});session.id=result.id;pending=false;state.driver=null;await refreshState();await navigate('overview');toast('Save carregado e validado. Original preservado.');}catch(error){toast(error.message,true);}finally{document.body.classList.remove('busy');event.target.value='';}
};
document.querySelector('#undo').onclick=async()=>{try{await api('/undo',{method:'POST'});await refreshState();await navigate();toast('Última alteração desfeita.');}catch(error){toast(error.message,true);}};

async function exportSave() {
  if(pending){toast('Aplique os campos editados antes de exportar o save.',true);return;}
  const button=document.querySelector('#export');button.disabled=true;
  try {
    const format=session.meta.can_export_save?'sav':'sqlite';
    const response=await fetch(`/api/saves/${session.id}/export?format=${format}`,{method:'POST'});
    if(!response.ok){const error=await response.json();throw new Error(error.detail);}
    const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=session.meta.filename.replace(/\.[^.]+$/,'')+`_editado.${format}`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    toast('Novo arquivo exportado e reaberto para verificação estrutural.');
  }catch(error){toast(error.message,true);}finally{button.disabled=false;}
}
document.querySelector('#export').onclick=exportSave;
window.addEventListener('beforeunload',event=>{if(pending){event.preventDefault();event.returnValue='';}});
try {await request('/api/health');document.querySelector('#api-state').textContent='online';if(session.id)await refreshState();}catch(error){document.querySelector('#api-state').textContent='sem sessão';session.id=null;localStorage.removeItem('f1-session');}
await navigate();

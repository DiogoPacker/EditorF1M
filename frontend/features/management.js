import {api, patch, session, escape as esc, number} from '../api.js';
import {lineChart} from '../charts.js';

export function headToHead(left = {}, right = {}) {
  return Object.keys(left).filter(key=>right[key]!=null).reduce((score,key)=>{
    if(left[key]<right[key])score[0]++;
    else if(right[key]<left[key])score[1]++;
    return score;
  },[0,0]);
}

export function managementFeature(context) {
  const {state,heading,field,currentTeam,teamOptions,mutate,navigate}=context;
  let comparison;

  async function facilities() {
    const data=await api(`/teams/${state.team}/facilities`);
    return heading('FACILITIES','Instalações',`${currentTeam().name} · níveis e conservação lidos do save.`)+`<div class="toolbar"><label>Equipe<select id="facilities-team">${teamOptions(state.team)}</select></label></div><div class="notice">${esc(data.note)}</div>`+(data.supported?`<div class="facility-grid">${data.facilities.map(item=>`<form class="panel facility-panel" data-facility="${item.BuildingType}"><h3>${esc(item.name)}</h3><span class="badge">${item.editable?'EM OPERAÇÃO':'OBRA EM ANDAMENTO'}</span><fieldset ${item.editable?'':'disabled'}><label class="form-field">Nível<select name="building_id">${item.levels.map(level=>`<option value="${level.BuildingID}" ${level.BuildingID===item.BuildingID?'selected':''}>Nível ${level.UpgradeLevel}</option>`).join('')}</select></label>${field('condition','Conservação (%)',item.condition,'number','min="0" max="100" step="0.1" required')}<div class="progress"><span style="width:${Math.min(100,item.condition)}%;background:${currentTeam().color}"></span></div><button class="button primary">Aplicar instalação</button></fieldset></form>`).join('')}</div>`:'');
  }

  function bindFacilities() {
    document.querySelector('#facilities-team').onchange=event=>context.selectTeam(Number(event.target.value));
    document.querySelectorAll('[data-facility]').forEach(form=>form.onsubmit=event=>{
      event.preventDefault();
      const data=new FormData(form);
      mutate(()=>patch(`/teams/${state.team}/facilities/${form.dataset.facility}`,{building_id:Number(data.get('building_id')),condition:Number(data.get('condition'))}),form);
    });
  }

  function identityForm() {
    const team=currentTeam();
    return `<div class="section-head"><h2>Identidade da equipe</h2></div><form class="panel" id="identity-form"><div class="form-grid">${field('name','Nome da equipe',team.name,'text','maxlength="80" required')}<label class="form-field">Cor da equipe<input type="color" name="color" value="${esc(team.color)}" ${team.color_editable?'':'disabled'}></label></div><p>Nome e cor vêm do arquivo importado. A edição grava o nome/localização e a cor principal disponíveis no banco; não altera logotipos ou pinturas empacotados no jogo.</p>${team.color_editable?'':'<p>Este save não contém uma tabela de cores editável compatível.</p>'}<button class="button primary">Aplicar identidade</button></form>`;
  }

  function bindIdentity() {
    const form=document.querySelector('#identity-form');
    if(form)form.onsubmit=event=>{
      event.preventDefault();
      const data=new FormData(form),edit={name:data.get('name')};
      if(data.has('color'))edit.color=data.get('color');
      mutate(()=>patch(`/teams/${state.team}/identity`,edit),form);
    };
  }

  async function teamComparison() {
    state.teamCompareMetric ||= 'points';
    state.teamCompareSeason ??= session.meta.season;
    state.teamAnnotations ??= true;
    comparison=await api(`/compare/teams?metric=${state.teamCompareMetric}&season=${state.teamCompareSeason}`);
    const valid=new Set(state.teams.map(team=>team.TeamID));
    state.compareTeamIds=(state.compareTeamIds??state.teams.slice(0,2).map(team=>team.TeamID)).filter(id=>valid.has(id));
    if(!state.compareTeamIds.length)state.compareTeamIds=[state.teams[0].TeamID];
    const picked=comparison.summary.filter(row=>state.compareTeamIds.includes(row.team.TeamID));
    const left=picked[0],right=picked[1];
    const stats=[['Corridas · melhor carro',...headToHead(left?.race_positions,right?.race_positions)],['Classificação · melhor carro',...(comparison.qualifying_supported?headToHead(left?.qualifying_positions,right?.qualifying_positions):['—','—'])],...Object.entries(comparison.metrics).map(([key,label])=>[label,left?.[key]??'—',right?.[key]??'—'])];
    const seasons=[...new Set([session.meta.season,session.meta.season+1,...(comparison.seasons??[])])];
    const seasonLabel=value=>value===session.meta.season?'Temporada atual':value===session.meta.season+1?'Próxima temporada':`Histórico · ${value}`;
    return heading('TEAM COMPARISON','Comparação entre equipes','Selecione as equipes e o indicador. As linhas mostram a progressão acumulada dos resultados do save.')+`<div class="toolbar"><label>Temporada<select id="team-compare-season">${seasons.map(value=>`<option value="${value}" ${value===state.teamCompareSeason?'selected':''}>${seasonLabel(value)}</option>`).join('')}</select></label><label>Gráfico<select id="team-compare-metric">${Object.entries(comparison.metrics).map(([key,label])=>`<option value="${key}" ${key===state.teamCompareMetric?'selected':''}>${esc(label)} acumulados</option>`).join('')}</select></label><label><input id="team-annotations" type="checkbox" ${state.teamAnnotations?'checked':''}> Anotações</label></div><div class="team-comparison-layout"><aside class="panel"><h3>Equipes no gráfico</h3><div class="team-picks">${state.teams.map(team=>`<label style="--color:${team.color}"><input type="checkbox" data-compare-team="${team.TeamID}" ${state.compareTeamIds.includes(team.TeamID)?'checked':''}><span style="color:${team.color}">${esc(team.name)}</span></label>`).join('')}</div><div class="h2h-heading"><b style="color:${left?.team.color??'#aaa'}">${esc(left?.team.name??'—')}</b><span>×</span><b style="color:${right?.team.color??'#aaa'}">${esc(right?.team.name??'Escolha outra equipe')}</b></div>${stats.map(([label,a,b])=>`<div class="h2h-stat"><span>${esc(label)}</span><div><b style="color:${left?.team.color??'#aaa'}">${a==='—'?'—':number(a)}</b><b style="color:${right?.team.color??'#aaa'}">${b==='—'?'—':number(b)}</b></div></div>`).join('')}<p>O resumo compara as duas primeiras equipes selecionadas. Corridas e classificação contam a melhor posição de cada equipe nas etapas em comum; empates não pontuam.</p></aside><section class="panel">${lineChart(comparison,{selected:state.compareTeamIds,annotations:state.teamAnnotations})}</section></div>`;
  }

  function bindTeamComparison() {
    for(const [selector,key] of [['#team-compare-season','teamCompareSeason'],['#team-compare-metric','teamCompareMetric'],['#team-annotations','teamAnnotations']]){
      document.querySelector(selector).onchange=event=>{state[key]=key==='teamAnnotations'?event.target.checked:key==='teamCompareSeason'?Number(event.target.value):event.target.value;navigate();};
    }
    document.querySelectorAll('[data-compare-team]').forEach(input=>input.onchange=()=>{
      const picked=[...document.querySelectorAll('[data-compare-team]:checked')].map(input=>Number(input.dataset.compareTeam));
      if(!picked.length){input.checked=true;return;}
      state.compareTeamIds=picked;navigate();
    });
  }
  return {facilities,bindFacilities,identityForm,bindIdentity,teamComparison,bindTeamComparison};
}

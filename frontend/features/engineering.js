import {api, patch, escape as esc, number} from '../api.js';
import {lineChart} from '../charts.js';


const engineLabels={power:'Potência',fuel:'Eficiência de combustível',durability:'Durabilidade do motor',ers:'Durabilidade do ERS',gearbox:'Durabilidade do câmbio'};
const engineBounds={power:[0,100],fuel:[0,100],durability:[0,100],ers:[0,100],gearbox:[0,100]};



export function performanceStep(value, direction, benefitDirection=1, step=10, min=0, max=1000) {
  return Math.min(max,Math.max(min,Number((value+direction*benefitDirection*step).toFixed(10))));
}

function bulkButtons() {
  return '<div class="piece-bulk"><button type="button" data-bulk-performance="-1" title="Piorar todos os atributos desta peça em 10 pontos brutos" aria-label="Piorar peça em 10 pontos por atributo">−</button><button type="button" data-bulk-performance="1" title="Melhorar todos os atributos desta peça em 10 pontos brutos" aria-label="Melhorar peça em 10 pontos por atributo">+</button></div>';
}

export function pieceInput(stat,part,mode='raw') {
  const integer=mode==='raw';
  const value=integer?stat.Value:stat.UnitValue;
  const unit=[7,8,9].includes(stat.PartStat)?'kN':stat.PartStat===15?'unid. internas':'%';
  return `<label class="fitted-stat"><span>${esc(stat.label)}<small>${integer?'Valor bruto · 0–1000':'Valor convertido · '+unit}</small><small class="converted-value">${number(stat.UnitValue,3)} ${unit}</small></span><input type="number" data-fitted-stat="${stat.PartStat}" data-design="${part.DesignID}" data-original="${value}" data-improve-direction="${stat.PartStat===15?-1:1}" data-bulk-step="${integer?10:(stat.maximum_unit-stat.minimum_unit)/100}" step="any" min="${integer?0:stat.minimum_unit}" max="${integer?1000:stat.maximum_unit}" value="${value}" aria-label="${esc(part.part+' · '+stat.label)}" ${stat.editable===false?'disabled title="Conversão do atributo não reconhecida neste save"':'required' }></label>`;
}


export function engineeringFeature(context) {
  const {state,heading,field,teamOptions,currentTeam,openDialog,mutate,navigate} = context;
  let catalog;
  let fitted;

  async function engines() {
    catalog=await api('/engines');
    return heading('POWER UNIT LAB','Motores e fornecedores','Edite o perfil, crie uma variação e selecione o fornecedor de cada equipe.',`<button id="new-engine" class="button primary" ${!(catalog.create_supported??catalog.supported)?'disabled':''}>＋ Criar perfil de motor</button>`) +
      `<div class="notice">${esc(catalog.note)}</div><div class="engine-grid">${catalog.engines.map(engine=>`<form class="panel engine-panel" data-engine-form="${engine.engineId}"><div class="engine-title"><span class="engine-symbol">PU</span><input name="name" aria-label="Nome do perfil" value="${esc(engine.name)}" required maxlength="60"></div>${Object.entries(engineLabels).map(([key,label])=>`<label class="engine-stat"><span>${label}<small>%</small></span><input name="${key}" type="number" step=".1" min="${engineBounds[key][0]}" max="${engineBounds[key][1]}" value="${engine.values[key]??''}" ${engine.values[key]==null?'disabled':'required'}><div class="progress"><span style="width:${engine.values[key]??0}%"></span></div></label>`).join('')}<p class="engine-clients">${engine.teams.map(team=>`<span style="color:${team.color}">${esc(team.code)}</span>`).join(' · ')||'Sem equipes vinculadas'}</p><button class="button secondary">Aplicar perfil e sincronizar clientes</button></form>`).join('')}</div><div class="section-head"><h2>Fornecedores por equipe</h2><small>MESMOS ITENS E DESGASTE, NOVOS ATRIBUTOS</small></div><div class="supplier-grid">${state.teams.map(team=>{const selected=catalog.engines.find(engine=>engine.teams.some(item=>item.TeamID===team.TeamID));return `<form class="supplier-row" data-allocation-form="${team.TeamID}" style="--color:${team.color}"><span class="team-emblem">${esc(team.code)}</span><b>${esc(team.name)}</b><select name="engine_id" ${catalog.allocation_supported===false?'disabled':''} aria-label="Motor de ${esc(team.name)}">${catalog.engines.map(engine=>`<option value="${engine.engineId}" ${engine.engineId===selected?.engineId?'selected':''}>${esc(engine.name)}</option>`).join('')}</select><button class="button ghost" ${catalog.allocation_supported===false?'disabled':''}>Aplicar fornecedor</button></form>`;}).join('')}</div>`;
  }

  function bindEngines() {
    const createButton=document.querySelector('#new-engine');
    if(createButton)createButton.onclick=()=>openDialog('Criar perfil de motor',`<div class="form-grid">${field('name','Nome do perfil','','text','required maxlength="60"')}<label class="form-field">Copiar atributos de<select name="base_engine">${catalog.engines.map(engine=>`<option value="${engine.engineId}">${esc(engine.name)}</option>`).join('')}</select></label></div><p>Cria um perfil nas tabelas compatíveis do save. Não adiciona uma nova marca nativa no jogo.</p>`,data=>api('/engines',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:data.get('name'),base_engine:Number(data.get('base_engine'))})}));
    document.querySelectorAll('[data-engine-form]').forEach(form=>form.onsubmit=event=>{event.preventDefault();mutate(()=>{const data=new FormData(form);const edit={name:data.get('name')};for(const key of Object.keys(engineLabels))if(data.has(key))edit[key]=Number(data.get(key));return patch(`/engines/${form.dataset.engineForm}`,edit);},form);});
    bindSuppliers();
  }

  function bindSuppliers() {
    document.querySelectorAll('[data-allocation-form]').forEach(form=>form.onsubmit=event=>{event.preventDefault();mutate(()=>patch(`/teams/${form.dataset.allocationForm}/engine`,{engine_id:Number(new FormData(form).get('engine_id'))}),form);});
  }

  async function teamSupplier() {
    const profiles=await api('/engines');
    if(!profiles.supported||profiles.allocation_supported===false)return '';
    const selected=profiles.engines.find(engine=>engine.teams.some(team=>team.TeamID===state.team));
    return `<div class="section-head"><h2>Unidade de potência</h2></div><form class="panel" data-allocation-form="${state.team}"><div class="form-grid"><label class="form-field">Fornecedor de ${esc(currentTeam().name)}<select name="engine_id">${profiles.engines.map(engine=>`<option value="${engine.engineId}" ${engine.engineId===selected?.engineId?'selected':''}>${esc(engine.name)}</option>`).join('')}</select></label></div><div class="form-actions"><button class="button primary">Aplicar fornecedor</button><small>Sincroniza motor, ERS e câmbio; preserva os itens e o desgaste.</small></div></form>`;
  }

  async function performance() {
    state.performanceTab ||= 'graph';
    state.metric = state.metric==='points'?'overall':state.metric||'overall';
    state.partUnits ||= 'raw';
    const [cars,history] = await Promise.all([api(`/performance?car=${state.car}`),api(`/performance/history?metric=${state.metric}`)]);
    const ranking=[...cars].sort((first,second)=>(second.metrics[state.metric]?.value??-Infinity)-(first.metrics[state.metric]?.value??-Infinity));
    const maximum=Math.max(1,...ranking.map(row=>row.metrics[state.metric]?.value??0));
    const tabs=`<div class="segmented"><button data-performance-tab="graph" class="${state.performanceTab==='graph'?'active':''}">⌁ Gráfico</button><button data-performance-tab="parts" class="${state.performanceTab==='parts'?'active':''}">⚙ Peças instaladas</button><button data-performance-tab="expertise" class="${state.performanceTab==='expertise'?'active':''}">Expertise</button><button id="go-engines">Motores ↗</button></div>`;
    const rail=`<aside class="performance-ranking">${ranking.map((row,index)=>`<button class="rank-row ${row.team.TeamID===state.team?'selected':''}" style="--color:${row.team.color}" data-rank-team="${row.team.TeamID}"><strong>${index+1}</strong><span><b>${esc(row.team.name)}</b><div class="progress"><span style="width:${Math.max(0,(row.metrics[state.metric]?.value??0)/maximum*100)}%"></span></div></span><small>${number(row.metrics[state.metric]?.value,2)} ${esc(row.metrics[state.metric]?.unit??'')}</small></button>`).join('')}<p>Ranking atual: peças instaladas no carro ${state.car}. A linha histórica usa designs concluídos, não o equipamento usado na corrida.</p></aside>`;
    let content;
    if(state.performanceTab==='expertise') {
      content=await expertiseView();
    } else if(state.performanceTab==='parts') {
      fitted=await api(`/teams/${state.team}/fitted?car=${state.car}`);
      content=`<div class="toolbar"><label>Edição <select id="piece-units"><option value="raw" ${state.partUnits==='raw'?'selected':''}>Valores brutos · 0–1000</option><option value="converted" ${state.partUnits==='converted'?'selected':''}>Avançado · unidades convertidas</option></select></label></div><form id="fitted-form"><div class="panel-title"><h2 style="color:${currentTeam().color}">${esc(currentTeam().name)} / carro ${state.car}</h2><button class="button primary">Aplicar peças alteradas</button></div><div class="notice compact">Edite valores decimais de 0 a 1000; o valor convertido aparece abaixo. Os botões da peça melhoram/pioram cada atributo em 10 pontos brutos, invertendo o sentido de peso/durabilidade. Campos não alterados preservam a precisão original do save. Se a mesma versão estiver nos dois carros, ambos recebem a alteração. O desgaste dos itens é preservado.</div><div class="fitted-grid">${fitted.parts.map(part=>`<section class="part-panel"><div class="part-title"><h3>${esc(part.part)}</h3>${bulkButtons()}<small>#${part.DesignID} · v${part.DesignNumber} · carro ${part.shared_cars.join(' / ')}</small></div>${part.stats.map(stat=>pieceInput(stat,part,state.partUnits)).join('')}</section>`).join('')}</div></form>`;
    } else {
      const selected=state.all?[]:[state.team,state.opponent];
      content=`<section class="panel performance-chart"><div class="panel-title"><h2>Evolução · ${esc(cars[0]?.metrics[state.metric]?.label??state.metric)}</h2><span class="badge accent">MODELO ESTIMADO</span></div>${lineChart(history,{selected,precision:3})}</section>`;
    }
    return heading('PERFORMANCE','O desenvolvimento do seu grid.','Ranking atual à esquerda. Evolução de designs e edição direta das peças à direita.',tabs)+`<div class="toolbar"><label>Atributo <select id="performance-metric">${[['overall','Índice geral estimado'],['top_speed','Velocidade máxima'],['low','Curvas baixas'],['medium','Curvas médias'],['high','Curvas altas'],['dirty_air','Ar sujo'],['tyres','Pneus'],['drs','DRS']].map(([key,label])=>`<option value="${key}" ${key===state.metric?'selected':''}>${label}</option>`).join('')}</select></label><label>Carro <select id="performance-car"><option value="1">1</option><option value="2" ${state.car===2?'selected':''}>2</option></select></label><label>Comparar com <select id="performance-opponent">${teamOptions(state.opponent)}</select></label><label><input type="checkbox" id="performance-all" ${state.all?'checked':''}> Grid completo</label></div><div class="performance-workspace">${rail}<div>${content}</div></div><div class="notice compact">Estimativas a partir do banco, sem acerto, pneus, combustível ou simulação de pista. O índice geral é uma composição dos atributos aerodinâmicos do editor; não é o overall oficial e não inclui potência do motor. Etapas futuras não recebem valores inventados.</div>`;
  }


  async function expertiseView() {
    state.expertiseTarget ||= 'current';
    const data=await api(`/teams/${state.team}/expertise-parts`);
    const column=state.expertiseTarget==='current'?'Expertise':'NextSeasonExpertise';
    return `<div class="toolbar"><label>Expertise<select id="expertise-target"><option value="current" ${state.expertiseTarget==='current'?'selected':''}>Temporada atual</option><option value="next" ${state.expertiseTarget==='next'?'selected':''}>Próxima temporada</option></select></label></div><div class="notice">${esc(data.note)}</div><div class="fitted-grid">${data.parts.map(part=>`<form class="panel part-panel" data-expertise-part="${part.part_type}"><div class="part-title"><h3>${esc(part.name)}</h3>${bulkButtons()}</div>${part.stats.map(stat=>`<label class="fitted-stat"><span>${esc(stat.label)}<small>0–1000 · ${state.expertiseTarget==='current'?'atual':'próxima'}</small></span><input type="number" name="stat-${stat.PartStat}" value="${stat[column]}" data-original="${stat[column]}" data-improve-direction="${stat.direction}" data-bulk-step="10" min="0" max="1000" step="any" required></label>`).join('')}<button class="button primary">Aplicar expertise da peça</button></form>`).join('')}</div>`;
  }

  function bindExpertise() {
    const target=document.querySelector('#expertise-target');
    if(target)target.onchange=async event=>{
      const previous=state.expertiseTarget;state.expertiseTarget=event.target.value;
      if(await navigate()===false){state.expertiseTarget=previous;event.target.value=previous;}
    };
    document.querySelectorAll('[data-expertise-part]').forEach(form=>form.onsubmit=event=>{
      event.preventDefault();
      mutate(()=>{
        const stats={};
        form.querySelectorAll('input[name^="stat-"]').forEach(input=>{if(Number(input.value)!==Number(input.dataset.original))stats[input.name.slice(5)]=Number(input.value);});
        if(!Object.keys(stats).length)throw new Error('Nenhum atributo foi alterado.');
        return patch(`/teams/${state.team}/expertise-parts/${form.dataset.expertisePart}`,{target:state.expertiseTarget,stats});
      },form);
    });
  }

  function bindBulkControls() {
    document.querySelectorAll('[data-bulk-performance]').forEach(button=>button.onclick=()=>{
      button.closest('.part-panel').querySelectorAll('input[data-improve-direction]').forEach(input=>{
        if(input.disabled)return;
        input.value=performanceStep(Number(input.value),Number(button.dataset.bulkPerformance),Number(input.dataset.improveDirection),Number(input.dataset.bulkStep),Number(input.min),Number(input.max));
        input.dispatchEvent(new Event('input',{bubbles:true}));
        input.dispatchEvent(new Event('change',{bubbles:true}));
      });
    });
  }

  function bindPerformance() {
    document.querySelectorAll('[data-performance-tab]').forEach(button=>button.onclick=()=>{state.performanceTab=button.dataset.performanceTab;navigate();});
    document.querySelector('#go-engines').onclick=()=>navigate('engines');
    for(const [selector,key] of [['#performance-metric','metric'],['#performance-car','car'],['#performance-opponent','opponent'],['#performance-all','all']])document.querySelector(selector).onchange=event=>{state[key]=key==='all'?event.target.checked:key==='metric'?event.target.value:Number(event.target.value);navigate();};
    document.querySelectorAll('[data-rank-team]').forEach(button=>button.onclick=()=>context.selectTeam(Number(button.dataset.rankTeam)));
    const units=document.querySelector('#piece-units');
    if(units)units.onchange=async event=>{const previous=state.partUnits;state.partUnits=event.target.value;const changed=await navigate();if(changed===false){state.partUnits=previous;event.target.value=previous;}};
    bindBulkControls();
    bindExpertise();
    const form=document.querySelector('#fitted-form');
    if(form)form.onsubmit=event=>{event.preventDefault();mutate(()=>{
      const stats=[...form.querySelectorAll('[data-fitted-stat]')].filter(input=>Number(input.value)!==Number(input.dataset.original)).map(input=>({design_id:Number(input.dataset.design),stat_id:Number(input.dataset.fittedStat),value:Number(input.value)}));
      if(!stats.length)throw new Error('Nenhum atributo foi alterado.');
      return patch(`/teams/${state.team}/fitted?car=${state.car}`,{units:state.partUnits,stats});
    },form);};
  }
  return {engines,bindEngines,performance,bindPerformance,teamSupplier,bindSuppliers,expertiseView,bindExpertisePage:()=>{bindExpertise();bindBulkControls();}};
}

import {api, session, escape as esc, money} from '../api.js';

export function contractHubMarkup(driver, teams, season, field) {
  const teamName = contract => teams.find(team=>team.TeamID===contract.TeamID)?.name ?? contract.TeamName ?? 'Equipe';
  const role = contract => Number(contract.PosInTeam)>2 ? 'Academia' : `Carro ${contract.PosInTeam}`;
  const cards = (contracts, future) => contracts.length ? contracts.map(contract=>`<article class="hub-contract"><div><b>${esc(teamName(contract))}</b><span>${esc(role(contract))} · ${future?season+1:season} até ${contract.EndSeason}</span><small>Salário anual ${money(contract.Salary)} · bônus ${money(contract.RaceBonus)}</small></div><button type="button" class="button ghost" data-hub-edit="${contract.contract_id}" data-hub-future="${future}">Editar contrato</button></article>`).join('') : `<p>${future?'Nenhum contrato futuro assinado.':'Sem vínculo atual.'}</p>`;
  const future=driver.future_contracts?.find(contract=>teams.some(team=>team.TeamID===contract.TeamID));
  const current=driver.affiliations?.find(contract=>Number(contract.Formula)===1)??driver.contract;
  const initial=future??current;
  return `<div class="hub-contracts"><section><h3>Vínculos atuais · ${season}</h3>${cards(driver.affiliations??[],false)}</section><section><h3>Próxima temporada · ${season+1}</h3>${cards(driver.future_contracts??[],true)}</section></div><h3>Definir equipe e função</h3><div class="form-grid"><label class="form-field">Quando<select name="timing"><option value="next">Próxima temporada · ${season+1}</option><option value="now">Imediatamente · ${season}</option></select></label><label class="form-field">Equipe<select name="team_id">${teams.map(team=>`<option value="${team.TeamID}" ${team.TeamID===initial?.TeamID?'selected':''}>${esc(team.name)}</option>`).join('')}</select></label><label class="form-field">Função<select name="role"><option value="1" ${Number(initial?.PosInTeam)===1?'selected':''}>Titular · carro 1</option><option value="2" ${Number(initial?.PosInTeam)===2?'selected':''}>Titular · carro 2</option><option value="academy" ${Number(initial?.PosInTeam)>2?'selected':''}>Academia</option></select></label>${field('salary','Salário anual ($)',initial?.Salary??1000000,'number','required min="0" max="1000000000" step="1"')}${field('end_season','Contrato até',Math.max(season+1,initial?.EndSeason??0),'number',`required min="${season+1}" max="2100" step="1"`)}</div><p>Na próxima temporada, o vínculo atual é mantido até o fim deste ano. Uma vaga ocupada exige conferir quem sai. Na academia, o vínculo de F2/F3 é preservado.</p><button type="button" class="button secondary" id="hub-preview">Conferir novo contrato</button><div id="hub-preview-result" aria-live="polite"></div>`;
}

export function openContractHub(driver, context, editContract) {
  const {state,field,openDialog}=context;
  let confirmed=null;
  function payload(data) {
    const common={driver_id:driver.StaffID,team_id:Number(data.get('team_id')),timing:data.get('timing'),salary:Number(data.get('salary')),end_season:Number(data.get('end_season'))};
    return data.get('role')==='academy'?{...common,keep_feeder_seat:true}:{...common,seat:Number(data.get('role')),displaced:'release'};
  }
  openDialog(`${driver.name} · Hub de contratos`,contractHubMarkup(driver,state.teams,session.meta.season,field),async data=>{
    const edit=payload(data);
    if(!confirmed||confirmed.signature!==JSON.stringify(edit))throw new Error('Confira o novo contrato antes de aplicar.');
    if('seat' in edit)await api('/transfers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...edit,expected_outgoing:confirmed.outgoing})});
    else {const {team_id,...body}=edit;await api(`/teams/${team_id}/academy`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});}
  });
  const form=document.querySelector('#modal-form');
  form.querySelectorAll('[data-hub-edit]').forEach(button=>button.onclick=()=>editContract(Number(button.dataset.hubEdit),driver.StaffID,button.dataset.hubFuture==='true'));
  form.addEventListener('input',()=>{confirmed=null;form.querySelector('#hub-preview-result').textContent='Campos alterados. Confira novamente antes de aplicar.';});
  form.querySelector('#hub-preview').onclick=async()=>{
    const result=form.querySelector('#hub-preview-result');
    confirmed=null;
    if(!form.reportValidity())return;
    const edit=payload(new FormData(form)),signature=JSON.stringify(edit);
    try {
      let outgoing=null,message;
      if('seat' in edit){
        const response=await api('/transfers/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(edit)});
        outgoing=response.outgoing?.StaffID??null;
        message=`${driver.name} → ${response.team.name}, carro ${edit.seat}, em ${response.year}. Sai da vaga: ${response.outgoing?.name??'ninguém'}. ${response.message}`;
      } else message=`${driver.name} → academia ${state.teams.find(team=>team.TeamID===edit.team_id)?.name}, em ${session.meta.season+(edit.timing==='next'?1:0)}, até ${edit.end_season}. Não ocupa uma vaga de titular. Mantém eventual vaga em F2/F3.`;
      if(JSON.stringify(payload(new FormData(form)))!==signature)return;
      confirmed={signature,outgoing};
      result.innerHTML=`<div class="notice">${esc(message)}</div>`;
    }catch(error){result.textContent=error.message;}
  };
}

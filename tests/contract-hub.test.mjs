import test from 'node:test';
import assert from 'node:assert/strict';
import {contractHubMarkup, openContractHub} from '../frontend/features/contract-hub.js';
import {session} from '../frontend/api.js';

const teams=[{TeamID:1,name:'Ferrari'},{TeamID:3,name:'Red Bull'}];
const driver={StaffID:90,name:'Rafael Câmara',affiliations:[{contract_id:1,TeamID:1,Formula:1,PosInTeam:5,EndSeason:2026,Salary:100000,RaceBonus:0}],future_contracts:[{contract_id:2,TeamID:3,PosInTeam:2,EndSeason:2029,Salary:2000000,RaceBonus:0}]};
const field=(name,label,value)=>`<input name="${name}" value="${value}">`;

test('hub shows current academy and future race seat with destination and years',()=>{
  const html=contractHubMarkup(driver,teams,2026,field);
  assert.match(html,/Academia · 2026 até 2026/);
  assert.match(html,/Carro 2 · 2027 até 2029/);
  assert.match(html,/Red Bull/);
  assert.match(html,/value="3" selected/);
  assert.match(html,/value="2" selected/);
  assert.match(html,/data-hub-edit="1"/);
  assert.match(html,/data-hub-edit="2"/);
});

test('free drivers can also configure future seats and academy',()=>{
  const html=contractHubMarkup({name:'Livre',affiliations:[],future_contracts:[]},teams,2026,field);
  assert.match(html,/Sem vínculo atual/);
  assert.match(html,/Nenhum contrato futuro/);
  assert.match(html,/Titular · carro 1/);
  assert.match(html,/Titular · carro 2/);
  assert.match(html,/value="academy"/);
});

test('hub refuses applying a new contract without checking its preview',async()=>{
  session.meta={season:2026};
  let operation;
  const previous=globalThis.document;
  globalThis.document={querySelector:()=>({querySelectorAll:()=>[],addEventListener:()=>{},querySelector:()=>({})})};
  try {
    openContractHub(driver,{state:{teams},field,openDialog:(_title,_html,callback)=>operation=callback},()=>{});
    const data=new Map(Object.entries({team_id:'3',timing:'next',salary:'2000000',end_season:'2029',role:'2'}));
    await assert.rejects(()=>operation(data),/Confira o novo contrato/);
  }finally{globalThis.document=previous;}
});

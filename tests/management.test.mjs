import test from 'node:test';
import assert from 'node:assert/strict';
import {session} from '../frontend/api.js';
import {managementFeature,headToHead} from '../frontend/features/management.js';
import {engineeringFeature,performanceStep,pieceInput} from '../frontend/features/engineering.js';

const teams=[{TeamID:45,name:'Fiction Racing',color:'#123abc',code:'FR',color_editable:true},{TeamID:98,name:'Other Fiction',color:'#ef1234',code:'OF'}];
const context=()=>({state:{teams,team:45,car:1,performanceTab:'expertise'},heading:(_tag,title,note)=>`<h1>${title}</h1>${note}`,field:(name,label,value)=>`<label>${label}<input type="number" name="${name}" value="${value}"></label>`,currentTeam:()=>teams[0],teamOptions:()=>'<option value="45">Fiction Racing</option>',navigate:()=>{},mutate:()=>{},openDialog:()=>{},selectTeam:()=>{}});

session.id='fixture';session.meta={season:1888};
globalThis.fetch=async url=>{
  let body;
  if(url.endsWith('/facilities'))body={supported:true,note:'From save',facilities:[{BuildingType:7,name:'Fiction Facility',BuildingID:501,condition:78.5,editable:true,levels:[{BuildingID:501,UpgradeLevel:1},{BuildingID:502,UpgradeLevel:2}]}]};
  else if(url.endsWith('/expertise-parts'))body={parts:[{part_type:3,name:'Chassi',stats:[{PartStat:4,label:'Arrasto',Expertise:500.25,NextSeasonExpertise:450.5,direction:1},{PartStat:15,label:'Peso',Expertise:300.75,NextSeasonExpertise:290.5,direction:-1}]}],note:'Development expertise'};
  else if(url.includes('/compare/teams'))body={seasons:[1888,1887],metrics:{points:'Pontos',wins:'Vitórias',podiums:'Pódios',poles:'Poles',dnfs:'Abandonos'},labels:['Race A','Race B'],series:teams.map((team,i)=>({id:team.TeamID,name:team.name,color:team.color,values:[i+1,i+5]})),summary:teams.map(team=>({team,points:5,wins:1,podiums:2,poles:1,dnfs:0,race_positions:{1:1},qualifying_positions:{1:1}})),qualifying_supported:true,note:'Recorded results'};
  else if(url.includes('/performance/history'))body={labels:[],series:[],note:''};
  else if(url.includes('/performance?'))body=teams.map(team=>({team,metrics:{overall:{value:70,label:'Index',unit:'%'}}}));
  else throw new Error('Unexpected URL '+url);
  return {ok:true,json:async()=>body};
};

test('piece improvements use ten raw points, preserve floats and reverse weight',()=>{
  assert.equal(performanceStep(500.25,1),510.25);
  assert.equal(performanceStep(300.75,1,-1),290.75);
  assert.equal(performanceStep(300.75,-1,-1),310.75);
  assert.equal(performanceStep(995,1),1000);
  assert.equal(performanceStep(3,1,-1),0);
  assert.equal(performanceStep(50,1,1,1,0,100),51);
  const html=pieceInput({PartStat:15,Value:300.75,UnitValue:4000,label:'Peso',minimum_unit:2000,maximum_unit:5000},{DesignID:1,part:'Chassi'});
  assert.match(html,/data-improve-direction="-1"/);
  assert.match(html,/value="300.75"/);
});

test('expertise panels expose current/next seasons and per-piece bulk controls',async()=>{
  const ctx=context();
  const html=await engineeringFeature(ctx).performance();
  assert.match(html,/Temporada atual/);
  assert.match(html,/Próxima temporada/);
  assert.match(html,/data-bulk-performance="1"/);
  assert.match(html,/data-bulk-performance="-1"/);
  assert.match(html,/value="500.25"/);
  assert.ok(!html.includes('2026')&&!html.includes('2027'));
  ctx.state.expertiseTarget='next';
  assert.match(await engineeringFeature(ctx).performance(),/value="450.5"/);
});

test('facilities expose actual levels and decimal condition',async()=>{
  const html=await managementFeature(context()).facilities();
  assert.match(html,/Fiction Facility/);
  assert.match(html,/value="502"/);
  assert.match(html,/value="78.5"/);
});

test('team comparison provides metric choice, annotations and selected team lines',async()=>{
  const html=await managementFeature(context()).teamComparison();
  for(const label of ['Temporada atual','Próxima temporada','Anotações','Vitórias','Pódios','Poles','Abandonos'])assert.ok(html.includes(label));
  assert.match(html,/stroke="#123abc"/);
  assert.match(html,/chart-annotation/);
  assert.ok(!html.includes('NaN'));
});

test('head to head counts only shared races and excludes ties',()=>{
  assert.deepEqual(headToHead({1:1,2:3,3:4,4:1},{1:2,2:1,3:4}),[1,1]);
  assert.deepEqual(headToHead(),[0,0]);
});

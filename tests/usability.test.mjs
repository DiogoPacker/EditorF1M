import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';

globalThis.localStorage={getItem:()=>null};
const {driverGroup,sortedDrivers,driverOptions}=await import('../frontend/drivers.js');
const {parseDriverDrag,bindDriverDrag,driverDragType}=await import('../frontend/features/drag.js');
const {pieceInput}=await import('../frontend/features/engineering.js');
const {normalizeFontScale}=await import('../frontend/preferences.js');

const driver=(StaffID,average,Formula,PosInTeam=1)=>({StaffID,name:'Piloto '+StaffID,average,Retired:0,contract:Formula?{Formula,PosInTeam}:null});

test('default order is F1, academy, F2, F3, free; academy wins over feeder role',()=>{
  const academy=driver(2,95,2);
  academy.affiliations=[{Formula:2,PosInTeam:1},{Formula:1,PosInTeam:8}];
  const list=[driver(5,99,null),driver(4,80,3),academy,driver(3,96,2),driver(1,70,1)];
  assert.equal(driverGroup(academy),1);
  assert.deepEqual(sortedDrivers(list).map(item=>item.StaffID),[1,2,3,4,5]);
  assert.deepEqual(sortedDrivers(list,'overall-desc').map(item=>item.StaffID),[5,3,2,4,1]);
  assert.deepEqual(sortedDrivers(list,'overall-asc').map(item=>item.StaffID),[1,4,2,3,5]);
  assert.deepEqual(list.map(item=>item.StaffID),[5,4,2,3,1]);
});

test('unknown overall sorts last and retired drivers are excluded',()=>{
  const list=[driver(1,null,1),driver(2,90,1),{...driver(3,99,1),Retired:1}];
  assert.deepEqual(sortedDrivers(list,'overall-desc').map(item=>item.StaffID),[2,1]);
  assert.deepEqual(sortedDrivers(list,'overall-asc').map(item=>item.StaffID),[2,1]);
  assert.ok(driverOptions(list,2).includes('<optgroup'));
});

test('category and overall sorting accept numeric strings from imported data',()=>{
  const list=[driver(1,'80','1','1'),driver(2,'95','1','2'),driver(3,'99','2','1')];
  list.forEach(row=>row.Retired='0');
  assert.deepEqual(sortedDrivers(list).map(row=>row.StaffID),[2,1,3]);
  assert.deepEqual(sortedDrivers(list,'overall-desc').map(row=>row.StaffID),[3,2,1]);
});

test('drag payload requires a known source, driver, team and seat',()=>{
  assert.equal(parseDriverDrag('{bad'),null);
  assert.equal(parseDriverDrag(JSON.stringify({driverId:1,source:'seat',teamId:3,seat:9})),null);
  assert.equal(parseDriverDrag(JSON.stringify({driverId:1,source:'academy'})),null);
  assert.deepEqual(parseDriverDrag(JSON.stringify({driverId:1,source:'entry'})),{driverId:1,source:'entry'});
});

test('drag/drop dispatches to seat, academy and entry without applying an edit',()=>{
  for(const targetKind of ['seat','academy','entry']) {
    const handlers={},dragHandlers={},calls=[],storage=new Map();
    const classes={add:()=>{},remove:()=>{}};
    const element={dataset:{dragDriver:'42',dragSource:'academy',dragTeam:'3'},classList:classes,addEventListener:(name,handler)=>dragHandlers[name]=handler};
    const root={querySelectorAll:selector=>selector==='[data-drag-driver]'?[element]:[],addEventListener:(name,handler)=>handlers[name]=handler};
    bindDriverDrag(root,{select:id=>calls.push(['select',id]),dropSeat:(...args)=>calls.push(['seat',...args]),dropAcademy:(...args)=>calls.push(['academy',...args]),dropEntry:(...args)=>calls.push(['entry',...args])});
    const transfer={types:[driverDragType],setData:(type,value)=>storage.set(type,value),getData:type=>storage.get(type)};
    dragHandlers.dragstart({dataTransfer:transfer});
    const target={dataset:{seatDrop:'2',dropTeam:'4',academyDrop:'4'},classList:classes,closest(){return this;},hasAttribute:name=>name===`data-${targetKind}-drop`};
    let prevented=false;
    handlers.drop({target,dataTransfer:transfer,preventDefault:()=>prevented=true});
    assert.ok(prevented);
    assert.equal(calls.at(-1)[0],targetKind);
    assert.equal(calls.at(-1).at(-1).driverId,42);
    assert.equal(calls.at(-1).at(-1).teamId,3);
  }
});

test('integer piece input does not expose decimals or silently flag untouched precision',()=>{
  const stat={PartStat:9,Value:473.5,UnitValue:7.4706394,label:'Downforce',minimum_unit:6.9,maximum_unit:8.1};
  const part={DesignID:111,part:'Assoalho'};
  const html=pieceInput(stat,part);
  assert.ok(html.includes('step="1"'));
  assert.ok(html.includes('value="474"'));
  assert.ok(html.includes('data-original="474"'));
  assert.ok(html.includes('min="0" max="1000"'));
  assert.ok(pieceInput(stat,part,'converted').includes('value="7.4706394"'));
  assert.equal(stat.Value,473.5);
});

test('font preference is bounded and invalid preferences return the default',()=>{
  assert.equal(normalizeFontScale(null),1);
  assert.equal(normalizeFontScale('1.2'),1.2);
  assert.equal(normalizeFontScale('NaN'),1);
  assert.equal(normalizeFontScale('99'),1);
});

test('advanced design and database views are no longer navigation entries',()=>{
  const source=readFileSync('frontend/app.js','utf8');
  const pages=source.match(/const pages = ([^\n]+);/)[1];
  assert.ok(!pages.includes("['parts',"));
  assert.ok(!pages.includes("['database',"));
});

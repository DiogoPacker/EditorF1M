import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import test from 'node:test';

globalThis.localStorage = {getItem:()=>null};
const {session,escape:esc} = await import('../frontend/api.js');
const {gridFeature} = await import('../frontend/features/grid.js');
const {comparisonFeature} = await import('../frontend/features/comparison.js');
const {recordsFeature} = await import('../frontend/features/records.js');
const {engineeringFeature} = await import('../frontend/features/engineering.js');
const {sortedDrivers} = await import('../frontend/drivers.js');
const hasFixture=existsSync('work/ui-fixture.json');
const fixture=hasFixture?JSON.parse(readFileSync('work/ui-fixture.json','utf8')):{};
globalThis.fetch=async url=>{
  if(!(url in fixture))throw new Error(`Missing fixture: ${url}`);
  return {ok:true,json:async()=>structuredClone(fixture[url])};
};
session.id='fixture';
session.meta={season:2026};

function context() {
  const state={team:3,teams:fixture['/api/saves/fixture/teams'],drivers:fixture['/api/saves/fixture/drivers'],compareLeft:1,compareRight:10,car:1,metric:'overall',all:true,opponent:4};
  return {state,heading:(tag,title,description,right='')=>`<h1>${esc(title)}</h1>${esc(description)}${right}`,field:(name,label,value)=>`<input name="${name}" value="${esc(value)}">`,currentTeam:()=>state.teams.find(team=>team.TeamID===state.team),teamOptions:()=>'<option>Team</option>',navigate:()=>{},mutate:()=>{},openDialog:()=>{},selectTeam:()=>{}};
}

test('grid and lineups render all teams and contracts',{skip:!hasFixture},async()=>{
  const ctx=context(),screen=gridFeature(ctx);
  const rows=await screen.view();
  assert.equal((rows.match(/class="roster-row"/g)||[]).length,11);
  assert.ok(rows.includes('AlphaTauri')&&rows.includes('Cadillac'));
  assert.ok(rows.includes('data-edit-contract'));
  ctx.state.lineup=true;
  assert.equal(((await screen.view()).match(/class="lineup-card"/g)||[]).length,11);
});

test('comparison renders paired attributes and two radar polygons',{skip:!hasFixture},async()=>{
  const html=await comparisonFeature(context()).view();
  assert.ok(html.includes('Lewis Hamilton')&&html.includes('Max Verstappen'));
  assert.equal((html.match(/<polygon points=/g)||[]).length,2);
  assert.ok(html.includes('Frenagem')&&html.includes('Crescimento'));
  assert.ok(html.includes('COMPARAÇÃO EM LINHAS'));
  assert.ok(html.includes('aria-label="Comparação de atributos dos pilotos em linhas"'));
  assert.ok((html.match(/stroke-width="2.5"/g)||[]).length >= 16);
  assert.ok(!html.includes('paired-bar'));
});

test('comparison initially chooses the best two and preserves selection when sorting changes',{skip:!hasFixture},async()=>{
  const ctx=context();
  delete ctx.state.compareLeft;
  delete ctx.state.compareRight;
  const best=sortedDrivers(ctx.state.drivers,'overall-desc');
  const screen=comparisonFeature(ctx);
  await screen.view();
  assert.equal(ctx.state.compareLeft,best[0].StaffID);
  assert.equal(ctx.state.compareRight,best[1].StaffID);
  ctx.state.driverSort='overall-asc';
  await screen.view();
  assert.equal(ctx.state.compareLeft,best[0].StaffID);
  assert.equal(ctx.state.compareRight,best[1].StaffID);
});

test('records render both main and sprint columns',{skip:!hasFixture},async()=>{
  const html=await recordsFeature(context()).view();
  assert.ok(html.includes('Records Hub'));
  assert.ok(html.includes('class="sticky-driver"'));
  assert.ok(html.includes('total-points'));
  assert.ok(!html.includes('[STRING_LITERAL'));
});

test('engine profiles and supplier selectors are available',{skip:!hasFixture},async()=>{
  const screen=engineeringFeature(context());
  const html=await screen.engines();
  assert.ok(html.includes('Criar perfil de motor'));
  assert.equal((html.match(/data-allocation-form=/g)||[]).length,11);
  assert.ok(html.includes('data-engine-form'));
  assert.ok((await screen.teamSupplier()).includes('data-allocation-form="3"'));
});

test('performance has ranking, lines and current fitted editors',{skip:!hasFixture},async()=>{
  const ctx=context(),screen=engineeringFeature(ctx);
  const graph=await screen.performance();
  assert.equal((graph.match(/data-rank-team=/g)||[]).length,11);
  assert.ok(graph.includes('ÚLTIMO GP'));
  ctx.state.performanceTab='parts';
  const parts=await screen.performance();
  assert.equal((parts.match(/class="part-panel"/g)||[]).length,6);
  assert.ok(parts.includes('data-fitted-stat'));
  assert.ok(!parts.includes('NaN'));
});

import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.localStorage = {getItem: () => null};
const {lineChart, radar} = await import('../frontend/charts.js');
const {escape} = await import('../frontend/api.js');

test('chart keeps team color and escapes labels', () => {
  const markup = lineChart({labels:['Bahrain', '<script>'], series:[{id:3,name:'Red Bull <Racing>',color:'#5285ff',values:[1,5]}],note:'Real results'});
  assert.ok(markup.includes('stroke="#5285ff"'));
  assert.ok(markup.includes('Red Bull &lt;Racing&gt;'));
  assert.ok(!markup.includes('<script>'));
  assert.equal((markup.match(/<circle /g) || []).length, 2);
});

test('missing points do not produce invented connecting segments', () => {
  const markup = lineChart({labels:['A','B','C'],series:[{id:1,name:'Ferrari',color:'#ed3947',values:[10,null,20]}],note:''});
  assert.equal((markup.match(/stroke-width="2.5"/g) || []).length, 0);
  assert.equal((markup.match(/<circle /g) || []).length, 2);
});

test('selected teams filter and empty state', () => {
  const markup = lineChart({labels:['A'],series:[{id:1,name:'Ferrari',color:'#ed3947',values:[10]},{id:3,name:'Red Bull',color:'#5285ff',values:[12]}],note:''},{selected:[3]});
  assert.ok(!markup.includes('Ferrari'));
  assert.ok(markup.includes('Red Bull'));
  assert.ok(lineChart({labels:[],series:[],note:''}).includes('Sem histórico'));
});

test('radar requires enough attributes and encodes labels', () => {
  assert.equal(radar([]), '');
  const markup=radar([{Val:80,label:'Curvas'},{Val:90,label:'Frenagem'},{Val:70,label:'<Controle>'}]);
  assert.ok(markup.includes('class="shape"'));
  assert.ok(markup.includes('&lt;Controle&gt;'));
  assert.equal(escape('"<&'), '&quot;&lt;&amp;');
});

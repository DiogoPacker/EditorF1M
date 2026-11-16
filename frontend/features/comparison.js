import {api, escape as esc, number} from '../api.js';
import {lineChart} from '../charts.js';
import {driverOptions, sortedDrivers, sortControl} from '../drivers.js';


export function comparisonFeature(context) {
  const {state,heading,navigate} = context;
  const options = selected => driverOptions(state.drivers,selected,state.driverSort);

  async function view() {
    state.driverSort ||= 'category';
    const best=sortedDrivers(state.drivers,'overall-desc');
    if(!best.length)return heading('HEAD TO HEAD','Comparação de atributos','Não há pilotos ativos disponíveis neste save.');
    if(!best.some(driver=>driver.StaffID===state.compareLeft))state.compareLeft=best[0].StaffID;
    if(!best.some(driver=>driver.StaffID===state.compareRight))state.compareRight=best.find(driver=>driver.StaffID!==state.compareLeft)?.StaffID??best[0].StaffID;
    const {left,right} = await api(`/compare/drivers?left=${state.compareLeft}&right=${state.compareRight}`);
    const leftColor=left.team?.color??'#b2a1ff',rightColor=right.team?.color??'#69dbc5';
    const rightStats=new Map(right.stats.map(stat=>[stat.StatID,stat]));
    const stats=left.stats.filter(stat=>rightStats.has(stat.StatID));
    const other=[['Crescimento',left.Improvability,right.Improvability],['Agressividade',left.Aggression,right.Aggression],['Valor de mercado',left.Marketability,right.Marketability]];
    const values=(label,first,second)=>`<div class="attribute-compare"><div><b>${esc(label)}</b><span style="color:${leftColor}">${number(first)}</span><span style="color:${rightColor}">${number(second)}</span></div><small>${first===second?'Empate':(first>second?esc(left.last_name_display):esc(right.last_name_display))+' +'+number(Math.abs(first-second))}</small></div>`;
    const chart=(labels,leftValues,rightValues)=>lineChart({title:'Comparação de atributos dos pilotos em linhas',labels,series:[{id:left.StaffID,name:left.name,color:leftColor,values:leftValues},{id:right.StaffID,name:right.name,color:rightColor,values:rightValues}],note:'Cada ponto é um atributo, não uma etapa no tempo. Escala de 0 a 100.'},{minimum:0,maximum:100});
    return heading('HEAD TO HEAD','Comparação de atributos','Dois pilotos, os mesmos critérios. Valores reais do banco, sem alterar o save nesta tela.') +
      `<div class="comparison-sort">${sortControl('comparison-sort',state.driverSort)}<small>Seleção inicial: os dois melhores pela média dos atributos. Depois, sua escolha é mantida.</small></div><div class="compare-selectors"><select id="compare-left" aria-label="Primeiro piloto">${options(state.compareLeft)}</select><span>VS</span><select id="compare-right" aria-label="Segundo piloto">${options(state.compareRight)}</select></div><div class="comparison-hero" style="--left:${leftColor};--right:${rightColor}"><div><small>${esc(left.team?.name??'SEM EQUIPE F1')}</small><h2>${esc(left.name)}</h2><b>${number(left.average,1)}</b></div><span>ATRIBUTOS<br><small>MÉDIA SIMPLES</small></span><div><small>${esc(right.team?.name??'SEM EQUIPE F1')}</small><h2>${esc(right.name)}</h2><b>${number(right.average,1)}</b></div></div><section class="panel"><div class="panel-title"><h2>Atributos de pilotagem</h2><span class="badge">COMPARAÇÃO EM LINHAS</span></div><div class="comparison-layout"><div class="attribute-comparison-chart">${chart(stats.map(stat=>stat.label),stats.map(stat=>stat.Val),stats.map(stat=>rightStats.get(stat.StatID).Val))}</div><div class="comparison-radar">${radarCompare(stats,rightStats,leftColor,rightColor)}<div class="chart-legend"><span style="color:${leftColor}">● ${esc(left.code_display)}</span><span style="color:${rightColor}">● ${esc(right.code_display)}</span></div></div></div><div class="attribute-grid">${stats.map(stat=>values(stat.label,stat.Val,rightStats.get(stat.StatID).Val)).join('')}</div><div class="section-head"><h2>Outros atributos</h2></div>${chart(other.map(row=>row[0]),other.map(row=>row[1]),other.map(row=>row[2]))}<div class="attribute-grid">${other.map(row=>values(...row)).join('')}</div></section>`;
  }

  function bind() {
    for(const [selector,key] of [['#compare-left','compareLeft'],['#compare-right','compareRight']]) {const element=document.querySelector(selector);if(element)element.onchange=event=>{state[key]=Number(event.target.value);navigate();};}
    const order=document.querySelector('#comparison-sort');if(order)order.onchange=event=>{state.driverSort=event.target.value;navigate();};
  }
  return {view,bind};
}

export function radarCompare(stats,rightStats,leftColor,rightColor) {
  const center=140,radius=90;
  const point=(index,ratio)=>{const angle=index/stats.length*2*Math.PI-Math.PI/2;return [center+Math.cos(angle)*radius*ratio,center+Math.sin(angle)*radius*ratio];};
  let svg='<svg viewBox="0 0 280 280" class="radar" role="img" aria-label="Radar comparativo de pilotos">';
  for(const ratio of [.25,.5,.75,1])svg+=`<polygon class="grid" points="${stats.map((_,index)=>point(index,ratio).join(',')).join(' ')}"/>`;
  for(const [color,values] of [[leftColor,stats],[rightColor,stats.map(stat=>rightStats.get(stat.StatID))]])svg+=`<polygon points="${values.map((stat,index)=>point(index,stat.Val/100).join(',')).join(' ')}" fill="${esc(color)}" fill-opacity=".12" stroke="${esc(color)}" stroke-width="2"/>`;
  stats.forEach((stat,index)=>{const location=point(index,1.25);svg+=`<text x="${location[0]}" y="${location[1]}" text-anchor="middle">${esc(stat.label.slice(0,3).toUpperCase())}</text>`;});
  return svg+'</svg>';
}

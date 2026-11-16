import {escape, number} from './api.js';

export function lineChart(data, {selected = [], precision = 0, minimum, maximum, annotations = false} = {}) {
  const series = data.series.filter(item => !selected.length || selected.includes(item.id));
  const values = series.flatMap(item => item.values).filter(value => value != null);
  if (!values.length) return '<div class="notice">Sem histórico disponível para esta seleção.</div>';
  const width = 1080, height = 380, left = 72, right = 1010, top = 20, bottom = 315;
  let low = precision ? Math.min(...values) * .98 : Math.min(0, ...values);
  let high = Math.max(...values);
  if(Number.isFinite(minimum))low=minimum;
  if(Number.isFinite(maximum))high=maximum;
  if (high <= low) high = low + 1;
  const horizontal = index => left + index / Math.max(1, data.labels.length - 1) * (right - left);
  const vertical = value => bottom - (value - low) / (high - low) * (bottom - top);
  let svg = `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(data.title ?? 'Gráfico de evolução das equipes')}">`;
  for (let index = 0; index <= 5; index++) {
    const value = low + (high - low) * index / 5;
    svg += `<line class="grid" x1="${left}" x2="${right}" y1="${vertical(value)}" y2="${vertical(value)}"/><text x="${left - 12}" y="${vertical(value) + 4}" text-anchor="end">${number(value, precision)}</text>`;
  }
  data.labels.forEach((label, index) => {
    if (index % Math.max(1, Math.ceil(data.labels.length / 12)) === 0 || index === data.labels.length - 1)
      svg += `<text transform="translate(${horizontal(index)},338) rotate(-25)" text-anchor="end">${escape(label)}</text>`;
  });
  if (data.current_index != null && data.current_index >= 0) {
    const current = horizontal(data.current_index);
    svg += `<line x1="${current}" x2="${current}" y1="${top}" y2="${bottom}" stroke="#d6ba6a" stroke-dasharray="5 5"/><text x="${current + 6}" y="${top + 12}">ÚLTIMO GP</text>`;
  }
  for (const item of series) {
    let previous = null;
    item.values.forEach((value, index) => {
      if (value == null) {previous = null; return;}
      const point = [horizontal(index), vertical(value)];
      if (previous) svg += `<line x1="${previous[0]}" y1="${previous[1]}" x2="${point[0]}" y2="${point[1]}" stroke="${escape(item.color)}" stroke-width="2.5"/>`;
      svg += `<circle cx="${point[0]}" cy="${point[1]}" r="4" fill="${escape(item.color)}"><title>${escape(item.name)} · ${escape(data.labels[index])}: ${number(value, precision)}</title></circle>`;
      if (annotations && !item.values.slice(index + 1).some(value=>value!=null)) svg += `<text x="${point[0]+7}" y="${point[1]-10}" fill="${escape(item.color)}" class="chart-annotation">${number(value, precision)}</text>`;
      previous = point;
    });
  }
  svg += '</svg>';
  return `<div class="chart-legend">${series.map(item => `<span><i style="background:${escape(item.color)}"></i>${escape(item.name)}</span>`).join('')}</div>${svg}<p>${escape(data.note)}</p>`;
}

export function radar(stats) {
  const selected = stats.slice(0, 9), center = 140, radius = 83;
  if (selected.length < 3) return '';
  const point = (index, ratio) => {
    const angle = -Math.PI / 2 + index / selected.length * Math.PI * 2;
    return [center + Math.cos(angle) * radius * ratio, center + Math.sin(angle) * radius * ratio];
  };
  let content = '<svg class="radar" viewBox="0 0 280 280" role="img" aria-label="Radar dos atributos do piloto">';
  for (const scale of [.25,.5,.75,1]) content += `<polygon class="grid" points="${selected.map((_, index) => point(index, scale).join(',')).join(' ')}"/>`;
  content += `<polygon class="shape" points="${selected.map((stat, index) => point(index, stat.Val / 100).join(',')).join(' ')}"/>`;
  selected.forEach((stat,index) => {const location = point(index,1.3); content += `<text x="${location[0]}" y="${location[1]}" text-anchor="middle">${escape(stat.label)}</text>`;});
  return content + '</svg>';
}

export function normalizeFontScale(value) {
  const parsed=Number(value);
  return Number.isFinite(parsed)&&parsed>=.9&&parsed<=1.3 ? Math.round(parsed*10)/10 : 1;
}


export function installFontControls() {
  let scale=normalizeFontScale(localStorage.getItem('f1-font-scale'));
  const controls=document.createElement('div');
  controls.className='font-controls';
  controls.setAttribute('role','group');
  controls.setAttribute('aria-label','Tamanho das letras');
  controls.innerHTML='<button type="button" aria-label="Diminuir letras" title="Diminuir letras">A−</button><button type="button" aria-label="Aumentar letras" title="Aumentar letras">A＋</button>';
  const [smaller,larger]=controls.querySelectorAll('button');
  function apply() {
    document.documentElement.style.setProperty('--font-scale',String(scale));
    smaller.disabled=scale<=.9;
    larger.disabled=scale>=1.3;
    localStorage.setItem('f1-font-scale',String(scale));
  }
  smaller.onclick=()=>{scale=Math.max(.9,Math.round((scale-.1)*10)/10);apply();};
  larger.onclick=()=>{scale=Math.min(1.3,Math.round((scale+.1)*10)/10);apply();};
  document.querySelector('.top-actions').prepend(controls);
  apply();
}

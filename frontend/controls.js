export function steppedValue(value, step, direction, min = -Infinity, max = Infinity, fast = false) {
  const amount = Number.isFinite(Number(step)) && Number(step) > 0 ? Number(step) : 1;
  const current = Number.isFinite(Number(value)) ? Number(value) : 0;
  return Math.min(max, Math.max(min, Number((current + amount * direction * (fast ? 10 : 1)).toFixed(10))));
}

export function installNumberControls(root) {
  root.querySelectorAll('input[type="number"]').forEach(input => {
    if (input.closest('.number-stepper')) return;
    const wrapper = document.createElement('span');
    wrapper.className = 'number-stepper';
    input.before(wrapper);
    wrapper.append(input);
    for (const [symbol, direction, label] of [['−', -1, 'Diminuir'], ['+', 1, 'Aumentar']]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = symbol;
      button.setAttribute('aria-label', `${label} ${input.getAttribute('aria-label') || input.name || 'valor'}`);
      button.title = `${label} · Shift + clique: 10 passos`;
      button.disabled = input.disabled || input.readOnly;
      button.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        const min = input.min === '' ? -Infinity : Number(input.min);
        const max = input.max === '' ? Infinity : Number(input.max);
        input.value = steppedValue(input.value, input.step, direction, min, max, event.shiftKey);
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new Event('change', {bubbles: true}));
      });
      if (direction < 0) wrapper.prepend(button); else wrapper.append(button);
    }
  });
}

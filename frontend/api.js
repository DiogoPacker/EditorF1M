// Cada abertura começa vazia; nunca retomar o save da visita anterior.
export const session = {id: null, meta: null};

export async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { detail = response.statusText; }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}

export function api(path = '', options = {}) {
  if (!session.id) throw new Error('Abra um save primeiro.');
  return request(`/api/saves/${session.id}${path}`, options);
}

export function patch(path, data) {
  return api(path, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
}

export const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]));
export const money = value => value == null ? '—' : '$ ' + Number(value).toLocaleString('pt-BR');
export const number = (value, decimals = 0) => value == null ? '—' : Number(value).toLocaleString('pt-BR', {maximumFractionDigits: decimals});

export function toast(message, error = false) {
  const element = document.querySelector('#toast');
  element.textContent = message;
  element.className = error ? 'error' : '';
  element.style.display = 'block';
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {element.style.display = 'none';}, error ? 10000 : 4500);
}

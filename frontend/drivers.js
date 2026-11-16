import {escape as esc, number} from './api.js';


export const driverGroups = ['F1 — titulares', 'Academia / reservas', 'F2', 'F3', 'Livres — sem equipe'];
export const driverSorts = [['category', 'Categoria · melhores primeiro'], ['overall-desc', 'Overall · maior primeiro'], ['overall-asc', 'Overall · menor primeiro'], ['name', 'Nome · A–Z']];

export function driverGroup(driver) {
  const contracts = driver.affiliations?.length ? driver.affiliations : driver.contract ? [driver.contract] : [];
  if (contracts.some(contract => Number(contract.Formula) === 1 && [1,2].includes(Number(contract.PosInTeam)))) return 0;
  if (contracts.some(contract => Number(contract.Formula) === 1 && Number(contract.PosInTeam) > 2)) return 1;
  if (contracts.some(contract => Number(contract.Formula) === 2)) return 2;
  if (contracts.some(contract => Number(contract.Formula) === 3)) return 3;
  return 4;
}

export function sortedDrivers(drivers, order = 'category') {
  const nameOrder = (first, second) => first.name.localeCompare(second.name, 'pt-BR', {sensitivity:'base'}) || first.StaffID-second.StaffID;
  const rating = driver => driver.average != null && driver.average !== '' && Number.isFinite(Number(driver.average)) ? Number(driver.average) : -Infinity;
  return drivers.filter(driver=>!Number(driver.Retired)).sort((first,second)=>{
    if (order === 'name') return nameOrder(first,second);
    const difference = order === 'category' ? driverGroup(first)-driverGroup(second) : 0;
    if (difference) return difference;
    if (!Number.isFinite(rating(first)) || !Number.isFinite(rating(second))) return rating(second)-rating(first) || nameOrder(first,second);
    return (order === 'overall-asc' ? rating(first)-rating(second) : rating(second)-rating(first)) || nameOrder(first,second);
  });
}

export function driverSubtitle(driver, teams = []) {
  const group = driverGroup(driver);
  const contracts = driver.affiliations?.length ? driver.affiliations : driver.contract ? [driver.contract] : [];
  const contract = contracts.find(contract=>group<=1 ? contract.Formula===1 && (group===0 ? [1,2].includes(contract.PosInTeam) : contract.PosInTeam>2) : contract.Formula===group);
  const team = teams.find(team=>team.TeamID===contract?.TeamID);
  return group===4 ? 'Livre — sem equipe' : `${driverGroups[group]} · ${team?.name??contract?.TeamName??driver.team?.name??''}`;
}

export function sortControl(id, selected = 'category') {
  return `<label class="list-sort-label">Ordenar por<select id="${esc(id)}">${driverSorts.map(([value,label])=>`<option value="${value}" ${value===selected?'selected':''}>${label}</option>`).join('')}</select><small>Overall mostrado = média simples dos atributos.</small></label>`;
}

export function driverOptions(drivers, selected, order = 'category') {
  const list = sortedDrivers(drivers,order);
  const option = driver=>`<option value="${driver.StaffID}" ${driver.StaffID===selected?'selected':''}>${esc(driver.name)} · ${number(driver.average,1)}</option>`;
  if (order !== 'category') return list.map(option).join('');
  return driverGroups.map((label,group)=>{
    const members=list.filter(driver=>driverGroup(driver)===group);
    return members.length ? `<optgroup label="${esc(label)}">${members.map(option).join('')}</optgroup>` : '';
  }).join('');
}

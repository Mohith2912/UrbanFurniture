export function money(value, decimals = 2) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(Number(value || 0) / 100);
}

export function dateText(value) {
  if (!value) return '—';
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export const today = () => new Date().toISOString().slice(0, 10);
export const dueDate = (days = 30) => new Date(Date.now() + Number(days) * 86400000).toISOString().slice(0, 10);

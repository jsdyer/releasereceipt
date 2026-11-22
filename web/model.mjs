export const sectors = {all: 'All industries', goods: 'Goods-producing industries', services: 'Services-producing industries'};

export function shiftMonth(month, offset) {
  const [year, number] = month.split('-').map(Number);
  return new Date(Date.UTC(year, number - 1 + offset, 1)).toISOString().slice(0, 7);
}

export function receipts(releases, sector) {
  const months = new Map();
  for (const release of [...releases].sort((a,b) => a.published.localeCompare(b.published))) {
    release.series[sector].forEach((value, index, values) => {
      const month = shiftMonth(release.month, index + 1 - values.length);
      if (!months.has(month)) months.set(month, []);
      months.get(month).push({month, value, initial: month === release.month, published: release.published, table: release.table});
    });
  }
  return months;
}

export function revision(rows) {
  const initial = rows.find(row => row.initial);
  return initial && rows.length > 1 ? Math.round((rows.at(-1).value - initial.value) * 10) / 10 : null;
}

export function csv(rows) {
  return ['reference_month,sector,released,stage,monthly_growth_percent,source_table', ...rows.map(r =>
    [r.month, r.sector, r.published, r.initial ? 'first table' : 'later table', r.value.toFixed(1), r.table].join(',')
  )].join('\r\n') + '\r\n';
}

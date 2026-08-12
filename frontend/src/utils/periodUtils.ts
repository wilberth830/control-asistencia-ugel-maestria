export type PeriodImport = {
  period_start: string | null;
  period_end: string | null;
};

const months = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

export function importTouchesPeriod(item: PeriodImport, month: number, year: number) {
  if (!item.period_start && !item.period_end) return false;
  const monthStart = new Date(year, month - 1, 1).getTime();
  const monthEnd = new Date(year, month, 0).getTime();
  const importStart = parseDateValue(item.period_start ?? item.period_end);
  const importEnd = parseDateValue(item.period_end ?? item.period_start);
  if (importStart === null || importEnd === null) return false;
  return importStart <= monthEnd && importEnd >= monthStart;
}

export function yearsFromImports(imports: PeriodImport[], fallbackYear: number) {
  const years = new Set<number>();
  imports.forEach((item) => {
    const startYear = item.period_start ? Number(item.period_start.slice(0, 4)) : null;
    const endYear = item.period_end ? Number(item.period_end.slice(0, 4)) : null;
    if (startYear) years.add(startYear);
    if (endYear) years.add(endYear);
    if (startYear && endYear) {
      for (let value = startYear; value <= endYear; value += 1) years.add(value);
    }
  });
  return years.size ? [...years].sort((a, b) => b - a) : [fallbackYear];
}

export function monthsFromImports(
  imports: PeriodImport[],
  selectedYear: number,
  fallbackMonth: number,
) {
  const values = months
    .map((_, index) => index + 1)
    .filter((month) => imports.some((item) => importTouchesPeriod(item, month, selectedYear)))
    .sort((left, right) => right - left);
  const available = values.length ? values : [fallbackMonth];
  return available.map((value) => ({ value, label: months[value - 1] }));
}

function parseDateValue(value?: string | null) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day).getTime();
}

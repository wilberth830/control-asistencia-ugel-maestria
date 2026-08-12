import { describe, expect, it } from "vitest";

import {
  importTouchesPeriod,
  monthsFromImports,
  yearsFromImports,
} from "../utils/periodUtils";
import type { PeriodImport } from "../utils/periodUtils";

const importRow: PeriodImport = {
  period_start: "2026-07-30",
  period_end: "2026-08-02",
};

describe("periodos de importación", () => {
  it("incluye todos los meses tocados por el archivo", () => {
    expect(importTouchesPeriod(importRow, 7, 2026)).toBe(true);
    expect(importTouchesPeriod(importRow, 8, 2026)).toBe(true);
    expect(importTouchesPeriod(importRow, 9, 2026)).toBe(false);
  });

  it("deriva años y meses disponibles", () => {
    expect(yearsFromImports([importRow], 2025)).toEqual([2026]);
    expect(monthsFromImports([importRow], 2026, 1).map((item) => item.value)).toEqual([
      8,
      7,
    ]);
  });
});

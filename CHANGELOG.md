# Changelog

## 1.0.0 (2026-11-25)

First release.

- **Name.** The packages are named lifefrom-units:
  - Python distribution `lifefrom-units`, import `lifefrom_units`;
  - npm package `@lifefrom/units`;
  - CLI `lifefrom-units`.
- **Specification:** `data/units.json`.
  - 158 units: 24 proper and 18 arbitrary dimensions.
  - 27 normalisation rules.
  - 60 analytes with conversions, covering 83 LifeFrom markers.
  - 6 forbidden rules: Lp(a), insulin, AMH, HbA1c % vs mmol/mol by factor, HbA1c as a fraction, IU for serum 25-OH-D.
  - 61 cited sources.
- **Functions.** Both packages have `normalize_unit`, `convert`, `convert_result`, `parse_value`, `parse_result`, `same_unit`, `explain`, `unit_info`, `analytes` and a CLI. Neither has runtime dependencies.
  - Python needs 3.9 or later.
  - TypeScript ships as strict ESM, with camelCase names and snake_case aliases.
- **Caller-supplied factor.** `factor=` is optional and never a default. `explain()` records it, with the rule it overrides.
- **Qualified values.** `<5`, `>1000`, `5.4 H` and `5,4 L` are parsed into a value, a comparator and a flag, and the qualifiers are kept through a conversion. Plain `convert` raises `qualified_value` rather than drop them.
- **Caveats.** `explain()` returns `warnings` and `reference_compounds`. Enzyme conversions warn that methods and temperatures are not made comparable. 25-OH-D (D3 vs D2) and folate (folic acid vs 5-MTHF) name their reference compound and the alternative.
- **AMH.** Refused by default. The NHANES factor 7.14 is not stated to be assay-independent.
- **Tests.** 1,501 shared test vectors. Both packages pass all of them with bit-identical results.
- **Website data.** `web/lifefrom-units.json`, with warnings and the reference compound shipped next to each factor.
- **UCUM.** 143 units carry a UCUM code. All are validated by our grammar check and by ucum-lhc 8.0.1.
- **Changes from LifeFrom release 1:**
  - 28 factors replaced by sourced values, all within 0.1% of the old ones;
  - HbA1c now uses the NGSP master equation;
  - 44 conversions added;
  - TSH mU/L ↔ mIU/L and IgE kU/L ↔ IU/mL are no longer converted by default (no source found); `factor=` covers them.

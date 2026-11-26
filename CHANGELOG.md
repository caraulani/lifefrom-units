# Changelog

## 1.1.0 (2026-11-26)

Fix: "mil/mm3" and "mil/µL" are no longer read as millions by default.

- **The bug.** 1.0.0 listed `Mil/mm3` as an alias of `10^6/mm³` and `Mil/µL` as an alias of `10^6/µL`, and matched them without regard to case. On a Spanish report "mil" is the word for one thousand: white cells "7,5 mil/mm3" are 7.5 × 10^3/mm³, and 1.0.0 converted them 1000× too high. US reports use "Mil/µL" for millions (red cells), and Romanian reports use "mil./µL" for millions ("mii/µL" for thousands). Found by lab-reading-bench: 12 white-cell and platelet values on its generated Spanish reports came out 1000× too high.
- **Refused without a language.** `mil/mm3`, `mil/mm³`, `mil/cmm`, `mil./mm3`, `mil/µL` and `mil./µL` (any case, any µ spelling) now raise a new error, `AmbiguousUnitError` (code `ambiguous_unit`), unless a locale is given. The error carries the readings and the reason.
- **New optional `locale`.** `normalize_unit`, `unit_info`, `convert`, `convert_result`, `same_unit` and `explain` take an optional `locale` (Python keyword; TypeScript last argument `{ locale }`; CLI `--locale`/`-l`). It is a language tag such as `es`, `es-AR`, `en-US` or `ro`; only the language subtag is used. `es` reads "mil" as thousand; `en` and `ro` read it as million. Other languages are refused. A locale never changes an unambiguous spelling.
- **Sourced readings.** `explain()` starts with a `spelling_reading` step that names the reading and its sources: Spanish Wiktionary "mil" (the RAE dictionary refused a scripted download), the NIH Clinical Center's Spanish CBC leaflet (which uses "mil/mm3" for millions, following US usage), the UW Medicine lab test guide (RBC in "mil/uL"), and DEX '09 "mie" and "milion" for Romanian. No real Spanish or Romanian lab report printing these exact spellings was found online; see METHODS.md §3.
- **New unambiguous spellings.** `mill/mm3`, `mill/mm³`, `mill./mm3`, `millones/mm3`, `millones/mm³`, `Million/mm3` (10^6/mm³); `mill./µL`, `millones/µL` (10^6/µL); `mii/µL`, `miles/µL` (10^3/µL); `mii/mm3`, `mii/mm³`, `miles/mm3`, `miles/mm³`, `Thousand/mm3` (10^3/mm³).
- **Specification.** `data/units.json` adds `ambiguous[]`, `language_readings{}` and `lookup.ambiguous`; `schema_version` stays 1 (additive). `web/lifefrom-units.json` adds `ambiguous[]`. 66 cited sources (5 new).
- **Tests.** 1,587 shared vectors (86 new, 22 of them `ambiguous_unit`). The language cross-check now also compares explanation steps and the `ambiguous_unit` message.
- **Compatibility.** Every other call behaves as in 1.0.0. Code that relied on `Mil/µL` or `Mil/mm3` meaning millions must now pass `locale="en"`.

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

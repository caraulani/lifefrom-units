# Methods

This document is meant to let a stranger rebuild lifefrom-units 1.1.0 and get the same files. All sources were accessed on 2026-11-25, except the five language-reading sources added in 1.1.0 (§3), accessed on 2026-11-26.

## 1. Rebuild

```bash
./scripts/build_all.sh --fetch
```

This runs four steps:

1. `scripts/fetch_sources.sh` downloads every raw file into `../_raw/` (outside the repository).
2. `scripts/build.py` writes:
   - `data/units.json`, `data/analyte_factors.csv`, `data/release1_comparison.csv` and `data/release1_unknown_units.txt`;
   - `web/lifefrom-units.json`;
   - the package data copies (`python/src/lifefrom_units/units.json`, `ts/src/data.ts`).
3. `scripts/make_vectors.py` writes `tests/vectors.json`.
4. The script then runs:
   - the Python suite on current Python and on Python 3.9;
   - the TypeScript suite on Node;
   - a cross-language comparison;
   - local package builds and `SHA256SUMS`.

Tools: Python 3.9+ with only the standard library for the build, `uv` for the test environments, and Node 18+ with TypeScript 5.7 as a dev dependency. Both packages have zero runtime dependencies.

Rebuilding from a fresh download gave byte-identical `data/units.json`, `web/lifefrom-units.json` and `tests/vectors.json`, checked with SHA-256 on 2026-11-25.

## 2. Inputs

| Input | Where | Used for |
|---|---|---|
| LifeFrom release 1 (`markers.csv`, `units.csv`, `ambiguities.csv`) | `_raw/lifefrom-release-1/` | marker slugs (join key), the unit spellings that must resolve, and the comparison with release 1's factors |
| PubChem PUG REST, `compound/cid/<CID>/property/Title,MolecularFormula,MolecularWeight/JSON` | `_raw/pubchem/cid_<CID>.json` (35 compounds) | molar masses of compounds |
| CIAAW abridged standard atomic weights, https://www.ciaaw.org/abridged-atomic-weights.htm | `_raw/ciaaw/abridged.htm` | atomic weights of elements (Ca, Mg, P, Fe, Zn, Cu, Se, Mn, Cr, Na, K, Cl) and the formula-based cross-check |
| NGSP, https://ngsp.org/ifccngsp.asp | `_raw/ngsp/ifccngsp.html` | IFCC–NGSP master equation, Table 2 |
| CDC NHANES 2021–2023 lab documentation (`BIOPRO_L`, `TRIGLY_L`, `TCHOL_L`, `GLU_L`, `TST_L`, `FOLATE_L`, `ALB_CR_L`, `INS_L`, `HDL_L`) | `_raw/nhanes-docs-labunits/` | published factor for triglycerides (primary); AMH factor quoted in the AMH refusal; cross-checks for 20 other factors |
| UCUM essence 2.2, https://github.com/ucum-org/ucum | `_raw/ucum/ucum-essence.xml` | build-time validation of UCUM codes only; not redistributed |
| Europe PMC full texts PMC9639807, PMC9279959, PMC6152246 | `_raw/labunits-europepmc/` | quoted statements for Lp(a), insulin and the enzyme unit |
| Spanish Wiktionary "mil"; NIH Clinical Center Spanish CBC leaflet (Wayback Machine copy); UW Medicine DLMP test guide, RBC; DEX '09 "mie" and "milion" via dexonline.ro | `_raw/unit-languages/` | how "mil/mm3" and "mil/µL" are read in Spanish, English and Romanian (§3); cited, nothing numeric is read from them |
| IOM 2011, *Dietary Reference Intakes for Calcium and Vitamin D*, ch. 3, p. 78 (doi:10.17226/13050) | read online at nationalacademies.org/read/13050/chapter/5; that server refused a scripted download | 1 µg vitamin D = 40 IU (dose units); rounded serum divisor 2.5 (cross-check) |

## 3. Units and normalisation

**Unit table.** `scripts/spec.py` defines 158 canonical units in 24 proper dimensions plus 18 arbitrary or descriptive units.

- Each unit has a scale to its dimension's base unit. The scale is computed as an exact fraction (Python `fractions.Fraction`) and then converted to the nearest double.
- Proper units are built from SI prefixes over g, mol, Eq, IU, U, kat and cell counts, divided by L, dL or mL. The rest are fractions, rates, time, cell volume, osmolality and D-dimer FEU/DDU.
- `U` (enzyme unit or assay unit, depending on the analyte) and `IU` are separate dimensions. Neither converts to mass or moles without an analyte rule.
- Each arbitrary unit (S/CO, index, AI, EU, CU, AU/mL, titer, ratio, qualitative, semiquantitative, descriptive, calculated, pH, /hpf, /lpf, EU/dL, /100 WBC, the aldosterone-renin ratio unit) is its own dimension. It converts only to itself. This follows UCUM §24–§25: arbitrary units "are not commensurable with any other unit".

**Normalisation.** 27 ordered regular-expression rules are stored in `data/units.json`. They cover:

- Greek mu and micro sign;
- superscript digits;
- `10E9`, `10*9`, `10**9`, `×10⁹`;
- leading `x`/`×`;
- `mc` and `u` as micro;
- French `UI`;
- UCUM `[IU]`;
- `/hr` and `/24 hr`;
- spacing.

The rules avoid `\b`, lookbehind and Unicode classes, so Python and JavaScript apply them the same way.

A unit string is looked up in two passes:

1. The rules are applied and all whitespace is removed. The result is looked up in `lookup.exact`.
2. If that fails, the same is done to the lower-cased input, which is looked up in `lookup.casefold`.

Some spellings must never match by case: `G/L` (giga per litre) vs `g/L`, `T/L`, `M/µL`, and `nM`, `pM`, `µM`, `mM` vs `nm`. These are kept out of the case-folded table. The build fails if two units collide after case folding.

**Spellings that mean different units in different languages (added in 1.1.0).** "mil" is the Spanish word for one thousand, an English abbreviation for million, and the Romanian abbreviation "mil." for milion. So `7,5 mil/mm3` on a Spanish report is 7.5 × 10^3/mm³ (white cells), while `4.5 Mil/µL` on a US report is 4.5 × 10^6/µL (red cells). Case does not separate the two. Version 1.0.0 listed `Mil/mm3` and `Mil/µL` as aliases of the million units and matched them case-insensitively, so Spanish white-cell and platelet counts came out 1000× too high (found by lab-reading-bench on its generated Spanish reports: 12 values).

- `mil/mm3`, `mil/mm³`, `mil/cmm`, `mil./mm3`, `mil./mm³`, `mil/µL` and `mil./µL` (any case, any spelling of µ) are kept in `ambiguous[]`, not in the lookup tables. The build fails if any of them also resolves as a unit, or if a case-sensitive alias folds onto one.
- They are looked up after `lookup.exact` and before `lookup.casefold`. Without a locale, or with a language that has no reading, they raise `ambiguous_unit`.
- With a locale, only the primary language subtag counts (`es-AR` → `es`). Readings shipped:

| Language | "mil" | `mil/mm3` | `mil/µL` | Sources |
|---|---|---|---|---|
| `es` | thousand | 10^3/mm³ | 10^3/µL | Spanish Wiktionary, "mil": "Diez veces cien", "El número 1000, 10^3" (the RAE *Diccionario de la lengua española* gives the same definition but refused a scripted download, HTTP 403). NIH Clinical Center Spanish CBC leaflet, cited because it shows the opposite: "Los glóbulos rojos se miden en millones por milímetro cúbico (mil/mm3)". |
| `en` | million | 10^6/mm³ | 10^6/µL | UW Medicine DLMP test guide, RBC, reference ranges in "mil/uL"; the NIH Clinical Center leaflet above. |
| `ro` | million | 10^6/mm³ | 10^6/µL | DEX '09 "milion": "Număr egal cu o mie de mii"; DEX '09 "mie, mii": "Numărul care în numărătoare are locul între 999 și 1001". |

What we could not source:

- We found no Spanish or Romanian laboratory report online that prints `mil/mm3`, `mil/µL` or `mil./µL`. The Spanish reading rests on the meaning of the word, and the Romanian one on the two numerals; no dictionary entry for the abbreviation "mil." itself was found.
- The NIH leaflet shows that a Spanish-language document can follow US usage, so `locale="es"` means "this report follows Spanish usage", not only "this report is in Spanish".
- No reading is shipped for other languages. Portuguese "mil" is also thousand, but no source was fetched, so `pt` is refused for now.

Unambiguous spellings were added and need no locale: `mill/mm3`, `mill./mm3`, `millones/mm3`, `Million/mm3`, `mill./µL`, `millones/µL` (millions); `mii/µL`, `mii/mm3`, `miles/µL`, `miles/mm3`, `Thousand/mm3` (thousands).

**Coverage of release 1.** Every unit string in release 1's `units.csv` resolves: 575 rows plus their `equivalent_forms`. `data/release1_unknown_units.txt` is empty.

## 4. Conversion model

All conversions are affine maps on base units: `base_to = a × base_from + b`. For factors, b = 0. For the HbA1c equation, b ≠ 0.

**Same dimension, no analyte needed.** The factor is `scale_from / scale_to`. This is "derived: unit arithmetic" and needs no source. Examples: mg/L ↔ µg/mL, 10^9/L ↔ K/µL, % ↔ L/L, U/L ↔ kU/L.

**Different dimensions.** An analyte is required. Each analyte lists "bridges" between dimensions. The engine finds the shortest chain by breadth-first search, so mEq/L → mmol/L → mg/dL works for magnesium, and composes the affine maps. The bridge kinds are:

| Kind | Bridge | Source |
|---|---|---|
| `molar_mass` | mass concentration ↔ substance concentration (and mass rate ↔ substance rate): a = 1/M | PubChem molecular weight (CID recorded) or CIAAW atomic weight |
| `urea_nitrogen` | BUN mass (as N) ↔ urea substance: a = 1/M(N2) | PubChem CID 947 (N2, 28.014 g/mol) |
| `published_factor` | used where the analyte is not one compound | NHANES TRIGLY_L (triglycerides 0.01129) |
| `charge` | substance ↔ charge equivalents: a = \|z\| | derived: unit arithmetic with the ion charge |
| `enzyme_unit` | U/L ↔ katal/L: 1 U = 1 µmol/min = 1/60 µkat | derived from UCUM definitions (U = umol/min, kat = mol/s); Ramsay & Tipton 2017 |
| `label_equivalence` | IU/L ↔ U/L, enzymes only | Ramsay & Tipton 2017: "the Unit, sometimes referred to as the International Unit (IU)" |
| `creatinine_denominator` | mg/g ↔ mg/mmol (urine ACR, PCR): a = M(creatinine) | PubChem CID 588 |
| `equation` | HbA1c IFCC mmol/mol ↔ NGSP %: NGSP = 0.09148 × IFCC + 2.152 | NGSP Table 2; Hoelzel et al. 2004 |
| `dose_equivalence` | vitamin D mass ↔ IU: 1 µg = 40 IU | IOM 2011, ch. 3, p. 78 |

**Forbidden rules.** Each forbidden rule has a reason and a source. Analyte-specific rules are checked before any conversion. Generic rules (no analyte) are checked only when no bridge applies.

1. Lp(a): mass concentration ↔ substance concentration. Kronenberg et al. 2022: "This panel does not recommend using a standard factor to convert between mg/dL and nmol/L, as assays vary extensively."
2. Insulin: IU concentration ↔ substance concentration. Rosli et al. 2022: "there are still several different conversion factors available depending on the manufacturer or field."
3. Any analyte: fraction (%) ↔ substance fraction (mmol/mol) by factor. The error points to `analyte="hba1c"`.
4. HbA1c: no conversion to or from a fraction of 1 (`fraction`, `L/L`, `‰`). NGSP % is a calibrated scale.
5. 25-hydroxyvitamin D: no IU concentration. IU are dose units (IOM 2011).
6. AMH: mass concentration ↔ substance concentration. AMH is a glycoprotein with no formula-based molar mass. NHANES TST_L multiplies by 7.14, but does not state that this factor is assay-independent, so it is not applied by default.

Conversions between arbitrary units are always refused (UCUM §24–§25).

**Caveats that ship with a factor.** `explain()` returns `warnings` and `reference_compounds`.

- **Enzymes.** Converting U/L, IU/L and µkat/L changes the unit only. It does not make results from different methods, reaction temperatures or reference systems comparable.
- **25-OH-D.** The reference compound is D3 (CID 5283731, 400.6 g/mol). D2 (CID 5710148, 412.6 g/mol) is about 3% different.
- **Folate.** The reference compound is folic acid (CID 135398658, 441.4 g/mol). L-methylfolate (CID 135398561, 459.5 g/mol) is about 4% different.
- **Other molar-mass factors** report their reference compound or element in `reference_compounds`.
- **Website.** `web/lifefrom-units.json` carries the same warnings and the reference compound with each factor.

**Caller-supplied factor.** `convert`, `convert_result` and `explain` take an optional `factor` (`value_to = value_from × factor`).

- It is never a default, and it must be a positive number.
- It replaces the library's own result, including a refusal.
- `explain` returns `kind: "user_factor"` and `user_factor: {value, overrides, library_kind, library_factor}`.
- The warnings say that the factor is unchecked, name the rule it overrides (with that rule's reason), or give how far it differs from the library's factor.
- Unknown units and unknown analytes still raise errors.

**Qualified values.** `parse_result` splits a reported value into three parts: a comparator (`<`, `>`, `<=`, `>=`, also `≤`, `≥`, `=<`, `=>`), the number, and a trailing flag (`H`, `L`, `HH`, `LL`, `A`, `AA`, optionally in `()` or `[]`, or `↑`, `↓`, `*`, `!`).

- Flag letters are upper-cased.
- A flag is recognised only after a number.
- `convert_result` converts the number and keeps both qualifiers. Every conversion is increasing, so the comparator stays valid.
- The flag is copied unchanged, with a note that it refers to the original lab's reference interval.
- `parse_value` and `convert` raise `qualified_value` on such input rather than drop the qualifier. If the number itself is malformed, that error is raised instead.

**Errors.** Each error has a stable code shared by both packages:

- `unknown_unit`, `unknown_analyte`
- `incompatible_units`: different dimensions and no analyte
- `forbidden`
- `no_sourced_conversion`: an analyte was given but no bridge exists
- `ambiguous_unit`: the spelling means different units in different languages and no usable locale was given (§3)
- `invalid_value`, `qualified_value`, `ambiguous_value`

**Values.** `parse_value` accepts:

- numbers;
- decimal commas (`5,4`);
- mixed separators where the rightmost one is the decimal (`1.234,5`, `1,234.5`);
- thousands groups of exactly three digits (`1.234.567`);
- thin, narrow and non-breaking spaces and `'` between digits;
- the Unicode minus sign.

A single comma followed by exactly three digits, with a 1–3 digit non-zero integer part (`1,234`), could be read two ways and raises `ambiguous_value`. A single dot is always decimal. Values with a comparator or flag raise `qualified_value` (see above). Words raise `invalid_value`.

## 5. Molar masses: choice of value

- **Compounds:** PubChem `MolecularWeight`, as published (4–5 significant figures). PubChem computes it from the formula with standard atomic weights.
- **Elements:** CIAAW abridged standard atomic weight. PubChem's element records round some of these more coarsely (zinc 65.4 vs CIAAW 65.38).
- Where release 1's factor disagrees with the sourced one, lifefrom-units uses the sourced one (section 8).

Conventions, each recorded in `analytes[].note`:

- Triglycerides: published NHANES factor 0.01129. Triolein (CID 5497163, 885.4 g/mol) gives 0.011294, used as a cross-check only.
- Folate: folic acid, CID 135398658.
- Vitamin B12: cyanocobalamin, CID 5311498; PubChem's record title is "Anacobin".
- 25-Hydroxyvitamin D: 25-hydroxyvitamin D3, CID 5283731. D2 (CID 5710148, 412.6) differs by about 3%.
- 1,25-Dihydroxyvitamin D: calcitriol.
- T3 and reverse T3: same formula and molar mass (CIDs 5920 and 644280).
- Phosphorus: expressed as P.
- Iron (TIBC, UIBC): expressed as iron.
- Lactate: lactic acid, CID 612.
- BUN: mass of nitrogen; urea has 2 N.

## 6. Hand verification of analyte factors

Each factor below was checked two ways, both independent of the lifefrom-units engine.

**(a) Molar mass from the formula.** The molar mass was recomputed from PubChem's molecular formula using CIAAW abridged atomic weights (`scripts/verify_factors.py`). This checks that the PubChem value and CID refer to the intended compound and that the rounding is as expected.

**(b) Published factors.** Where a published factor exists in a table fetched today, the lifefrom-units factor was compared with it. All differences are within the rounding of the published factor. The published factors have 3–4 significant figures; for example, NHANES gives calcium as 0.250, against 1/4.0078 = 0.2495.

Every PubChem record was also read directly as raw JSON, and its title and formula checked against the analyte name. The table has 32 rows: 27 PubChem compounds and 5 elements.

| # | Analyte | PubChem CID / element | Formula | PubChem MW | MW from formula (CIAAW) | Diff | lifefrom-units factor | Published factor | Diff vs published |
|---|---|---|---|---|---|---|---|---|---|
| 1 | glucose (mg/dL → mmol/L) | 5793 | C6H12O6 | 180.16 | 180.156 | +0.002% | 0.055506 | 0.05551 (NHANES GLU_L) | -0.01% |
| 2 | cholesterol (mg/dL → mmol/L) | 5997 | C27H46O | 386.7 | 386.664 | +0.009% | 0.02586 | 0.02586 (NHANES TCHOL_L) | -0.00% |
| 3 | creatinine (mg/dL → µmol/L) | 588 | C4H7N3O | 113.12 | 113.120 | +0.000% | 88.402 | 88.4 (NHANES BIOPRO_L) | +0.00% |
| 4 | uric-acid (mg/dL → µmol/L) | 1175 | C5H4N4O3 | 168.11 | 168.112 | -0.001% | 59.485 | 59.48 (NHANES BIOPRO_L) | +0.01% |
| 5 | bilirubin (mg/dL → µmol/L) | 5280352 | C33H36N4O6 | 584.7 | 584.673 | +0.005% | 17.103 | 17.1 (NHANES BIOPRO_L) | +0.02% |
| 6 | urea (mg/dL → mmol/L) | 1176 | CH4N2O | 60.056 | 60.056 | +0.000% | 0.16651 | — |  |
| 7 | cortisol (µg/dL → nmol/L) | 5754 | C21H30O5 | 362.5 | 362.466 | +0.009% | 27.586 | — |  |
| 8 | testosterone (ng/dL → nmol/L) | 6013 | C19H28O2 | 288.4 | 288.431 | -0.011% | 0.034674 | 0.0347 (NHANES TST_L) | -0.07% |
| 9 | estradiol (pg/mL → pmol/L) | 5757 | C18H24O2 | 272.4 | 272.388 | +0.004% | 3.6711 | 3.67 (NHANES TST_L) | +0.03% |
| 10 | estrone (ng/dL → pmol/L) | 5870 | C18H22O2 | 270.4 | 270.372 | +0.010% | 36.982 | 37.0 (NHANES TST_L) | -0.05% |
| 11 | dhea-s (µg/dL → µmol/L) | 12594 | C19H28O5S | 368.5 | 368.488 | +0.003% | 0.027137 | 0.0271 (NHANES TST_L) | +0.14% |
| 12 | androstenedione (ng/dL → nmol/L) | 6128 | C19H26O2 | 286.4 | 286.415 | -0.005% | 0.034916 | 0.0349 (NHANES TST_L) | +0.05% |
| 13 | 17-hydroxyprogesterone (ng/dL → nmol/L) | 6238 | C21H30O3 | 330.5 | 330.468 | +0.010% | 0.030257 | 0.0303 (NHANES TST_L) | -0.14% |
| 14 | progesterone (ng/dL → nmol/L) | 5994 | C21H30O2 | 314.5 | 314.469 | +0.010% | 0.031797 | 0.0318 (NHANES TST_L) | -0.01% |
| 15 | folate (ng/mL → nmol/L) | 135398658 | C19H19N7O6 | 441.4 | 441.404 | -0.001% | 2.2655 | 2.265 (NHANES FOLATE_L) | +0.02% |
| 16 | triiodothyronine (pg/mL → pmol/L) | 5920 | C15H12I3NO4 | 650.97 | 650.964 | +0.001% | 1.5362 | — |  |
| 17 | thyroxine (ng/dL → pmol/L) | 5819 | C15H11I4NO4 | 776.87 | 776.856 | +0.002% | 12.872 | — |  |
| 18 | vitamin-b12 (pg/mL → pmol/L) | 5311498 | C63H88CoN14O14P | 1355.4 | 1355.388 | +0.001% | 0.73779 | — |  |
| 19 | 25-hydroxyvitamin-d (ng/mL → nmol/L) | 5283731 | C27H44O2 | 400.6 | 400.647 | -0.012% | 2.4963 | 2.5 (IOM 2011 (multiply by 2.5)) | -0.15% |
| 20 | 1-25-dihydroxyvitamin-d (pg/mL → pmol/L) | 5280453 | C27H44O3 | 416.6 | 416.646 | -0.011% | 2.4004 | — |  |
| 21 | homocysteine (mg/L → µmol/L) | 91552 | C4H9NO2S | 135.19 | 135.181 | +0.007% | 7.397 | — |  |
| 22 | methylmalonic-acid (µg/mL → µmol/L) | 487 | C4H6O4 | 118.09 | 118.088 | +0.002% | 8.4681 | — |  |
| 23 | vitamin-a (µg/dL → µmol/L) | 445354 | C20H30O | 286.5 | 286.459 | +0.014% | 0.034904 | — |  |
| 24 | vitamin-c (mg/dL → µmol/L) | 54670067 | C6H8O6 | 176.12 | 176.124 | -0.002% | 56.779 | — |  |
| 25 | vitamin-e (mg/L → µmol/L) | 14985 | C29H50O2 | 430.7 | 430.717 | -0.004% | 2.3218 | — |  |
| 26 | lactate (mg/dL → mmol/L) | 612 | C3H6O3 | 90.08 | 90.078 | +0.002% | 0.11101 | — |  |
| 27 | aldosterone (ng/dL → pmol/L) | 5839 | C21H28O5 | 360.4 | 360.450 | -0.014% | 27.747 | — |  |
| 28 | calcium (mg/dL → mmol/L) | Ca (CIAAW) | Ca | — | 40.078 | — | 0.24951 | 0.25 (NHANES BIOPRO_L) | -0.19% |
| 29 | iron (µg/dL → µmol/L) | Fe (CIAAW) | Fe | — | 55.845 | — | 0.17907 | 0.1791 (NHANES BIOPRO_L) | -0.02% |
| 30 | phosphorus (mg/dL → mmol/L) | P (CIAAW) | P | — | 30.974 | — | 0.32285 | 0.323 (NHANES BIOPRO_L) | -0.05% |
| 31 | magnesium (mg/dL → mmol/L) | Mg (CIAAW) | Mg | — | 24.305 | — | 0.41144 | — |  |
| 32 | zinc (µg/dL → µmol/L) | Zn (CIAAW) | Zn | — | 65.38 | — | 0.15295 | — |  |

Result:

- All PubChem molar masses agree with the formula-based value to within 0.014%. That is the size of PubChem's own rounding.
- All lifefrom-units factors agree with the published NHANES or IOM factors to within 0.19%. The largest gaps (calcium −0.19%, 25(OH)D −0.15%, 17-OHP −0.14%, DHEA-S +0.14%) come from the published factors being rounded to 3 significant figures (0.250, 2.5, 0.0303, 0.0271).

The same comparison is in `data/analyte_factors.csv`, in the `published_crosscheck` and `crosscheck_rel_diff` columns.

## 7. Test vectors

`scripts/make_vectors.py` writes 1,587 vectors. It does not import lifefrom-units. Expected values come from three places:

- a separate hand-written scale table;
- molar masses read straight from the raw PubChem and CIAAW files, with exact fraction arithmetic;
- hand-typed values from published tables, with tolerances set to the table's rounding.

| Op | Count | Notes |
|---|---|---|
| `normalize` | 324 | spelling variants of 55 units (µ/u/mcg/μ, case, spacing, ×10⁹, superscripts, UI, [IU], 24 h), 11 unknown strings, and 51 for `mil/…` with and without a locale |
| `convert` | 898 | unit arithmetic across 10 dimensions; molar-mass conversions for 43 analytes in both directions; charge; BUN; published factors; enzymes; creatinine ratios; HbA1c (master equation and NGSP Table 1); vitamin D doses; 8 caller-supplied factors; `mil/…` with a locale and refused without; error cases |
| `roundtrip` | 163 | there and back, relative tolerance 1e-12 |
| `same_unit` | 85 | true and false pairs, with and without an analyte |
| `parse_value` | 50 | decimal commas, thousands separators, ambiguous, invalid and qualified inputs |
| `parse_result` | 30 | comparators, flags, both together, malformed inputs |
| `convert_result` | 12 | censored and flagged values through glucose, mg/L, HbA1c and a caller-supplied factor |
| `explain` | 25 | kind, factor or equation, derived flag, source ids, reference compounds, warnings, user-factor record, language-reading sources |

Error vectors by code:

| Code | Count |
|---|---|
| `forbidden` | 47 |
| `invalid_value` | 26 |
| `ambiguous_unit` | 22 |
| `unknown_unit` | 15 |
| `no_sourced_conversion` | 13 |
| `qualified_value` | 10 |
| `incompatible_units` | 10 |
| `ambiguous_value` | 5 |
| `unknown_analyte` | 4 |

Both suites read the same `tests/vectors.json`:

- **Python:** `python/tests/test_vectors.py`, run with pytest on Python 3.14 and 3.9.6.
- **TypeScript:** `ts/test/vectors.test.ts`, run with `node --test` on Node 26.

`scripts/crosscheck_languages.py` then runs every vector through both packages and requires identical results: the same doubles, the same explanation text, warnings, reference compounds and user-factor records, and the same error codes. Since 1.1.0 it also compares every explanation step and the full `ambiguous_unit` message.

## 8. Comparison with LifeFrom release 1

`data/release1_comparison.csv` compares every non-preferred unit row of release 1 with lifefrom-units. The flags:

| Flag | Rows | Meaning |
|---|---|---|
| (none) | 221 | release 1 and lifefrom-units agree; this includes rows where both refuse |
| `new in lifefrom-units` | 44 | release 1 had no conversion; lifefrom-units has a sourced or derived one |
| `differs` | 28 | both convert; the factor differs by more than 1 part in 10⁶ but less than 0.1% |
| `release-1 converts, lifefrom-units does not` | 2 | TSH mU/L → mIU/L and IgE kU/L → IU/mL; no source found for treating U as IU for these hormones and proteins |
| `equation` | 1 | HbA1c: release 1 used (% − 2.15) × 10.929; lifefrom-units uses the NGSP master equation |

The 28 differing factors are all release 1 "LifeFrom reader factor" values. The largest gaps are:

| Analyte | Gap | Why |
|---|---|---|
| total testosterone | +0.075% | release 1 used M = 288.18; PubChem gives 288.4 |
| serum iron and TIBC | −0.037% | 55.8 vs 55.845 |
| zinc | −0.031% | release 1's 0.153 is rounded |
| vitamin B12 | +0.029% | |

None changes a reported value at clinical precision. lifefrom-units uses the sourced value in every case.

## 9. UCUM validation

- `scripts/ucum_validate.py` implements the UCUM case-sensitive grammar (main-term, term, component, annotatable, simple-unit, exponent, factor, annotation), with atoms and prefixes from `ucum-essence.xml` 2.2.
- The build fails on any invalid code.
- As an independent check, `scripts/check_ucum_lhc.cjs` was run against `@lhncbc/ucum-lhc` 8.0.1, installed separately (it is not a dependency of this repository):
  - all 143 codes were valid;
  - all 1,114 same-dimension, non-IU unit pairs gave the same factor as lifefrom-units to within 1e-9;
  - mg/dL → mmol/L with each of the 43 molar masses matched;
  - ucum-lhc refused the 210 IU prefix pairs (strict UCUM §25), which lifefrom-units allows on purpose (see README).

## 10. What was not done

- Factors for proteins and peptides were not derived, and AMH's published NHANES factor is not applied by default. Proteins and peptides have no formula-based molar mass, and published factors vary by calibrator. Callers can pass their own `factor=`.
- Ammonia was left out. Labs report it either as NH3 or as nitrogen, so a single factor would be wrong for some labs.
- Haemoglobin g/dL ↔ mmol/L was left out because no source was fetched.
- No reference intervals are included.

# @lifefrom/units

Normalise clinical lab unit spellings and convert lab values with sourced, analyte-specific factors. ESM, strict TypeScript types, zero runtime dependencies. It uses the same data and the same test vectors as the Python package `lifefrom-units`.

```ts
import { convert, convertResult, normalizeUnit, sameUnit, explain, LifeFromUnitsError } from '@lifefrom/units';

normalizeUnit('mcg/l');                             // 'µg/L'
sameUnit('µg/L', 'ng/mL');                          // true
convert('5,4', 'mmol/L', 'mg/dL', 'glucose');       // 97.2864
convertResult('5,4 H', 'mmol/L', 'mg/dL', 'glucose').text;  // '97.2864 H'
convert(10, 'µIU/mL', 'pmol/L', 'insulin', 6);      // 60, your factor (explain() records it)
convert(50, 'mg/dL', 'nmol/L', 'lipoprotein-a');    // throws LifeFromUnitsError, code 'forbidden'
```

Error codes:

- `unknown_unit`, `unknown_analyte`
- `incompatible_units`
- `forbidden`
- `no_sourced_conversion`
- `invalid_value`, `qualified_value`, `ambiguous_value`

Sources, checks and limitations are described in the repository README and METHODS: https://github.com/caraulani/lifefrom-units

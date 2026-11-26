# lifefrom-units (Python)

Normalise clinical lab unit spellings and convert lab values with sourced, analyte-specific factors. Zero runtime dependencies. Python 3.9 or newer. Distribution `lifefrom-units`, import `lifefrom_units`, CLI `lifefrom-units`.

```python
from lifefrom_units import convert, convert_result, normalize_unit, same_unit, explain

normalize_unit("mcg/l")                                    # 'µg/L'
convert("5,4", "mmol/L", "mg/dL", analyte="glucose")       # 97.2864
convert_result("<5", "mg/dL", "mmol/L", analyte="glucose") # comparator '<' kept
same_unit("K/µL", "10^9/L")                                # True
convert(10, "µIU/mL", "pmol/L", analyte="insulin", factor=6)  # your factor; recorded by explain()
explain("mg/dL", "nmol/L", analyte="lipoprotein-a")        # raises ForbiddenConversionError
convert("7,5", "mil/mm3", "10^9/L", locale="es")           # 7.5: in Spanish "mil" is thousand
convert("7,5", "mil/mm3", "10^9/L")                        # raises AmbiguousUnitError (million in English)
```

Sources, checks and limitations are described in the repository README and METHODS: https://github.com/caraulani/lifefrom-units

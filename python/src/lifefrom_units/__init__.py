"""lifefrom_units: normalise clinical lab unit spellings and convert values with sourced factors.

>>> from lifefrom_units import convert, normalize_unit
>>> normalize_unit("mcg/l")
'µg/L'
>>> round(convert(5.4, "mmol/L", "mg/dL", analyte="glucose"), 1)
97.3
"""
from .core import (
    SPEC,
    AmbiguousUnitError,
    AmbiguousValueError,
    ForbiddenConversionError,
    IncompatibleUnitsError,
    InvalidValueError,
    LifeFromUnitsError,
    NoSourcedConversionError,
    QualifiedValueError,
    UnknownAnalyteError,
    UnknownUnitError,
    analytes,
    convert,
    convert_result,
    explain,
    normalize_unit,
    parse_result,
    parse_value,
    same_unit,
    unit_info,
)
from . import core

__version__ = SPEC["version"]

__all__ = [
    "AmbiguousUnitError", "AmbiguousValueError", "ForbiddenConversionError", "IncompatibleUnitsError", "InvalidValueError",
    "LifeFromUnitsError", "NoSourcedConversionError", "QualifiedValueError", "UnknownAnalyteError", "UnknownUnitError", "analytes",
    "convert", "convert_result", "core", "explain", "normalize_unit", "parse_result", "parse_value", "same_unit", "unit_info", "__version__",
]

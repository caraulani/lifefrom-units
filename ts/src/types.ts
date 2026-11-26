/** Shape of units.json (data/units.json), shared with the Python package. */

export interface Rule {
  pattern: string;
  replacement: string;
  note: string;
}

export interface UnitRecord {
  unit: string;
  dimension: string;
  /** Multiply a value in this unit by `scale` to get the dimension's base unit. */
  scale: number;
  aliases: string[];
  case_sensitive_aliases: string[];
  ucum: string | null;
  note: string | null;
}

export interface Source {
  id?: string;
  label: string;
  url: string;
  kind: string;
  accessed: string;
  doi?: string;
  location?: string;
  pubchem_cid?: number;
  formula?: string;
  molar_mass?: string;
  element?: string;
  api_url?: string;
  title?: string;
}

export interface Bridge {
  from: string;
  to: string;
  /** base_to = a * base_from + b */
  a: number;
  b: number;
  kind: string;
  description: string;
  basis: string;
  sources: string[];
  display: Record<string, string> | null;
  reference_compound?: ReferenceCompound | null;
}

export interface ReferenceCompound {
  name: string;
  molar_mass: number;
  molar_mass_text: string;
  unit: string;
  source: string;
  pubchem_cid?: number;
  formula?: string;
  element?: string;
}

export interface Analyte {
  id: string;
  name: string;
  marker_slugs: string[];
  molar_mass: { value: number; unit: string; source: string } | null;
  charge: number | null;
  bridges: Bridge[];
  note: string | null;
  caveats: string[];
  caveat_sources: string[];
}

export interface Forbidden {
  id: string;
  analyte: string | null;
  a: string;
  b: string;
  a_units: string[] | null;
  b_units: string[] | null;
  example: string[];
  reason: string;
  sources: string[];
}

/** A spelling that means different units in different languages ('mil/mm3'); readings: language subtag -> unit. */
export interface AmbiguousSpelling {
  id: string;
  spellings: string[];
  readings: Record<string, string>;
  reason: string;
}

export interface LanguageReading {
  meaning: string;
  note: string;
  sources: string[];
}

export interface Spec {
  name: string;
  version: string;
  schema_version: number;
  normalization: { rules: Rule[]; procedure: string };
  dimensions: Record<string, { name: string; base: string; convertible: boolean }>;
  units: UnitRecord[];
  lookup: {
    exact: Record<string, string>;
    casefold: Record<string, string>;
    ambiguous: Record<string, string>;
    analytes: Record<string, string>;
  };
  ambiguous: AmbiguousSpelling[];
  language_readings: Record<string, LanguageReading>;
  analytes: Analyte[];
  forbidden: Forbidden[];
  arbitrary_reason: string;
  sources: Record<string, Source>;
}

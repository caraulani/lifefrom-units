#!/usr/bin/env bash
# Download every raw source that scripts/build.py reads.
# Raw files go to ../_raw/<source>/ (outside this repo, never committed).
# Access date for release 1.0.0: 2026-11-25; the language-reading sources added in 1.1.0: 2026-11-26.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
RAW="${LABUNITS_RAW:-$HERE/../_raw}"

mkdir -p "$RAW/pubchem" "$RAW/ciaaw" "$RAW/ngsp" "$RAW/nhanes-docs-labunits" "$RAW/ucum"

# PubChem PUG REST: molecular weight for each compound CID used in data/units.json.
CIDS="$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import spec; print(" ".join(str(c) for c in spec.pubchem_cids()))' "$HERE/scripts")"
for cid in $CIDS; do
  curl -sf "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/$cid/property/Title,MolecularFormula,MolecularWeight/JSON" \
    -o "$RAW/pubchem/cid_$cid.json"
  sleep 0.3
done

# CIAAW abridged standard atomic weights (elements).
curl -sfL "https://www.ciaaw.org/abridged-atomic-weights.htm" -o "$RAW/ciaaw/abridged.htm"

# NGSP page with the IFCC-NGSP master equation (Table 2).
curl -sfL "https://ngsp.org/ifccngsp.asp" -o "$RAW/ngsp/ifccngsp.html"

# NHANES 2021-2023 laboratory documentation (published conversion factors, used as a cross-check
# and as the primary source for triglycerides and AMH).
for f in TRIGLY_L TCHOL_L HDL_L GLU_L BIOPRO_L INS_L FOLATE_L TST_L ALB_CR_L; do
  curl -sfL "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/$f.htm" -o "$RAW/nhanes-docs-labunits/$f.htm"
done

# UCUM essence (atoms and prefixes), used only at build time to validate UCUM code strings.
# It is not redistributed in this repository.
curl -sfL "https://raw.githubusercontent.com/ucum-org/ucum/main/ucum-essence.xml" -o "$RAW/ucum/ucum-essence.xml"


# Full texts used for quoted statements (Lp(a), insulin, enzyme unit). Audit copies only; build.py does not read them.
mkdir -p "$RAW/labunits-europepmc"
for p in PMC9639807 PMC9279959 PMC6152246; do
  curl -sf "https://www.ebi.ac.uk/europepmc/webservices/rest/$p/fullTextXML" -o "$RAW/labunits-europepmc/$p.xml"
done

# Sources for reading "mil/mm3" and "mil/µL" by language (added in 1.1.0; cited only, nothing numeric is read).
mkdir -p "$RAW/unit-languages"
curl -sfL "https://web.archive.org/web/20090109175010id_/http://www.cc.nih.gov/ccc/patient_education/pepubs_sp/cbcsp.pdf" \
  -o "$RAW/unit-languages/nih-cc-cbc-es.pdf"
curl -sfL "https://dlmp.uw.edu/test-guide/view/RBC" -o "$RAW/unit-languages/uw-dlmp-rbc.html"
curl -sfL "https://es.wiktionary.org/wiki/mil" -o "$RAW/unit-languages/eswiktionary-mil.html"
curl -sfL "https://dexonline.ro/definitie/mie" -o "$RAW/unit-languages/dexonline-mie.html"
curl -sfL "https://dexonline.ro/definitie/milion" -o "$RAW/unit-languages/dexonline-milion.html"

echo "fetched into $RAW"

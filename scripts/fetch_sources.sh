#!/usr/bin/env bash
# Download every raw source that scripts/build.py reads.
# Raw files go to ../_raw/<source>/ (outside this repo, never committed).
# Access date for release 1.0.0: 2026-11-25; the language-reading sources added in 1.1.0: 2026-11-26; the German sources added in 1.2.0: 2026-11-27.
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


# Sources for German, Austrian and Swiss count spellings (added in 1.2.0; cited only, nothing numeric is read).
mkdir -p "$RAW/unit-languages-de"
UA="Mozilla/5.0"
curl -sfL -A "$UA" "https://de.wiktionary.org/w/index.php?title=Tsd.&action=raw" -o "$RAW/unit-languages-de/dewiktionary-tsd.txt"
curl -sfL -A "$UA" "https://de.wiktionary.org/w/index.php?title=Mio.&action=raw" -o "$RAW/unit-languages-de/dewiktionary-mio.txt"
curl -sfL -A "$UA" "https://de.wikipedia.org/w/index.php?title=Blutbild&action=raw" -o "$RAW/unit-languages-de/dewikipedia-blutbild.txt"
curl -sfL -A "$UA" "https://de.wikipedia.org/w/index.php?title=Leukozyt&action=raw" -o "$RAW/unit-languages-de/dewikipedia-leukozyt.txt"
curl -sfL -A "$UA" "https://www.gesundheit.gv.at/labor/laborwerte/blutbild/leukozyten" -o "$RAW/unit-languages-de/gesundheit-gv-leukozyten.html"
curl -sfL -A "$UA" "https://www.gesundheit.gv.at/labor/laborwerte/blutbild/erythrozyten" -o "$RAW/unit-languages-de/gesundheit-gv-erythrozyten.html"
curl -sfL -A "$UA" "https://zlm.insel.ch/fileadmin/Zentrum_f%C3%BCr_Labormedizin/Dokumente/Akkreditierungsurkunden_und_Referenzwerte/Referenzwerte__Morphologische_Haematologie.pdf" \
  -o "$RAW/unit-languages-de/insel-zlm-haematologie.pdf"
curl -sfL -A "$UA" "https://www.uniklinik-ulm.de/fileadmin/default/09_Sonstige/Klinische-Chemie/Seiteninhalte/Seiteninhalte_B/Kleines_Blutbild_und_maschinelle_Differenzierung_FB-PAE_6_BB_OE.pdf" \
  -o "$RAW/unit-languages-de/ukulm-kleines-blutbild.pdf"
curl -sfL -A "$UA" "https://www.med.uni-magdeburg.de/unimagdeburg_mm/Downloads/Kliniken/KHAE/haemalabor/InfoLabParm.pdf" \
  -o "$RAW/unit-languages-de/ukmd-laborparameter.pdf"
curl -sfL -A "$UA" "https://www.mhh.de/fileadmin/mhh/zentrallabor-zla/downloads/LVZ_ZLA_Referenzbereiche.pdf" \
  -o "$RAW/unit-languages-de/mhh-zla-referenzbereiche.pdf"

echo "fetched into $RAW"

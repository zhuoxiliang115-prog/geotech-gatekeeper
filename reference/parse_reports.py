"""
Prototype parser for Macquarie Geotech-style lab report PDFs.

Handles two report types found in these bundled PDFs:
  - "Determination of Emerson class number of a soil"
  - "Determination of the particle size distribution of a soil..."

Each PDF page = one report. Report type is detected from the title line,
then a type-specific extractor pulls the relevant fields.

Usage:
    python3 parse_reports.py <input.pdf> [<input2.pdf> ...]

Outputs (in ./output/):
    emerson_results.csv
    psd_results.csv
"""

import sys
import re
import csv
from pathlib import Path
import pdfplumber

OUT_DIR = Path("/home/claude/output")
OUT_DIR.mkdir(exist_ok=True)

# ---------- shared helpers ----------

FIELD_PATTERNS = {
    "mg_sample_no": r"MG Sample No\.\s*([A-Za-z0-9\-]+)",
    "mg_project_no": r"MG Project No\.\s*([A-Za-z0-9\-]+)",
    "client": r"Client\s+([^\n]+?)\s+MG Sample No",
    "project": r"Project\s+([^\n]+?)\s+Date Sampled",
    "sample_id": r"Sample ID\s+([^\n]+?)\s+Date Received",
    "date_sampled": r"Date Sampled\s+(\d{1,2}/\d{1,2}/\d{4})",
    "date_received": r"Date Received\s+(\d{1,2}/\d{1,2}/\d{4})",
    "date_tested": r"Date Tested\s+(\d{1,2}/\d{1,2}/\d{4})",
    "report_no": r"Report No\.\s+([A-Za-z0-9\-_]+)",
    "sample_description": r"Sample Description\s+([^\n]+)",
}


def extract_common_fields(text):
    fields = {}
    for key, pattern in FIELD_PATTERNS.items():
        m = re.search(pattern, text)
        fields[key] = m.group(1).strip() if m else None
    return fields


def get_report_title(text):
    lines = text.split("\n")
    return lines[1].strip() if len(lines) > 1 else ""


# ---------- Emerson parser ----------

def parse_emerson_page(text):
    fields = extract_common_fields(text)
    class_m = re.search(r"Emerson Class Number:\s*(\d+)", text)
    water_m = re.search(r"Type of Water Used:\s*([A-Za-z]+)", text)
    notes_m = re.search(r"Sample Description[^\n]+\n.*?Emerson Class Number", text, re.S)
    # crude notes capture: look for a line after "Notes" heading before signature block
    notes_section = re.search(r"\nNotes\n(.*?)\nAccredited", text, re.S)
    notes = notes_section.group(1).strip() if notes_section else ""
    fields["emerson_class"] = int(class_m.group(1)) if class_m else None
    fields["water_type"] = water_m.group(1) if water_m else None
    fields["notes"] = notes if notes else None
    return fields


EMERSON_DISPERSION = {
    1: "High", 2: "High",
    3: "Medium - remoulded samples may be dispersive",
    4: "Low", 5: "Low", 6: "Low", 7: "Very Low", 8: "Very Low",
}


# ---------- Atterberg / Plasticity Index parser ----------

def parse_atterberg_page(text):
    fields = extract_common_fields(text)

    def grab(label):
        m = re.search(re.escape(label) + r"\s*\(%\)\s*([\d.]+|Non-Plastic|Unobtainable)", text)
        return m.group(1) if m else None

    ll_raw = grab("Liquid Limit")
    pl_raw = grab("Plastic Limit")
    pi_raw = grab("Plasticity Index")
    ls_m = re.search(r"Linear Shrinkage \(%\)\s*([\d.]+|Unobtainable)", text)

    def to_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    fields["liquid_limit"] = to_float(ll_raw)
    fields["plastic_limit"] = to_float(pl_raw)
    fields["plasticity_index"] = to_float(pi_raw)
    fields["linear_shrinkage_pct"] = to_float(ls_m.group(1)) if ls_m else None
    fields["non_plastic"] = (ll_raw == "Non-Plastic")

    # A-line classification (AS1726 / Casagrande): PI = 0.73(LL-20)
    if fields["liquid_limit"] is not None and fields["plasticity_index"] is not None:
        a_line_pi = 0.73 * (fields["liquid_limit"] - 20)
        fields["a_line_pi_at_this_ll"] = round(a_line_pi, 1)
        fields["above_a_line"] = fields["plasticity_index"] > a_line_pi
        fields["classification_zone"] = "CLAY" if fields["above_a_line"] else "SILT"
    else:
        fields["a_line_pi_at_this_ll"] = None
        fields["above_a_line"] = None
        fields["classification_zone"] = "Non-Plastic" if fields["non_plastic"] else None

    return fields


# ---------- PSD parser ----------

def parse_psd_page(page):
    text = page.extract_text() or ""
    fields = extract_common_fields(text)

    sieve_sizes, passing_pct = [], []
    for table in page.extract_tables():
        for row in table:
            if not row or row[0] is None:
                continue
            cell0 = str(row[0])
            # the sieve-size column looks like "200\n75\n63\n37.5\n..."
            if re.match(r"^\d", cell0.strip()) and "\n" in cell0:
                sizes = [float(x) for x in cell0.split("\n") if x.strip()]
                pct = [float(x) for x in str(row[1]).split("\n") if x.strip()]
                if len(sizes) == len(pct) and len(sizes) > 5:
                    sieve_sizes, passing_pct = sizes, pct

    fields["sieve_sizes_mm"] = sieve_sizes
    fields["passing_pct"] = passing_pct
    return fields


# ---------- main dispatch ----------

def process_pdf(path):
    emerson_rows, psd_rows, atterberg_rows = [], [], []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            title = get_report_title(text)
            if title.startswith("Determination of Emerson class number"):
                row = parse_emerson_page(text)
                row["source_pdf"] = path.name
                row["page"] = i + 1
                row["dispersion_potential"] = EMERSON_DISPERSION.get(row["emerson_class"])
                emerson_rows.append(row)
            elif title.startswith("Determination of the particle size distribution"):
                row = parse_psd_page(page)
                row["source_pdf"] = path.name
                row["page"] = i + 1
                psd_rows.append(row)
            elif title.startswith("Determination of the liquid limit"):
                row = parse_atterberg_page(text)
                row["source_pdf"] = path.name
                row["page"] = i + 1
                atterberg_rows.append(row)
    return emerson_rows, psd_rows, atterberg_rows


def write_emerson_csv(rows, path):
    cols = ["source_pdf", "page", "mg_sample_no", "sample_id", "project",
            "date_sampled", "date_tested", "sample_description",
            "emerson_class", "dispersion_potential", "water_type", "notes"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})


def write_psd_csv(rows, path):
    # long format: one row per sieve size per sample, easy to chart
    cols = ["source_pdf", "page", "mg_sample_no", "sample_id",
            "sample_description", "sieve_mm", "passing_pct"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            for size, pct in zip(r["sieve_sizes_mm"], r["passing_pct"]):
                w.writerow({
                    "source_pdf": r["source_pdf"], "page": r["page"],
                    "mg_sample_no": r["mg_sample_no"], "sample_id": r["sample_id"],
                    "sample_description": r["sample_description"],
                    "sieve_mm": size, "passing_pct": pct,
                })


def write_atterberg_csv(rows, path):
    cols = ["source_pdf", "page", "mg_sample_no", "sample_id", "sample_description",
            "liquid_limit", "plastic_limit", "plasticity_index", "linear_shrinkage_pct",
            "non_plastic", "a_line_pi_at_this_ll", "above_a_line", "classification_zone"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})


if __name__ == "__main__":
    pdf_paths = [Path(p) for p in sys.argv[1:]]
    all_emerson, all_psd, all_atterberg = [], [], []
    for p in pdf_paths:
        e, s, a = process_pdf(p)
        all_emerson.extend(e)
        all_psd.extend(s)
        all_atterberg.extend(a)
        print(f"{p.name}: {len(e)} Emerson, {len(s)} PSD, {len(a)} Atterberg reports parsed")

    write_emerson_csv(all_emerson, OUT_DIR / "emerson_results.csv")
    write_psd_csv(all_psd, OUT_DIR / "psd_results.csv")
    write_atterberg_csv(all_atterberg, OUT_DIR / "atterberg_results.csv")
    print(f"\nWrote {OUT_DIR/'emerson_results.csv'} ({len(all_emerson)} rows)")
    print(f"Wrote {OUT_DIR/'psd_results.csv'} ({sum(len(r['sieve_sizes_mm']) for r in all_psd)} rows)")
    print(f"Wrote {OUT_DIR/'atterberg_results.csv'} ({len(all_atterberg)} rows)")

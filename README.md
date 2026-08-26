# MediAssist - Scope & Progress

## What it does
Explains content already present in discharge summaries, lab reports, and 
typed prescriptions. A patient-facing RAG tool that answers factual 
questions grounded strictly in the uploaded document.

## What it does NOT do
- No diagnosis
- No treatment recommendations
- No dosage advice
- No prognosis speculation

## Document types supported
- Discharge summaries
- Lab reports
- Typed prescriptions
- Text-native PDFs only (no OCR/scanned documents)

## Build status
Phases 0-3 complete: scope defined, synthetic test dataset generated 
(24 documents across 3 types + eval_qa.json ground truth), PDF ingestion 
built (src/ingest.py), section-aware chunking built (src/chunker.py). 
Phases 4 onward (embeddings, retrieval, generation, refusal layer, 
eval harness, demo UI) not yet started.

---

## Limitations identified and resolved

**1. Bold-based header detection was font-name-only.**  
Initial version checked `"Bold" in span["font"]`, which only catches 
PDFs where bold is encoded in the font name (e.g. "Helvetica-Bold"). 
Real-world PDFs (Word exports, EMR systems) often mark bold via a 
separate flags bitmask instead. Fixed by checking both signals: 
`"Bold" in span["font"] or bool(span["flags"] & 2**4)`.

**2. Table column headers were misclassified as section headers.**  
PyMuPDF correctly identifies table header cells (e.g. "Test", "Result", 
"Reference Range") as bold, which caused them to be wrongly tagged as 
section titles. Fixed with `fix_table_header_rows()`, which detects 
consecutive runs of bold elements and keeps only the first as a real 
header, demoting the rest and tagging them as `is_table_header` for 
downstream use.

**3. Lab table chunking assumed a fixed 3-column layout.**  
Originally hardcoded to expect exactly Test/Result/Reference Range. 
Rebuilt to dynamically detect column count from the table header row, 
so it generalizes to N-column tables rather than breaking on anything 
non-standard. A 3-column layout still gets clean natural-language 
formatting; other column counts fall back to a generic pipe-separated 
format.

**4. Lab section detection only matched exact "LAB RESULTS" text.**  
Testing against a prescription (titled "LAB VALUES") exposed that the 
original check was too narrow. Replaced with a keyword list covering 
common real-world naming variants (LAB RESULTS, LABORATORY RESULTS, LAB 
VALUES, LABORATORY VALUES, LABS, LABORATORY DATA, LABORATORY FINDINGS, 
PATHOLOGY RESULTS, PATHOLOGY REPORT, TEST RESULTS, DIAGNOSTIC RESULTS), 
matched as a substring so modifiers like "(FASTING)" don't break 
detection.

**5. Chunker assumed all lab data arrives as a table.**  
Testing against the prescription document surfaced a case the chunker 
didn't handle: prescription lab values are already single-line 
"Test: Result (Reference Range: X-Y)" entries, not a rendered table, 
so no table-header row exists to detect a column count from. Added a 
fallback (`chunk_lab_lines_no_table()`) that treats each line as its 
own chunk directly when zero table-header columns are detected.

---

## Known limitations / not addressed

- **Handwritten prescriptions are explicitly out of scope.** Handwriting 
  recognition for medical documents is a separate, hard OCR/HTR problem 
  with high misread risk on dosages — given this system's core safety 
  requirement (grounded, non-hallucinated answers), ingesting unreliable 
  OCR output would undermine the entire trust model. Would require a 
  dedicated, separately-validated HTR pipeline.
- **Consecutive real section headers with no body text between them 
  would be incorrectly merged.** `fix_table_header_rows()` assumes only 
  the first element in a run of consecutive bold elements is a genuine 
  section header — this holds for every document in the test set, but 
  isn't provably safe for an arbitrary real hospital PDF where two 
  section titles might appear back-to-back.
- **Lab table formatting still assumes Test/Result/Reference-Range 
  semantics for its clean 3-column output.** Column count is now 
  detected dynamically, but the system doesn't read the actual header 
  row TEXT to know which column is which — a table with a different 
  3-column meaning (e.g. Test/Flag/Result) would still be formatted as 
  if it were Test/Result/Range.
- **Section-name keyword matching is a known list, not fully general.** 
  Covers common real-world naming variants but would miss an unlisted 
  variant entirely (e.g. a hospital using "CHEM PANEL" as a section 
  title with no other lab-related keyword present).

## Success metrics (to be measured in Phase 8)
- Retrieval hit rate
- Hallucination rate
- Refusal accuracy (on advice-seeking queries)
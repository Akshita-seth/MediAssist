import fitz  # PyMuPDF - reads PDF structure (text, fonts, bold, position)


def extract_text_simple(pdf_path):
    """
    Quick plain-text extraction - no structure, no font info.
    Useful for fast sanity checks, not used in the main pipeline.
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text


def extract_structured(pdf_path):
    """
    Extracts every text span from the PDF along with whether it's bold.
    Bold text is our signal for "this might be a section header".
    Returns a list of {"text": ..., "is_header": True/False}, in reading order.
    Note: this over-labels bold table-header cells (e.g. "Test", "Result")
    as headers too - fix_table_header_rows() corrects that afterward.
    """
    doc = fitz.open(pdf_path)
    elements = []
    for page in doc:
        page_dict = page.get_text("dict")
        for block in page_dict["blocks"]:
            if "lines" not in block:
                continue  # skip non-text blocks (e.g. images)
            for line in block["lines"]:
                for span in line["spans"]:
                    is_bold = "Bold" in span["font"] or bool(span["flags"] & 2**4)
                    elements.append({
                        "text": span["text"],
                        "is_header": is_bold
                    })
    doc.close()
    return elements




def fix_table_header_rows(elements):
   """
    Corrects extract_structured()'s over-labeling: when several bold
    elements appear back-to-back (e.g. a table's "Test / Result /
    Reference Range" header row), only the FIRST one in that run is a
    real section header - the rest are demoted to is_header: False.
    """
   cleaned = []
   i = 0
   while i < len(elements):
        el = elements[i]
        if el["is_header"]:
            run_start = i
            while i < len(elements) and elements[i]["is_header"]:
                i += 1
            run = elements[run_start:i]

            run[0]["is_table_header"] = False   # the real section header
            cleaned.append(run[0])

            for extra in run[1:]:               # the demoted table-column headers
                extra["is_header"] = False
                extra["is_table_header"] = True
                cleaned.append(extra)
        else:
            el["is_table_header"] = False
            cleaned.append(el)
            i += 1
   return cleaned



def parse_pdf(pdf_path):
    """
    Public entry point for this module - the ONE function other files
    (chunker.py, etc.) should call. Runs the full extraction + cleanup
    pipeline and returns the final, corrected list of elements.
    """
    elements = extract_structured(pdf_path)
    elements = fix_table_header_rows(elements)
    return elements


if __name__ == "__main__":
    # Quick manual test - swap the filename to check different doc types
    elements = parse_pdf("data/raw_pdfs/prescription_01.pdf")
    for el in elements:
        marker = "[HEADER]" if el["is_header"] else "        "
        print(f"{marker} {el['text']}")
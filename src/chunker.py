from ingest import parse_pdf


LAB_SECTION_KEYWORDS = [
    "LAB RESULTS", "LABORATORY RESULTS", "LAB VALUES", "LABORATORY VALUES",
    "LABS", "LABORATORY DATA", "LABORATORY FINDINGS",
    "PATHOLOGY RESULTS", "PATHOLOGY REPORT",
    "TEST RESULTS", "DIAGNOSTIC RESULTS"
]


def is_lab_section(section_name):
    """
    Checks if a section name matches any known lab-results-style
    keyword (substring match, so "LAB RESULTS (FASTING)" still
    matches "LAB RESULTS"). Not fully general - covers common
    real-world naming variants we know of, not every possible one.
    """
    section_upper = section_name.upper()
    return any(keyword in section_upper for keyword in LAB_SECTION_KEYWORDS)


def group_by_section(elements):
    """
    Groups the flat element list into sections, keeping each section's
    RAW elements (not yet joined into one string) - needed so
    chunk_lab_results() can inspect is_table_header flags per element.
    """
    sections = []
    current_section = "UNTITLED"
    current_elements = []

    for el in elements:
        if el["is_header"]:
            if current_elements:
                sections.append({
                    "section": current_section,
                    "elements": current_elements
                })
            current_section = el["text"]
            current_elements = []
        else:
            current_elements.append(el)

    if current_elements:
        sections.append({
            "section": current_section,
            "elements": current_elements
        })

    return sections


def chunk_lab_results(section_elements):
    """
    Splits a lab-results-style section into one chunk per test row,
    detecting the column count dynamically from the table header run
    instead of assuming a fixed 3 columns.
    """
    column_count = 0
    for el in section_elements:
        if el["is_table_header"]:
            column_count += 1
        else:
            break

    if column_count == 0:
        return chunk_lab_lines_no_table(section_elements)

    data_elements = section_elements[column_count:]

    chunks = []
    i = 0
    while i < len(data_elements):
        if i + (column_count - 1) < len(data_elements):
            row = [data_elements[i + j]["text"] for j in range(column_count)]
            result_value = row[1] if column_count > 1 else row[0]
            if any(char.isdigit() for char in result_value):
                if column_count == 3:
                    content = f"{row[0]}: {row[1]} (Reference Range: {row[2]})"
                else:
                    content = " | ".join(row)
                chunks.append({"section": "LAB RESULTS", "content": content})
                i += column_count
                continue
        chunks.append({"section": "LAB RESULTS", "content": data_elements[i]["text"]})
        i += 1
    return chunks

def chunk_lab_lines_no_table(section_elements):
    """
    Handles lab sections that aren't tables - already single-line
    "Name: Value (Reference Range: X-Y)" format, one test per line.
    Each line becomes its own chunk directly, no splitting needed.
    """
    chunks = []
    for el in section_elements:
        chunks.append({"section": "LAB RESULTS", "content": el["text"]})
    return chunks

def build_chunks(pdf_path):
    """
    Public entry point for this module. Runs the full chunking pipeline:
    parses the PDF, groups elements into sections, then produces final
    chunks - lab-results-style sections get split per-test, everything
    else becomes one chunk per section.
    """
    elements = parse_pdf(pdf_path)
    sections = group_by_section(elements)

    final_chunks = []
    for sec in sections:
        if is_lab_section(sec["section"]):
            final_chunks.extend(chunk_lab_results(sec["elements"]))
        else:
            content = "\n".join(el["text"] for el in sec["elements"])
            final_chunks.append({"section": sec["section"], "content": content})

    return final_chunks


if __name__ == "__main__":
    chunks = build_chunks("data/raw_pdfs/discharge_01.pdf")
    last_section = None
    for chunk in chunks:
        if chunk['section'] != last_section:
            print(f"\n=== {chunk['section']} ===")
            last_section = chunk['section']
        print(chunk['content'])


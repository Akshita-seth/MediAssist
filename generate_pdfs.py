from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import random
import re

def parse_lab_line(line):
    match = re.match(r"^(.*?):\s*(.*?)\s*\(Reference Range:\s*(.*?)\)$", line)
    if match:
        return [match.group(1).strip(), match.group(2).strip(), match.group(3).strip()]
    return [line, "", ""]

def build_lab_table(lab_lines):
    data = [["Test", "Result", "Reference Range"]] + [parse_lab_line(l) for l in lab_lines]
    table = Table(data, colWidths=[180, 140, 160])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    return table

def text_to_pdf(text_content, output_path, seed=None):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    rng = random.Random(seed)
    render_styles = ["bold_large", "bold_only", "bold_underline"]
    lines = text_content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            story.append(Spacer(1, 6))
            i += 1
            continue
        if line.startswith('## '):
            header_text = line[3:].strip()
            style_choice = rng.choice(render_styles)
            if style_choice == "bold_large":
                html = f"<b><font size=13>{header_text}</font></b>"
            elif style_choice == "bold_only":
                html = f"<b>{header_text}</b>"
            else:
                html = f"<b><u>{header_text}</u></b>"
            story.append(Paragraph(html, styles['Normal']))
            story.append(Spacer(1, 4))
            if "LAB RESULTS" in header_text.upper():
                lab_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('## '):
                    lab_lines.append(lines[i].strip())
                    i += 1
                story.append(build_lab_table(lab_lines))
                story.append(Spacer(1, 8))
                continue
        else:
            story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 4))
        i += 1
                
    doc.build(story)

if __name__ == "__main__":
       txt_folder = "data/synthetic_texts"
       pdf_folder = "data/raw_pdfs"
       os.makedirs(pdf_folder, exist_ok=True)

       for i, filename in enumerate(os.listdir(txt_folder)):
           if filename.endswith('.txt'):
                with open(os.path.join(txt_folder, filename)) as f:
                     content = f.read()
                output_name = filename.replace('.txt', '.pdf')
                text_to_pdf(content, os.path.join(pdf_folder, output_name), seed=i)
                print(f"Converted: {filename} → {output_name}")   
            
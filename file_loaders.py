import pymupdf
from docx import Document


def load_pdf(path):
    output = ""
    for page_number, page in enumerate(path):
        text = page.get_text()
        output += f"Page {page_number + 1}: {text}\n"
    return output

def load_txt(path):
    with open(path, 'r') as file:
        text = file.read()
    return text

def load_markdown(path):
    with open(path, 'r') as file:
        text = file.read()
    return text

def load_docx(path):
    doc = Document(path)
    output = ""
    for paragraph in doc.paragraphs:
        output += f"{paragraph.text}\n"
    return output

def universal_file_loader(path):
    if path.endswith('.pdf'):
        doc = pymupdf.open(path)
        return load_pdf(doc)
    elif path.endswith('.txt'):
        return load_txt(path)
    elif path.endswith('.md'):
        return load_markdown(path)
    elif path.endswith('.docx'):
        return load_docx(path)
    else:
        raise ValueError(f"Unsupported file format: {path}")

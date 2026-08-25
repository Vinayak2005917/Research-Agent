import pymupdf
from docx import Document
from pandas import read_csv, read_excel
import json


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

def load_csv(path):
    df = read_csv(path)
    return df.to_string()

def load_excel(path):
    df = read_excel(path)
    return df.to_string()

def load_json(path):
    with open(path, 'r') as file:
        data = json.load(file)
    return json.dumps(data, indent=4)

def universal_file_loader(path):
    path_lower = path.lower()
    if path_lower.endswith('.pdf'):
        doc = pymupdf.open(path)
        return load_pdf(doc)
    elif path_lower.endswith('.txt'):
        return load_txt(path)
    elif path_lower.endswith('.md'):
        return load_markdown(path)
    elif path_lower.endswith('.docx'):
        return load_docx(path)
    elif path_lower.endswith('.csv'):
        return load_csv(path)
    elif path_lower.endswith('.xlsx'):
        return load_excel(path)
    elif path_lower.endswith('.json'):
        return load_json(path)
    else:
        raise ValueError(f"Unsupported file format: {path}")

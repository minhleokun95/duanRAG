"""Buoc 1: Trich xuat text tu file quy che (PDF/Word) trong data/raw -> data/processed."""
import pathlib
import re

import pdfplumber
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def read_docx(path):
    doc = Document(path)
    lines = []
    for block in doc.iter_inner_content():  # giu dung thu tu doan van va bang
        if isinstance(block, Paragraph):
            lines.append(block.text)
        elif isinstance(block, Table):
            for row in block.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def read_pdf(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def clean(text):
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    files = [f for f in RAW.iterdir() if f.suffix.lower() in (".docx", ".pdf")]
    if not files:
        print(f"Chua co file nao trong: {RAW}")
        print("Hay copy file quy che (.pdf hoac .docx) vao thu muc do roi chay lai.")
        return
    for f in sorted(files):
        text = read_docx(f) if f.suffix.lower() == ".docx" else read_pdf(f)
        text = clean(text)
        (OUT / f"{f.stem}.txt").write_text(text, encoding="utf-8")
        status = "OK" if len(text) > 200 else "CANH BAO: text rat ngan (PDF scan? can OCR)"
        print(f"{status}: {f.name} -> {len(text)} ky tu")


if __name__ == "__main__":
    main()

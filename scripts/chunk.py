"""Buoc 2: Chia van ban theo tung Dieu (cat tiep theo Khoan neu qua dai) -> data/chunks.json."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "processed"
OUT = ROOT / "data" / "chunks.json"
MAX_CHARS = 1500

RE_CHUONG = re.compile(r"^Chương\s+[IVXLC\d]+", re.I)
RE_DIEU = re.compile(r"^Điều\s+(\d+)\s*[.:]?\s*(.*)$", re.I)
RE_KHOAN = re.compile(r"^\d+\s*[.)]\s")


def split_long(header, lines):
    parts, cur = [], ""
    for line in lines:
        if RE_KHOAN.match(line) and cur and len(cur) + len(line) > MAX_CHARS:
            parts.append(cur.strip())
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur.strip())
    return [f"{header}\n{p}" for p in parts] or [header]


import unicodedata


def process(doc, text):
    text = unicodedata.normalize("NFC", text)
    sections, chuong, cur = [], "", None
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = RE_DIEU.match(line)
        if m:
            cur = {"chuong": chuong, "dieu": m.group(1),
                   "title": m.group(2), "lines": []}
            sections.append(cur)
        elif RE_CHUONG.match(line):
            chuong, cur = line, None
        elif cur:
            cur["lines"].append(line)

    chunks = []
    for s in sections:
        header = f"Điều {s['dieu']}. {s['title']}".strip()
        for i, content in enumerate(split_long(header, s["lines"])):
            chunks.append({
                "id": f"{doc}_d{s['dieu']}_{i}",
                "doc": doc,
                "chuong": s["chuong"],
                "dieu": s["dieu"],
                "text": content,
            })
    return chunks


def main():
    files = sorted(IN.glob("*.txt"))
    if not files:
        print(f"Chua co file .txt trong {IN}. Hay chay extract.py truoc.")
        return
    all_chunks = []
    for f in files:
        c = process(f.stem, f.read_text(encoding="utf-8"))
        print(f"{f.name}: {len(c)} chunks")
        all_chunks += c
    if not all_chunks:
        print("0 chunk: khong tim thay dong bat dau bang 'Dieu X'. Gui 15 dong dau cua file .txt cho tro ly de chinh lai.")
        return
    OUT.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    lens = [len(c["text"]) for c in all_chunks]
    print(f"Tong: {len(all_chunks)} | ngan nhat: {min(lens)} | dai nhat: {max(lens)} ky tu")
    print(f"Da luu: {OUT}")


if __name__ == "__main__":
    main()

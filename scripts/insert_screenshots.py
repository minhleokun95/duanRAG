"""
Script ho tro chen anh chup man hinh he thong that vao ca 2 tai lieu bao cao:
1. Bao_Cao_Do_An_Tot_Nghiep_RAG_Hoc_Vu_Cap_Nhat.docx
2. Chuc_Nang_Va_Hoat_Dong_He_Thong_RAG.docx

Cach su dung:
1. Chup anh he thong theo huong dan va luu vao thu muc 'images/':
   - images/hinh_2_1.png (hoac .jpg) -> Giao dien Tab 1: Chatbot RAG
   - images/hinh_2_2.png (hoac .jpg) -> Giao dien Tab 2: Case Analyzer
   - images/hinh_2_3.png (hoac .jpg) -> Giao dien Tab 3: So tay Dieu khoan
   - images/hinh_2_4.png (hoac .jpg) -> Giao dien Tab 4: Mo phong tinh diem
2. Chay lenh: python scripts/insert_screenshots.py
3. Script se tu dong chen cac anh that vao dung khung tuong ung trong Word!
"""
import os
import pathlib
import docx
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_KEYS = {
    "hinh_2_1": ["GIAO DIỆN TRỢ LÝ AI HỎI ĐÁP", "RAG CHATBOT", "TAB 1"],
    "hinh_2_2": ["CỐ VẤN TÌNH HUỐNG HỌC VỤ", "CASE ANALYZER", "TAB 2"],
    "hinh_2_3": ["SỔ TAY QUY CHẾ", "CLAUSE CODEX", "TAB 3"],
    "hinh_2_4": ["MÔ PHỎNG & TÍNH ĐIỂM", "ACADEMIC SIMULATOR", "TAB 4"]
}

def find_image(key):
    for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"]:
        p = IMG_DIR / f"{key}{ext}"
        if p.exists():
            return p
    return None

def process_document(docx_path):
    if not docx_path.exists():
        print(f"[-] Khong tim thay file: {docx_path.name}")
        return
    
    doc = docx.Document(docx_path)
    inserted_count = 0
    
    for table in doc.tables:
        if not table.rows or not table.rows[0].cells:
            continue
        cell = table.rows[0].cells[0]
        text = cell.text
        
        for key, markers in IMAGE_KEYS.items():
            if any(m in text for m in markers):
                img_path = find_image(key)
                if img_path:
                    # Xoa noi dung text huong dan va chen anh
                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(str(img_path), width=Inches(6.0))
                    print(f"  [+] Da chen {img_path.name} vao khung {key.upper()} trong {docx_path.name}")
                    inserted_count += 1
                else:
                    print(f"  [-] Chua tim thay file anh cho {key} (can file: images/{key}.png)")
                break

    if inserted_count > 0:
        doc.save(docx_path)
        print(f"[OK] Da cap nhat {inserted_count} anh vao {docx_path.name} thanh cong!\n")
    else:
        print(f"[!] Chua co anh moi nao duoc chen vao {docx_path.name}.\n")

def main():
    print("=" * 65)
    print("CHUONG TRINH TU DONG CHEN ANH CHUP HE THONG VAO BAO CAO WORD")
    print("=" * 65)
    print(f"Thu muc chua anh: {IMG_DIR}\n")
    
    process_document(ROOT / "Bao_Cao_Do_An_Tot_Nghiep_RAG_Hoc_Vu_Cap_Nhat.docx")
    process_document(ROOT / "Chuc_Nang_Va_Hoat_Dong_He_Thong_RAG.docx")

if __name__ == "__main__":
    main()


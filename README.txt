========================================================================
   RAG QUY DINH HOC VU - HE THONG TRO LY AI CO VAN HOC VU THONG MINH
========================================================================

1. GIOI THIEU 4 PHAN HE CHUYEN SAU
- 💬 Phân hệ 1: Tro ly AI Hoi dap (Chatbot RAG): Tra loi thac mac quy che bang ngon ngu
  tu nhien, trich dan chinh xac Dieu/Khoan, ho tro streaming chu thoi gian thuc (SSE)
  va co che viet lai cau hoi da luot (Contextual Query Rewriting).
- ⚖️ Phân hệ 2: Co van Tinh huong Hoc vu (Case Analyzer): Tich hop giua Rule Engine
  toan hoc va AI. Phan loai 4 cap do rui ro (🟢 An toan, 🟡 Luu y, 🟠 Canh bao,
  🔴 Buoc thoi hoc) chuan 100% theo Dieu 11 va de xuat lo trinh xu ly an toan.
- 📖 Phân hệ 3: So tay & AI Dien giai Dieu khoan (Clause Codex): Tra cuu toan bo 16
  Dieu quy che mau, kem tinh nang AI dien giai 4 khoi thong tin theo ngon ngu sinh vien.
- 🧮 Phân hệ 4: Bo Cong cu Mo phong & Tinh diem Hoc vu (Academic Simulator):
  Module app/rule_engine.py cung cap 4 cong cu tinh toan doc lap voi LLM:
  + Tinh diem tong ket hoc phan he 10 (10/30/60), diem chu va diem he 4 (Dieu 7 & 8).
  + Mo phong cai thien diem CPA khi hoc lai mon F hoac hoc cai thien (Dieu 6 Khoan 2).
  + Kiem tra tinh trang canh bao hoc vu va nguy co buoc thoi hoc (Dieu 11 & Dieu 4).
  + Kiem tra 4 dieu kien tot nghiep va quy dinh giam hang tot nghiep (Dieu 12 & 13).

2. CACH CHAY UNG DUNG VA KIEM THU
- Chay ung dung web:
  + Nhan dup chuot vao: run_app.bat
  + Trinh duyet se tu dong mo tai: http://127.0.0.1:8000
- Chay bo kiem thu tu dong (Automated Unit Tests):
  + Nhan dup chuot vao: run_tests.bat
  + Hoac go lenh: .\.venv\Scripts\python.exe -m unittest tests/test_system.py
- Chay kiem tra danh gia thuc nghiem (75 test cases benchmark):
  + Go lenh: .\.venv\Scripts\python.exe scripts/evaluate_rag.py

3. KICH HOAT AI TOAN DIEN (GOOGLE GEMINI MIEN PHI)
- Mo giao dien web, bam vao bieu tuong ⚙️ (Cai dat AI) o goc tren ben phai.
- Lay API Key mien phi tai: https://aistudio.google.com/apikey (chi can dang nhap Google).
- Dan API Key vao, bam "Kiem tra ket noi" roi bam "Luu cau hinh".
- (Luu y: Khi chua co API Key, he thong van tu dong hoat dong o che do Trich xuat du phong
   va chay toan bo bo cong cu Rule Engine ma khong he bi loi).

4. HUONG DAN CHEN ANH CHUP HE THONG VAO BAO CAO WORD
- Chup 4 anh man hinh theo huong dan trong bao cao va luu vao thu muc images/:
  + images/hinh_2_1.png -> Giao dien Tab 1 (Chatbot RAG)
  + images/hinh_2_2.png -> Giao dien Tab 2 (Case Analyzer)
  + images/hinh_2_3.png -> Giao dien Tab 3 (So tay Dieu khoan)
  + images/hinh_2_4.png -> Giao dien Tab 4 (Mo phong tinh diem)
- Chay lenh tu dong chen anh vao ca 2 file Word:
  python scripts/insert_screenshots.py

5. CAU TRUC THU MUC DU AN
- app/main.py             : Backend FastAPI (RAG, Streaming SSE, APIs AI & Rule Engine).
- app/rule_engine.py       : Bo suy dien quy tac hoc vu toan hoc tat dinh (Rule Engine).
- app/index.html          : Giao dien Web SPA da nhiem, responsive, Dark/Light mode.
- data/chunks.json        : Danh sach 16 chunks chia theo tung Dieu (Clause-level).
- data/chroma/            : Vector Database luu embeddings (intfloat/multilingual-e5-small).
- data/raw/               : File van ban quy che goc (.docx / .pdf).
- tests/test_system.py    : Bo kiem thu tu dong (Automated Unit & Integration Tests).
- scripts/extract.py      : Trich xuat van ban chuan hoa Unicode NFC.
- scripts/chunk.py        : Phan doan theo Dieu va chuan hoa Unicode NFC.
- scripts/embed_index.py  : Tao embeddings véc-tơ va luu vao ChromaDB.
- scripts/evaluate_rag.py : Danh gia thuc nghiem dinh luong (75 cau hoi, BM25 vs E5, Latency).
- scripts/insert_screenshots.py : Cong cu tu dong chen anh chup man hinh vao 2 file Word.
- Bao_Cao_Do_An_Tot_Nghiep_RAG_Hoc_Vu_Cap_Nhat.docx : Ban bao cao do an tot nghiep chinh thuc.
- Chuc_Nang_Va_Hoat_Dong_He_Thong_RAG.docx : Ban thuyet minh ky thuat va danh gia thuc nghiem.
- Dockerfile              : Cau hinh dong goi Container da nen tang.
========================================================================

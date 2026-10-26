========================================================================
   RAG QUY DINH HOC VU - HE THONG TRO LY AI CO VAN HOC VU THONG MINH
========================================================================

1. GIOI THIEU TINH NANG AI TICH HOP
- 💬 Tro ly AI Hoi dap (Chatbot RAG): Tra loi thac mac quy che bang ngon ngu
  tu nhien, trich dan chinh xac Dieu/Khoan, ho tro streaming chu thoi gian thuc.
- ⚖️ Co van Tinh huong Hoc vu (Case Analyzer): Sinh vien nhap tinh huong
  (GPA, so tin chi, so lan canh bao...), AI doi chieu quy che de danh gia
  muc do rui ro va de xuat lo trinh xu ly an toan.
- 📖 So tay & AI Dien giai Dieu khoan (Clause Explainer): Tra cuu toan bo 16
  Dieu quy che, kem tinh nang AI giai thich bang ngon ngu sinh vien de hieu.
- ⚙️ Quan ly & Kiem tra ket noi AI tren Web: Ho tro Google Gemini (Mien phi),
  OpenAI (GPT-4o-mini), Ollama Local, DeepSeek...

2. CACH CHAY UNG DUNG
- Buoc 1: Chay setup.bat (chi can chay 1 lan dau de cai thu vien).
- Buoc 2: Chay run_app.bat (hoac lenh: uvicorn app.main:app --reload)
- Buoc 3: Mo trinh duyet tai: http://127.0.0.1:8000

3. KICH HOAT AI TOAN DIEN (GOOGLE GEMINI MIEN PHI)
- Mo giao dien web, bam vao bieu tuong ⚙️ (Cai dat AI) o goc tren ben phai.
- Lay API Key mien phi tai: https://aistudio.google.com/apikey (chi can login Google).
- Dan API Key vao, bam "Kiem tra ket noi" roi bam "Luu cau hinh".
- (Hoac mo file .env trong thu muc goc va dien LLM_API_KEY=...).

4. CAU TRUC DU AN
- app/main.py           : Backend FastAPI tich hop RAG, Streaming SSE va cac API AI.
- app/index.html        : Giao dien Web hien dai, responsive, ho tro Dark/Light mode.
- data/raw/             : File quy che goc (.docx / .pdf).
- data/chunks.json      : Danh sach cac chunk quy che chia theo tung Dieu.
- data/chroma/          : Vector Database luu embeddings (intfloat/multilingual-e5-small).
- scripts/extract.py    : Trich xuat van ban tu Word/PDF.
- scripts/chunk.py      : Phan doan van ban theo Dieu/Khoan.
- scripts/embed_index.py: Tao embeddings va luu vao Chroma DB.
- scripts/search_test.py: Test truy van vector DB tren console.
========================================================================

"""
Buoc 5-7+: He thong RAG Quy dinh hoc vu tich hop AI chuyen sau.
Ho tro:
1. Tro ly AI Hoi dap quy che thoi gian thuc (RAG + Multi-turn Chat + Streaming SSE).
2. Co van AI Phan tich tinh huong hoc vu ca nhan (Case Analyzer).
3. So tay & AI Dien giai dieu khoan sinh vien (Clause Explainer).
4. Quan ly & kiem tra ket noi AI truc tiep tren web (Gemini, OpenAI, Ollama, DeepSeek).
"""
import json
import os
import pathlib
import sys
import time
from typing import Any, Dict, List, Optional

import chromadb
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# Thiet lap duong dan va cau hinh
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rule_engine import (
    CourseGradeInput,
    GPASimulatorInput,
    GraduationCheckInput,
    StatusCheckInput,
    calculate_course_grade,
    check_academic_status_rules,
    check_graduation_eligibility,
    classify_academic_standing,
    simulate_gpa_improvement,
)

ENV_PATH = ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)

DB_DIR = ROOT / "data" / "chroma"
CHUNKS_FILE = ROOT / "data" / "chunks.json"
MODEL_NAME = "intfloat/multilingual-e5-small"
COLLECTION_NAME = "quy_dinh_hoc_vu"

DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"

import unicodedata

def init_knowledge_base():
    """Khoi dong embedding model va ChromaDB, tu dong lap chi muc neu chua co."""
    global embedder, chroma_client
    print("Dang khoi dong he thong RAG & nap model embedding...")
    try:
        embedder = SentenceTransformer(MODEL_NAME, local_files_only=True)
    except Exception:
        embedder = SentenceTransformer(MODEL_NAME)
        
    DB_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        col = chroma_client.get_collection(COLLECTION_NAME)
        if col.count() > 0:
            print(f"He thong san sang voi {col.count()} chunk quy che hoc vu.")
            return col
    except Exception:
        pass
        
    print("[Tu dong lap chi muc] Dang khoi tao vector DB tu data/chunks.json...")
    col = chroma_client.get_or_create_collection(COLLECTION_NAME)
    if CHUNKS_FILE.exists():
        chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
        ids = [str(c["id"]) for c in chunks]
        texts = [c["text"] for c in chunks]
        passages = ["passage: " + unicodedata.normalize("NFC", t) for t in texts]
        vecs = embedder.encode(passages, normalize_embeddings=True).tolist()
        metas = [{"dieu": str(c.get("dieu", "")), "doc": c.get("doc", ""), "chuong": c.get("chuong", "")} for c in chunks]
        col.add(ids=ids, embeddings=vecs, documents=texts, metadatas=metas)
        print(f"[Tu dong lap chi muc] Da nap thanh cong {len(chunks)} chunks quy che vao ChromaDB.")
    return col

collection = init_knowledge_base()

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="RAG Quy định học vụ AI Assistant",
    description="Hệ thống hỏi đáp và tư vấn quy định học vụ đại học tích hợp AI thông minh",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prompts chuyen biet cho tung tinh nang AI
SYSTEM_PROMPT = (
    "Bạn là Trợ lý AI Cố vấn Học vụ Thông minh của Trường Đại học. "
    "Nhiệm vụ của bạn là giải đáp mọi thắc mắc của sinh viên về quy chế, quy định học vụ một cách chuẩn xác, tận tình và dễ hiểu.\n\n"
    "CÁC QUY TẮC CỐT LÕI BẮT BUỘC:\n"
    "1. DỰA TRÊN NGỮ CẢNH: Chỉ trả lời dựa trên phần NGỮ CẢNH (CÁC ĐIỀU KHOẢN) được cung cấp. Tuyệt đối không tự bịa đặt số liệu hay áp dụng quy định của trường khác.\n"
    "2. TRÍCH DẪN NGUỒN CỤ THỂ: Trong câu trả lời, luôn ghi rõ căn cứ pháp lý theo dạng **(Điều X, Khoản Y)** để sinh viên dễ dàng tra cứu.\n"
    "3. ĐỊNH DẠNG RÕ RÀNG: Dùng gạch đầu dòng, bảng số liệu nếu có, in đậm các mốc thời gian, số tín chỉ, điểm số trọng yếu.\n"
    "4. TRƯỜNG HỢP KHÔNG CÓ THÔNG TIN: Nếu ngữ cảnh không có thông tin giải đáp, hãy trả lời: "
    "\"Theo tài liệu quy định học vụ hiện có, tôi chưa tìm thấy quy định cụ thể cho trường hợp này. Bạn nên liên hệ trực tiếp Phòng Đào tạo hoặc Cố vấn học tập khoa để được hỗ trợ chính xác nhất.\"\n"
    "5. PHONG CÁCH: Chuyên nghiệp, khách quan, thấu hiểu và thân thiện với sinh viên."
)

CASE_ANALYZER_PROMPT = (
    "Bạn là Chuyên gia Cố vấn Học vụ Đại học. Nhiệm vụ của bạn là phân tích trường hợp học vụ cụ thể của một sinh viên "
    "dựa trên các ĐIỀU KHOẢN QUY CHẾ ĐƯỢC CUNG CẤP TRONG NGỮ CẢNH.\n\n"
    "Hãy phân tích và trình bày kết quả thành 3 phần rõ ràng:\n"
    "### 1. 🚦 ĐÁNH GIÁ MỨC ĐỘ RỦI RO & TÌNH TRẠNG HIỆN TẠI\n"
    "- Xác định mức độ: [🟢 Bình thường] / [🟡 Cần lưu ý] / [🟠 Cảnh báo cao] / [🔴 Nguy cơ bị xử lý học vụ/buộc thôi học].\n"
    "- Tóm tắt tình trạng học tập của sinh viên dựa trên các chỉ số (GPA, số tín chỉ, số lần cảnh báo...).\n\n"
    "### 2. ⚖️ CĂN CỨ THEO QUY CHẾ ĐÀO TẠO\n"
    "- Nêu rõ các điều khoản quy định chi phối trực tiếp tình huống này (ví dụ: Điều 4 Khoản 3, Điều 11 Khoản 2...).\n"
    "- Giải thích ngắn gọn quy chế quy định thế nào về giới hạn tín chỉ, điều kiện cảnh báo hay buộc thôi học.\n\n"
    "### 3. 🧭 LỜI KHUYÊN & LỘ TRÌNH HÀNH ĐỘNG KHUYẾN NGHỊ\n"
    "- Kỳ tiếp theo sinh viên ĐƯỢC PHÉP và NÊN đăng ký bao nhiêu tín chỉ?\n"
    "- Các môn học lại / cải thiện nên ưu tiên thế nào?\n"
    "- Các thủ tục học vụ cần làm (nộp đơn xin cứu xét, gặp cố vấn học tập, bảo lưu nếu cần...).\n\n"
    "Tuyệt đối căn cứ vào tài liệu được cung cấp, không phỏng đoán tùy tiện."
)

EXPLAIN_CLAUSE_PROMPT = (
    "Bạn là Trợ lý Học vụ Thân thiện. Hãy giải thích điều khoản quy chế sau đây cho sinh viên một cách dễ hiểu, sinh động và thực tế:\n"
    "Cấu trúc phản hồi:\n"
    "### 🎯 3 Ý CHÍNH CẦN NHỚ NHẤT\n"
    "(Tóm tắt 3 điểm cốt lõi nhất dưới dạng gạch đầu dòng ngắn gọn)\n\n"
    "### 💡 DIỄN GIẢI THEO NGÔN NGỮ SINH VIÊN\n"
    "(Giải thích lại bằng lời lẽ bình dân, dễ hiểu, tránh thuật ngữ văn bản quy phạm pháp luật phức tạp)\n\n"
    "### ⚠️ NHỮNG LỖI SINH VIÊN DỄ MẮC PHẢI & LƯU Ý SỐNG CÒN\n"
    "(Cảnh báo về hạn chót, thủ tục hoặc các sai lầm sinh viên hay gặp dẫn đến mất quyền lợi)\n\n"
    "### 📝 VÍ DỤ THỰC TẾ\n"
    "(Đưa ra 1 tình huống ví dụ thực tế cụ thể của một bạn sinh viên áp dụng điều này)."
)


def get_ai_config(override_key: Optional[str] = None, override_url: Optional[str] = None, override_model: Optional[str] = None) -> Dict[str, Any]:
    """Lay cau hinh AI hien tai tu tham so hoac tu file .env."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    
    api_key = (override_key or os.getenv("LLM_API_KEY", "")).strip()
    base_url = (override_url or os.getenv("LLM_BASE_URL", "")).strip()
    model = (override_model or os.getenv("LLM_MODEL", "")).strip() or DEFAULT_GEMINI_MODEL
    
    # Tu dong xac dinh base_url mac dinh neu nguoi dung quen dien
    if not base_url:
        if "gemini" in model.lower() or api_key.startswith("AIza") or api_key.startswith("AQ."):
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        elif api_key.startswith("sk-"):
            base_url = "https://api.openai.com/v1"
        else:
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            
    is_configured = bool(api_key)
    provider_name = "Google Gemini" if "generativelanguage" in base_url or "gemini" in model else (
        "OpenAI" if "openai.com" in base_url else (
            "Ollama (Local)" if "localhost" in base_url or "127.0.0.1" in base_url else "OpenAI Compatible"
        )
    )
    
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "is_configured": is_configured,
        "provider": provider_name
    }


def get_openai_client(override_key: Optional[str] = None, override_url: Optional[str] = None, override_model: Optional[str] = None):
    """Tao OpenAI client tu cau hinh."""
    config = get_ai_config(override_key, override_url, override_model)
    if not config["is_configured"]:
        return None, config
    from openai import OpenAI
    client = OpenAI(
        base_url=config["base_url"] or None,
        api_key=config["api_key"],
        timeout=30.0,
        max_retries=1
    )
    return client, config


def create_chat_completion_resilient(client, primary_model: str, messages: list, temperature: float = 0.2, max_tokens: int = 1500, stream: bool = False):
    """Goi chat completion voi co che tu dong fallback neu model bi 404, 429 quota hoac timeout."""
    candidates = [primary_model]
    if "gemini" in primary_model.lower():
        for fb in ["gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-3.8-flash"]:
            if fb not in candidates:
                candidates.append(fb)
                
    last_err = None
    for m in candidates:
        try:
            res = client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            return res, m
        except Exception as e:
            last_err = e
            print(f"[Model fallback] Model '{m}' loi: {e}. Dang thu model tiep theo...")
            continue
    raise last_err


def retrieve_chunks(question: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Truy xuat cac chunk tu Chroma vector DB voi chuan hoa ky tu tieng Viet NFC."""
    top_k = max(1, min(top_k, 10))
    norm_question = unicodedata.normalize("NFC", question.strip())
    vec = embedder.encode(["query: " + norm_question], normalize_embeddings=True)[0].tolist()
    res = collection.query(query_embeddings=[vec], n_results=top_k)
    sources = []
    if res and res.get("documents") and len(res["documents"]) > 0:
        for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            sources.append({
                "dieu": str(m.get("dieu", "?")),
                "doc": m.get("doc", ""),
                "chuong": m.get("chuong", ""),
                "score": round(1.0 - float(d), 3),
                "text": t
            })
    return sources


def generate_smart_fallback_answer(question: str, sources: List[Dict[str, Any]]) -> str:
    """Tao cau tra loi tong hop co cau truc khi chua cau hinh LLM API key."""
    if not sources:
        return "Tôi không tìm thấy điều khoản quy định nào trong tài liệu liên quan đến câu hỏi này."
    
    primary = sources[0]
    lines = [l.strip() for l in primary["text"].split("\n") if l.strip()]
    header = lines[0] if lines else f"Điều {primary['dieu']}"
    body = "\n".join(f"> {l}" for l in lines[1:6])
    
    related = ", ".join(f"Điều {s['dieu']} (độ khớp: {int(s['score']*100)}%)" for s in sources[1:4]) if len(sources) > 1 else ""
    
    ans = (
        f"### 📋 Trích xuất quy định học vụ liên quan nhất:\n\n"
        f"**{header}**\n\n"
        f"{body}\n\n"
    )
    if related:
        ans += f"**Các điều khoản liên quan khác:** {related}.\n\n"
        
    ans += (
        "---\n"
        "💡 **Mẹo kích hoạt AI thông minh:** Hiện tại hệ thống đang ở chế độ *Trích xuất nguyên văn*. "
        "Bạn hãy mở mục **⚙️ Cài đặt AI** (góc trên bên phải), nhập **Google Gemini API Key** (hoàn toàn miễn phí) "
        "để AI tự động tổng hợp, phân tích và trả lời tự nhiên!"
    )
    return ans


# Models cho API
class MessageItem(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    top_k: int = 4
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class ChatStreamRequest(BaseModel):
    question: Optional[str] = None
    messages: List[MessageItem] = Field(default_factory=list)
    top_k: int = 4
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class CaseAnalysisRequest(BaseModel):
    situation: str
    gpa: Optional[float] = None
    credits: Optional[int] = None
    warning_count: Optional[int] = None
    semester_index: Optional[int] = None
    year_level: Optional[int] = None
    consecutive_warning: Optional[bool] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None



class ExplainClauseRequest(BaseModel):
    dieu: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class ConfigSaveRequest(BaseModel):
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None


class AITestRequest(BaseModel):
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None


# Endpoints giao dien va trang thai
@app.get("/")
def home():
    return FileResponse(ROOT / "app" / "index.html")


@app.get("/api/status")
def get_status():
    config = get_ai_config()
    return {
        "chunks": collection.count(),
        "llm": config["is_configured"],
        "provider": config["provider"],
        "model": config["model"],
        "base_url": config["base_url"]
    }


@app.get("/api/clauses")
def list_clauses():
    """Tra ve danh sach toan bo cac Dieu trong quy che."""
    if not CHUNKS_FILE.exists():
        return {"clauses": []}
    try:
        chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
        clauses_dict = {}
        for c in chunks:
            d = str(c.get("dieu", ""))
            if not d:
                continue
            if d not in clauses_dict:
                first_line = c["text"].split("\n")[0]
                clean_title = first_line
                for prefix in [f"Điều {d}.", f"Điều {d}:", f"Điều {d}"]:
                    if clean_title.startswith(prefix):
                        clean_title = clean_title[len(prefix):].strip()
                clauses_dict[d] = {
                    "dieu": d,
                    "chuong": c.get("chuong", ""),
                    "title": clean_title or f"Điều {d}",
                    "raw_text": c["text"],
                    "chunks": [c["text"]]
                }
            else:
                clauses_dict[d]["chunks"].append(c["text"])
                clauses_dict[d]["raw_text"] += "\n\n" + c["text"]
                
        def sort_key(item):
            d = item["dieu"]
            return int(d) if d.isdigit() else 999
            
        result = sorted(list(clauses_dict.values()), key=sort_key)
        return {"clauses": result}
    except Exception as e:
        return {"clauses": [], "error": str(e)}


@app.post("/api/ai/test")
def test_ai_connection(req: AITestRequest):
    """Kiem tra ket noi den AI model ma khong can luu cau hinh."""
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp API Key.")
    
    base_url = (req.base_url or "").strip()
    model = (req.model or DEFAULT_GEMINI_MODEL).strip()
    if not base_url:
        if "gemini" in model.lower() or key.startswith("AIza") or key.startswith("AQ."):
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            base_url = "https://api.openai.com/v1"
            
    t0 = time.time()
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=key, timeout=20.0, max_retries=1)
        res, used_model = create_chat_completion_resilient(
            client=client,
            primary_model=model,
            messages=[
                {"role": "user", "content": "Hãy phản hồi ngắn gọn: Kết nối AI thành công!"}
            ],
            max_tokens=100,
            stream=False
        )
        latency = round((time.time() - t0) * 1000)
        text = (res.choices[0].message.content or "Kết nối AI thành công!").strip()
        return {
            "ok": True,
            "latency_ms": latency,
            "model": used_model,
            "reply": text,
            "message": f"Kết nối AI thành công ({latency}ms)!"
        }
    except Exception as e:
        latency = round((time.time() - t0) * 1000)
        return {
            "ok": False,
            "latency_ms": latency,
            "error": str(e)
        }


@app.post("/api/config")
def save_ai_config(req: ConfigSaveRequest):
    """Luu cau hinh API Key vao file .env va ap dung ngay."""
    api_key = req.api_key.strip()
    base_url = (req.base_url or "").strip()
    model = (req.model or DEFAULT_GEMINI_MODEL).strip()
    
    if not base_url:
        if "gemini" in model.lower() or api_key.startswith("AIza") or api_key.startswith("AQ."):
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        elif api_key.startswith("sk-"):
            base_url = "https://api.openai.com/v1"
            
    try:
        if not ENV_PATH.exists():
            ENV_PATH.write_text("# Auto-generated\n", encoding="utf-8")
        
        set_key(str(ENV_PATH), "LLM_API_KEY", api_key)
        set_key(str(ENV_PATH), "LLM_BASE_URL", base_url)
        set_key(str(ENV_PATH), "LLM_MODEL", model)
        
        # Cap nhat bien moi truong trong bo nho
        os.environ["LLM_API_KEY"] = api_key
        os.environ["LLM_BASE_URL"] = base_url
        os.environ["LLM_MODEL"] = model
        
        return {
            "ok": True,
            "message": "Đã lưu cấu hình AI thành công vào hệ thống!",
            "model": model,
            "base_url": base_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể lưu vào .env: {str(e)}")


@app.post("/api/ask")
def ask(req: AskRequest):
    """API hoi dap co ban (khong streaming)."""
    question = req.question.strip()
    if not question:
        return {"answer": "", "sources": [], "mode": "empty"}
    
    sources = retrieve_chunks(question, req.top_k)
    client, config = get_openai_client(req.api_key, req.base_url, req.model)
    
    if not client:
        fallback = generate_smart_fallback_answer(question, sources)
        return {"answer": fallback, "sources": sources, "mode": "retrieval-fallback"}
    
    context = "\n\n".join(f"[Nguồn {i + 1} - Điều {s['dieu']}]\n{s['text']}" for i, s in enumerate(sources))
    user_prompt = f"NGỮ CẢNH CÁC ĐIỀU KHOẢN QUY ĐỊNH:\n{context}\n\nCÂU HỎI CỦA SINH VIÊN: {question}"
    
    try:
        resp, used_model = create_chat_completion_resilient(
            client=client,
            primary_model=config["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1500,
            stream=False
        )
        return {
            "answer": resp.choices[0].message.content,
            "sources": sources,
            "mode": "rag",
            "model": used_model
        }
    except Exception as e:
        fallback = generate_smart_fallback_answer(question, sources)
        return {
            "answer": fallback,
            "sources": sources,
            "mode": "llm-error",
            "error": str(e)
        }


@app.post("/api/chat/stream")
def chat_stream(req: ChatStreamRequest):
    """API Hoi dap AI streaming (SSE) ho tro hoi thoai da luot & trich dan."""
    question = (req.question or "").strip()
    if not question and req.messages:
        for m in reversed(req.messages):
            if m.role == "user" and m.content.strip():
                question = m.content.strip()
                break
                
    if not question:
        raise HTTPException(status_code=400, detail="Thiếu nội dung câu hỏi.")
        
    sources = retrieve_chunks(question, req.top_k)
    client, config = get_openai_client(req.api_key, req.base_url, req.model)
    
    def event_stream():
        # 1. Gui danh sach nguon trich dan truoc
        yield f"data: {json.dumps({'event': 'sources', 'sources': sources})}\n\n"
        
        # Neu chua co AI client, sinh fallback thong minh
        if not client:
            fallback = generate_smart_fallback_answer(question, sources)
            chunk_size = 6
            for i in range(0, len(fallback), chunk_size):
                sub = fallback[i:i + chunk_size]
                yield f"data: {json.dumps({'event': 'token', 'token': sub})}\n\n"
                time.sleep(0.01)
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            return
            
        context = "\n\n".join(f"[Nguồn {i + 1} - Điều {s['dieu']}]\n{s['text']}" for i, s in enumerate(sources))
        prompt_instruction = (
            f"DƯỚI ĐÂY LÀ CÁC ĐIỀU KHOẢN QUY CHẾ ĐƯỢC TRÍCH XUẤT CHO CÂU HỎI HIỆN TẠI:\n{context}\n\n"
            f"Hãy trả lời câu hỏi của sinh viên dựa trên thông tin trên."
        )
        
        messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in req.messages[:-1]:
            if m.content.strip():
                messages_to_send.append({"role": m.role, "content": m.content})
                
        messages_to_send.append({
            "role": "user",
            "content": f"{prompt_instruction}\n\nCÂU HỎI: {question}"
        })
        
        try:
            stream, used_model = create_chat_completion_resilient(
                client=client,
                primary_model=config["model"],
                messages=messages_to_send,
                temperature=0.2,
                max_tokens=2000,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'event': 'token', 'token': token})}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
        except Exception as e:
            err_msg = f"\n\n⚠️ *Lỗi kết nối AI*: {str(e)}\nĐang hiển thị nội dung trích xuất dự phòng:\n\n"
            yield f"data: {json.dumps({'event': 'token', 'token': err_msg})}\n\n"
            fallback = generate_smart_fallback_answer(question, sources)
            yield f"data: {json.dumps({'event': 'token', 'token': fallback})}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/analyze-case")
def analyze_case(req: CaseAnalysisRequest):
    """API Tu van va phan tich tinh huong hoc vu ca nhan bang AI ket hop Rule Engine."""
    sit = req.situation.strip()
    if not sit:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp mô tả tình huống.")
        
    query = f"quy định về: {sit}. Cảnh báo học vụ, thôi học, giới hạn tín chỉ đăng ký, học lại, bảo lưu điểm GPA"
    if req.gpa is not None:
        query += f" điểm trung bình {req.gpa}"
    if req.warning_count is not None and req.warning_count > 0:
        query += f" bị cảnh báo học vụ {req.warning_count} lần"
        
    sources = retrieve_chunks(query, top_k=6)
    client, config = get_openai_client(req.api_key, req.base_url, req.model)
    
    # Chay Rule Engine xac minh nghiep vu chuan 100% neu co thong so
    rule_eval = None
    if req.gpa is not None:
        sem_idx = req.semester_index if req.semester_index is not None else 2
        yr_lvl = req.year_level if req.year_level is not None else max(1, (sem_idx + 1) // 2)
        consec = bool(req.consecutive_warning or (req.warning_count is not None and req.warning_count >= 1))
        rule_eval = check_academic_status_rules(StatusCheckInput(
            semester_index=sem_idx,
            year_level=yr_lvl,
            gpa_semester=req.gpa,
            cpa_cumulative=req.gpa,
            previous_warnings=req.warning_count or 0,
            consecutive_warning=consec
        ))
        
    details_meta = []
    if req.gpa is not None:
        details_meta.append(f"Điểm GPA: {req.gpa}")
    if req.credits is not None:
        details_meta.append(f"Số tín chỉ: {req.credits}")
    if req.warning_count is not None:
        details_meta.append(f"Số lần đã bị cảnh báo học vụ: {req.warning_count}")
    if req.semester_index is not None:
        details_meta.append(f"Học kỳ thứ: {req.semester_index}")
    if req.year_level is not None:
        details_meta.append(f"Sinh viên năm thứ: {req.year_level}")
    meta_str = " | ".join(details_meta) if details_meta else "Chưa cung cấp chỉ số cụ thể"
    
    rule_summary_str = ""
    if rule_eval:
        rule_summary_str = (
            f"\n\nKẾT QUẢ XÁC MINH BỘ QUY CHẾ ĐÀO TẠO (RULE ENGINE):\n"
            f"- Đánh giá mức độ: {rule_eval['risk_label']}\n"
            f"- Xếp loại học lực: {rule_eval['academic_standing']}\n"
            f"- Hạn mức tín chỉ đăng ký kỳ tới: {rule_eval['allowed_credits_next_semester']['min']} - {rule_eval['allowed_credits_next_semester']['max']} tín chỉ ({rule_eval['allowed_credits_next_semester']['note']})\n"
            f"- Các căn cứ điều khoản: {', '.join(rule_eval['regulations_cited'])}\n"
        )
        if rule_eval['is_expelled']:
            rule_summary_str += f"- LƯU Ý SỐNG CÒN: {rule_eval['expel_reason']}\n"
            
    if not client:
        return {
            "analysis": (
                "### 🚦 Phân tích tình huống học vụ (Chế độ trích xuất & Rule Engine)\n\n"
                f"**Thông tin bạn cung cấp:** {sit}\n"
                f"**Chỉ số:** {meta_str}\n"
                f"{rule_summary_str}\n"
                "**Các điều khoản quy chế cần đặc biệt lưu ý:**\n"
                + "\n".join(f"- **Điều {s['dieu']}**: {s['text'].splitlines()[0]}" for s in sources[:4])
                + "\n\n> 💡 *Vui lòng cấu hình API Key (Google Gemini miễn phí) tại mục Cài đặt AI để nhận phân tích chuyên sâu tự động từ AI!*"
            ),
            "sources": sources,
            "rule_engine": rule_eval,
            "mode": "fallback"
        }
        
    context = "\n\n".join(f"[Nguồn Điều {s['dieu']}]\n{s['text']}" for s in sources)
    user_prompt = (
        f"THÔNG TIN TÌNH HUỐNG SINH VIÊN:\n"
        f"- Mô tả: {sit}\n"
        f"- Chỉ số học tập: {meta_str}\n"
        f"{rule_summary_str}\n"
        f"NGỮ CẢNH CÁC ĐIỀU KHOẢN QUY CHẾ:\n{context}\n\n"
        f"Hãy tiến hành phân tích học vụ theo đúng 3 phần đã quy định trong hệ thống. "
        f"ĐẶC BIỆT: Bắt buộc tôn trọng và trích dẫn các kết quả xác minh từ Bộ Quy chế (Rule Engine) ở trên."
    )
    
    try:
        resp, used_model = create_chat_completion_resilient(
            client=client,
            primary_model=config["model"],
            messages=[
                {"role": "system", "content": CASE_ANALYZER_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            stream=False
        )
        return {
            "analysis": resp.choices[0].message.content,
            "sources": sources,
            "rule_engine": rule_eval,
            "mode": "rag",
            "model": used_model
        }
    except Exception as e:
        return {
            "analysis": f"⚠️ Lỗi khi phân tích bằng AI: {str(e)}",
            "sources": sources,
            "rule_engine": rule_eval,
            "mode": "error"
        }


@app.post("/api/explain-dieu")
def explain_dieu(req: ExplainClauseRequest):
    """API AI dien giai va tom tat mot Dieu khoan cu the theo ngon ngu sinh vien."""
    dieu_target = req.dieu.strip()
    if not dieu_target:
        raise HTTPException(status_code=400, detail="Thiếu số Điều cần giải thích.")
        
    if not CHUNKS_FILE.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu quy chế.")
        
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    matched_chunks = [c for c in chunks if str(c.get("dieu", "")) == dieu_target]
    
    if not matched_chunks:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy Điều {dieu_target} trong quy chế.")
        
    full_text = "\n\n".join(c["text"] for c in matched_chunks)
    client, config = get_openai_client(req.api_key, req.base_url, req.model)
    
    if not client:
        first_line = matched_chunks[0]["text"].split("\n")[0]
        return {
            "explanation": (
                f"### 🎯 Nội dung chính Điều {dieu_target} ({first_line}):\n\n"
                f"> {full_text[:600]}...\n\n"
                "💡 *Hãy kết nối Gemini API Key miễn phí tại mục Cài đặt AI để AI diễn giải chi tiết bằng ngôn ngữ sinh viên!*"
            ),
            "raw_text": full_text,
            "dieu": dieu_target,
            "mode": "fallback"
        }
        
    user_prompt = f"HÃY GIẢI THÍCH NỘI DUNG ĐIỀU KHOẢN SAU ĐÂY:\n\n{full_text}"
    try:
        resp, used_model = create_chat_completion_resilient(
            client=client,
            primary_model=config["model"],
            messages=[
                {"role": "system", "content": EXPLAIN_CLAUSE_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1800,
            stream=False
        )
        return {
            "explanation": resp.choices[0].message.content,
            "raw_text": full_text,
            "dieu": dieu_target,
            "mode": "rag",
            "model": used_model
        }
    except Exception as e:
        return {
            "explanation": f"⚠️ Không thể gọi AI để giải thích: {str(e)}",
            "raw_text": full_text,
            "dieu": dieu_target,
            "mode": "error"
        }


# =====================================================================
# CAC ENDPOINTS MO PHONG & CONG CU TINH TOAN HOC VU (RULE ENGINE APIS)
# =====================================================================

@app.post("/api/simulator/status-check")
def api_status_check(req: StatusCheckInput):
    """
    Kiem tra tinh trang hoc vu, canh bao hoc vu va nguy co buoc thoi hoc
    tuan thu 100% Dieu 11 va Dieu 4 Quy che dao tao.
    """
    return check_academic_status_rules(req)


@app.post("/api/simulator/gpa-retake")
def api_gpa_retake(req: GPASimulatorInput):
    """
    Mo phong ket qua nang diem CPA khi hoc lai mon F hoac hoc cai thien mon D, D+
    theo cong thuc thay the diem cao nhat (Dieu 6 Khoan 2).
    """
    return simulate_gpa_improvement(req)


@app.post("/api/simulator/grade-calc")
def api_grade_calc(req: CourseGradeInput):
    """
    Tinh diem tong ket hoc phan (10% CC + 30% GK + 60% CK),
    quy doi sang thang chu va thang 4 (Dieu 7 & 8).
    """
    return calculate_course_grade(req)


@app.post("/api/simulator/graduation-check")
def api_graduation_check(req: GraduationCheckInput):
    """
    Kiem tra 4 dieu kien tot nghiep, xep hang tot nghiep va kiem tra
    quy dinh giam mot hang tot nghiep do hoc lai > 5% hoac bi ky luat (Dieu 12 & 13).
    """
    return check_graduation_eligibility(req)


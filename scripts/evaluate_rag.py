"""
Script Danh gia Thuc nghiem He thong RAG Quy dinh Hoc vu (RAG Benchmark & Evaluation Suite).
Phuc vu bao cao do an tot nghiep:
1. Do luong do chinh xac truy xuat ngu nghia: Hit@1, Hit@3, Hit@5, MRR (Mean Reciprocal Rank).
2. Do luong hieu nang thoi gian (Latency): Thoi gian ma hoa vector cau hoi, thoi gian truy van ChromaDB.
3. Phan tich chat luong theo tung nhom chu de cau hoi quy che.
4. Xuat bao cao thuc nghiem ra file JSON va dinh dang bang tong hop khoa hoc.
"""
import json
import os
import pathlib
import sys
import time
from typing import Any, Dict, List

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "data" / "chroma"
CHUNKS_FILE = ROOT / "data" / "chunks.json"
MODEL_NAME = "intfloat/multilingual-e5-small"
COLLECTION_NAME = "quy_dinh_hoc_vu"
RESULTS_FILE = ROOT / "data" / "evaluation_results.json"

if not DB_DIR.exists():
    sys.exit("Chua co vector DB. Hay chay truoc: python scripts\\embed_index.py")

# =====================================================================
# TAP DU LIEU KIEM THU CHUAN (GOLDEN EVALUATION BENCHMARK - 25 TEST CASES)
# =====================================================================
BENCHMARK_DATASET: List[Dict[str, Any]] = [
    # Nhom 1: Khai niem, Tin chi & Thoi gian dao tao (Dieu 2, 3)
    {
        "id": "TC01",
        "category": "Quy dinh chung & Tin chi",
        "question": "Một tín chỉ học tập được quy định bằng bao nhiêu tiết lý thuyết hoặc thực hành?",
        "expected_dieu": ["2"],
        "key_facts": "15 tiết lý thuyết hoặc 30 tiết thực hành, thí nghiệm"
    },
    {
        "id": "TC02",
        "category": "Quy dinh chung & Tin chi",
        "question": "Mỗi học phần trong chương trình có khối lượng bao nhiêu tín chỉ?",
        "expected_dieu": ["2"],
        "key_facts": "Từ 2 đến 4 tín chỉ"
    },
    {
        "id": "TC03",
        "category": "Quy dinh chung & Tin chi",
        "question": "Thời gian tối đa để sinh viên hoàn thành khóa học là bao nhiêu năm?",
        "expected_dieu": ["3"],
        "key_facts": "Không vượt quá 2 lần thời gian thiết kế (tức tối đa 8 năm)"
    },

    # Nhom 2: Dang ky hoc phan & Rut bot hoc phan (Dieu 4, 5)
    {
        "id": "TC04",
        "category": "Dang ky & Rut hoc phan",
        "question": "Một học kỳ chính sinh viên được đăng ký tối thiểu và tối đa bao nhiêu tín chỉ?",
        "expected_dieu": ["4"],
        "key_facts": "Tối thiểu 14 tín chỉ, tối đa 25 tín chỉ"
    },
    {
        "id": "TC05",
        "category": "Dang ky & Rut hoc phan",
        "question": "Sinh viên đang bị cảnh báo học vụ thì được đăng ký tối đa bao nhiêu tín chỉ kỳ tới?",
        "expected_dieu": ["4"],
        "key_facts": "Tối đa 14 tín chỉ"
    },
    {
        "id": "TC06",
        "category": "Dang ky & Rut hoc phan",
        "question": "Trong học kỳ hè sinh viên được phép đăng ký tối đa bao nhiêu tín chỉ?",
        "expected_dieu": ["4"],
        "key_facts": "Tối đa 10 tín chỉ"
    },
    {
        "id": "TC07",
        "category": "Dang ky & Rut hoc phan",
        "question": "Sinh viên được rút bớt học phần trong thời gian bao lâu kể từ đầu học kỳ?",
        "expected_dieu": ["5"],
        "key_facts": "Trong vòng 2 tuần kể từ ngày bắt đầu học kỳ"
    },
    {
        "id": "TC08",
        "category": "Dang ky & Rut hoc phan",
        "question": "Rút học phần trong thời hạn quy định có bị tính điểm và mất học phí không?",
        "expected_dieu": ["5"],
        "key_facts": "Không bị tính điểm và không phải nộp thêm học phí"
    },

    # Nhom 3: Hoc lai & Hoc cai thien diem (Dieu 6)
    {
        "id": "TC09",
        "category": "Hoc lai & Cai thien",
        "question": "Môn học bắt buộc bị điểm F thì sinh viên phải làm gì?",
        "expected_dieu": ["6"],
        "key_facts": "Phải đăng ký học lại học phần đó ở kỳ có mở lớp"
    },
    {
        "id": "TC10",
        "category": "Hoc lai & Cai thien",
        "question": "Điểm nào thì sinh viên được quyền đăng ký học cải thiện điểm?",
        "expected_dieu": ["6"],
        "key_facts": "Môn đạt điểm D hoặc D+ được quyền học lại cải thiện"
    },
    {
        "id": "TC11",
        "category": "Hoc lai & Cai thien",
        "question": "Khi học lại cải thiện điểm thì điểm mới hay điểm cũ được dùng để tính CPA tích lũy?",
        "expected_dieu": ["6"],
        "key_facts": "Điểm cao nhất trong các lần học được dùng để tính điểm tích lũy"
    },

    # Nhom 4: Thang diem & Cach tinh diem hoc phan (Dieu 7, 8, 9, 10)
    {
        "id": "TC12",
        "category": "Danh gia & Thang diem",
        "question": "Điểm học phần được tính theo tỷ lệ các điểm thành phần như thế nào?",
        "expected_dieu": ["8"],
        "key_facts": "10% chuyên cần + 30% giữa kỳ + 60% thi kết thúc"
    },
    {
        "id": "TC13",
        "category": "Danh gia & Thang diem",
        "question": "Vắng mặt bao nhiêu phần trăm số tiết thì sinh viên bị cấm thi?",
        "expected_dieu": ["8"],
        "key_facts": "Vắng quá 20% số tiết không được dự thi và nhận điểm 0"
    },
    {
        "id": "TC14",
        "category": "Danh gia & Thang diem",
        "question": "Mức điểm thang 10 từ bao nhiêu trở lên thì được quy đổi thành điểm A thang 4?",
        "expected_dieu": ["7"],
        "key_facts": "Từ 8.5 đến 10 là điểm A (4.0)"
    },
    {
        "id": "TC15",
        "category": "Danh gia & Thang diem",
        "question": "Thang điểm 4 quy định xếp loại học lực Xuất sắc và Giỏi từ bao nhiêu điểm?",
        "expected_dieu": ["10"],
        "key_facts": "Từ 3.6 đến 4.0 là Xuất sắc, từ 3.2 đến dưới 3.6 là Giỏi"
    },

    # Nhom 5: Canh bao hoc vu & Buoc thoi hoc (Dieu 11)
    {
        "id": "TC16",
        "category": "Canh bao & Xu ly hoc vu",
        "question": "Sinh viên năm nhất bị cảnh báo học vụ khi điểm trung bình tích lũy CPA dưới bao nhiêu?",
        "expected_dieu": ["11"],
        "key_facts": "CPA dưới 1.6 đối với năm thứ nhất"
    },
    {
        "id": "TC17",
        "category": "Canh bao & Xu ly hoc vu",
        "question": "Bị cảnh báo học vụ mấy lần liên tiếp thì sinh viên bị buộc thôi học?",
        "expected_dieu": ["11"],
        "key_facts": "Bị cảnh báo học vụ liên tiếp 2 học kỳ thì buộc thôi học"
    },
    {
        "id": "TC18",
        "category": "Canh bao & Xu ly hoc vu",
        "question": "Điểm trung bình học kỳ ở kỳ đầu tiên dưới bao nhiêu thì bị cảnh báo?",
        "expected_dieu": ["11"],
        "key_facts": "GPA học kỳ dưới 1.0 đối với học kỳ đầu tiên"
    },
    {
        "id": "TC19",
        "category": "Canh bao & Xu ly hoc vu",
        "question": "Sinh viên bị buộc thôi học có được bảo lưu kết quả học tập đã hoàn thành không?",
        "expected_dieu": ["11"],
        "key_facts": "Được quyền xin bảo lưu kết quả và cấp chứng nhận khối lượng tích lũy"
    },

    # Nhom 6: Xet & Hang tot nghiep (Dieu 12, 13)
    {
        "id": "TC20",
        "category": "Xet & Hang tot nghiep",
        "question": "Sinh viên cần đáp ứng những điều kiện nào để được xét công nhận tốt nghiệp?",
        "expected_dieu": ["12"],
        "key_facts": "Tích lũy đủ tín chỉ, CPA >= 2.0, chuẩn ngoại ngữ, GDQP-AN, GDTC, không bị kỷ luật"
    },
    {
        "id": "TC21",
        "category": "Xet & Hang tot nghiep",
        "question": "Điểm CPA toàn khóa tối thiểu là bao nhiêu để được xét tốt nghiệp đại học?",
        "expected_dieu": ["12"],
        "key_facts": "CPA toàn khóa đạt từ 2.0 trở lên"
    },
    {
        "id": "TC22",
        "category": "Xet & Hang tot nghiep",
        "question": "Trường hợp nào sinh viên tốt nghiệp loại Giỏi hoặc Xuất sắc bị giảm một hạng tốt nghiệp?",
        "expected_dieu": ["13"],
        "key_facts": "Bị kỷ luật cảnh cáo trở lên hoặc tín chỉ học lại vượt quá 5% tổng số tín chỉ"
    },

    # Nhom 7: Bao luu & Ky luat thi (Dieu 14, 15)
    {
        "id": "TC23",
        "category": "Bao luu & Ky luat",
        "question": "Thời gian nghỉ học tạm thời và bảo lưu kết quả tối đa là bao nhiêu học kỳ?",
        "expected_dieu": ["14"],
        "key_facts": "Tối đa là 2 học kỳ liên tiếp"
    },
    {
        "id": "TC24",
        "category": "Bao luu & Ky luat",
        "question": "Sinh viên nhìn bài hoặc trao đổi bài trong phòng thi bị xử lý thế nào?",
        "expected_dieu": ["15"],
        "key_facts": "Bị khiển trách và trừ 25% số điểm bài thi"
    },
    {
        "id": "TC25",
        "category": "Bao luu & Ky luat",
        "question": "Hành vi nhờ người khác thi hộ hoặc thi hộ người khác bị kỷ luật ở mức nào?",
        "expected_dieu": ["15"],
        "key_facts": "Đình chỉ thi điểm 0 và đình chỉ học tập 1 năm"
    }
]


def run_rag_evaluation(top_k: int = 5) -> Dict[str, Any]:
    print("=" * 75)
    print(" CHƯƠNG TRÌNH KIỂM THỬ & ĐÁNH GIÁ THỰC NGHIỆM HỆ THỐNG RAG HỌC VỤ ")
    print("=" * 75)
    print(f"[*] Đang tải mô hình nhúng: {MODEL_NAME}...")
    try:
        embedder = SentenceTransformer(MODEL_NAME, local_files_only=True)
    except Exception:
        embedder = SentenceTransformer(MODEL_NAME)

    print(f"[*] Đang kết nối ChromaDB tại: {DB_DIR}...")
    chroma_client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = chroma_client.get_collection(COLLECTION_NAME)
    print(f"[*] Tổng số chunk tri thức quy chế trong cơ sở dữ liệu: {collection.count()} chunks.")
    print(f"[*] Tổng số câu hỏi kiểm thử trong tập dữ liệu: {len(BENCHMARK_DATASET)} câu hỏi.")
    print("-" * 75)

    hit_1_count = 0
    hit_3_count = 0
    hit_5_count = 0
    reciprocal_ranks = []
    
    embedding_latencies = []
    retrieval_latencies = []
    total_retrieval_latencies = []
    
    detailed_results = []
    category_stats = {}

    for item in BENCHMARK_DATASET:
        qid = item["id"]
        cat = item["category"]
        q = item["question"]
        expected = item["expected_dieu"]

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "hit_1": 0, "hit_3": 0, "hit_5": 0, "rr_sum": 0.0}
        category_stats[cat]["total"] += 1

        # 1. Đo thời gian encode embedding
        t0 = time.perf_counter()
        query_vec = embedder.encode(["query: " + q], normalize_embeddings=True)[0].tolist()
        t1 = time.perf_counter()
        embed_ms = (t1 - t0) * 1000.0

        # 2. Đo thời gian truy vấn ChromaDB
        res = collection.query(query_embeddings=[query_vec], n_results=top_k)
        t2 = time.perf_counter()
        chroma_ms = (t2 - t1) * 1000.0
        total_ms = (t2 - t0) * 1000.0

        embedding_latencies.append(embed_ms)
        retrieval_latencies.append(chroma_ms)
        total_retrieval_latencies.append(total_ms)

        retrieved_dieus = []
        scores = []
        if res and res.get("metadatas") and len(res["metadatas"]) > 0:
            for m, d in zip(res["metadatas"][0], res["distances"][0]):
                retrieved_dieus.append(str(m.get("dieu", "")))
                scores.append(round(1.0 - float(d), 3))

        # Đánh giá thứ hạng (Rank) của đáp án đúng đầu tiên
        rank = 0
        for i, d in enumerate(retrieved_dieus):
            if d in expected:
                rank = i + 1
                break

        # Tính Hit@K và Reciprocal Rank
        is_hit_1 = (rank == 1)
        is_hit_3 = (0 < rank <= 3)
        is_hit_5 = (0 < rank <= 5)
        rr = (1.0 / rank) if rank > 0 else 0.0

        if is_hit_1:
            hit_1_count += 1
            category_stats[cat]["hit_1"] += 1
        if is_hit_3:
            hit_3_count += 1
            category_stats[cat]["hit_3"] += 1
        if is_hit_5:
            hit_5_count += 1
            category_stats[cat]["hit_5"] += 1
        category_stats[cat]["rr_sum"] += rr
        reciprocal_ranks.append(rr)

        top_match_str = f"Điều {retrieved_dieus[0]} (độ khớp: {scores[0]})" if retrieved_dieus else "Không tìm thấy"
        status_icon = "✅" if is_hit_1 else ("⚠️" if is_hit_3 else "❌")

        detailed_results.append({
            "id": qid,
            "category": cat,
            "question": q,
            "expected_dieu": expected,
            "retrieved_dieus": retrieved_dieus,
            "scores": scores,
            "first_correct_rank": rank,
            "reciprocal_rank": round(rr, 3),
            "hit_1": is_hit_1,
            "hit_3": is_hit_3,
            "hit_5": is_hit_5,
            "embedding_ms": round(embed_ms, 2),
            "chroma_ms": round(chroma_ms, 2),
            "total_ms": round(total_ms, 2)
        })

        print(f"[{qid}] {status_icon} Rank: {rank if rank > 0 else 'N/A'} | Top-1: {top_match_str:<25} | {embed_ms:.1f}ms + {chroma_ms:.1f}ms | Q: {q[:45]}...")

    # =====================================================================
    # TỔNG HỢP VÀ TÍNH TOÁN CÁC CHỈ SỐ THỰC NGHIỆM ĐỒ ÁN
    # =====================================================================
    n = len(BENCHMARK_DATASET)
    hit_1_rate = round((hit_1_count / n) * 100, 2)
    hit_3_rate = round((hit_3_count / n) * 100, 2)
    hit_5_rate = round((hit_5_count / n) * 100, 2)
    mrr = round(sum(reciprocal_ranks) / n, 4)

    avg_embed_ms = round(sum(embedding_latencies) / n, 2)
    avg_chroma_ms = round(sum(retrieval_latencies) / n, 2)
    avg_total_ms = round(sum(total_retrieval_latencies) / n, 2)

    print("\n" + "=" * 75)
    print(" BẢNG TỔNG HỢP KẾT QUẢ THỰC NGHIỆM ĐỘ CHÍNH XÁC VÀ HIỆU NĂNG RAG ")
    print("=" * 75)
    print(f"Tổng số mẫu kiểm thử:           {n} câu hỏi")
    print(f"Độ chính xác Top-1 (Hit@1):      {hit_1_count}/{n} ({hit_1_rate}%)")
    print(f"Độ chính xác Top-3 (Hit@3):      {hit_3_count}/{n} ({hit_3_rate}%)")
    print(f"Độ chính xác Top-5 (Hit@5):      {hit_5_count}/{n} ({hit_5_rate}%)")
    print(f"Điểm MRR (Mean Reciprocal Rank): {mrr} (trên thang điểm 1.0)")
    print("-" * 75)
    print(f"Thời gian mã hóa véc-tơ (E5):    {avg_embed_ms} ms / câu")
    print(f"Thời gian truy vấn ChromaDB:     {avg_chroma_ms} ms / câu")
    print(f"Tổng thời gian truy xuất (End):  {avg_total_ms} ms / câu")
    print("=" * 75)

    print("\n" + "=" * 75)
    print(" BẢNG CHI TIẾT THEO TỪNG NHÓM NGHIỆP VỤ HỌC VỤ ")
    print("=" * 75)
    print(f"{'Nhóm nghiệp vụ':<28} | {'Số câu':<6} | {'Hit@1':<8} | {'Hit@3':<8} | {'MRR':<6}")
    print("-" * 75)
    for cat, s in category_stats.items():
        c_n = s["total"]
        c_h1 = f"{round((s['hit_1']/c_n)*100, 1)}%"
        c_h3 = f"{round((s['hit_3']/c_n)*100, 1)}%"
        c_mrr = f"{round(s['rr_sum']/c_n, 3)}"
        print(f"{cat:<28} | {c_n:<6} | {c_h1:<8} | {c_h3:<8} | {c_mrr:<6}")
    print("=" * 75)

    summary_report = {
        "metadata": {
            "evaluation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_name": MODEL_NAME,
            "vector_dimensions": 384,
            "database": "ChromaDB (Persistent)",
            "collection_chunks_count": collection.count(),
            "total_benchmark_questions": n
        },
        "overall_metrics": {
            "hit_1_count": hit_1_count,
            "hit_1_rate_pct": hit_1_rate,
            "hit_3_count": hit_3_count,
            "hit_3_rate_pct": hit_3_rate,
            "hit_5_count": hit_5_count,
            "hit_5_rate_pct": hit_5_rate,
            "mrr": mrr,
            "avg_embedding_latency_ms": avg_embed_ms,
            "avg_chroma_latency_ms": avg_chroma_ms,
            "avg_total_retrieval_latency_ms": avg_total_ms
        },
        "category_breakdown": category_stats,
        "test_cases": detailed_results
    }

    # Luu ket qua JSON
    RESULTS_FILE.write_text(json.dumps(summary_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[+] Đã lưu toàn bộ kết quả thực nghiệm ra: {RESULTS_FILE}")

    return summary_report


if __name__ == "__main__":
    run_rag_evaluation()

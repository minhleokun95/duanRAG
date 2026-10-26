"""Thu truy xuat: nhap cau hoi, xem top-3 chunk gan nhat trong vector DB."""
import pathlib
import sys

import chromadb
from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "data" / "chroma"
MODEL_NAME = "intfloat/multilingual-e5-small"
COLLECTION = "quy_dinh_hoc_vu"
TOP_K = 3


def main():
    if not DB_DIR.exists():
        print("Chua co vector DB. Hay chay scripts\\embed_index.py truoc.")
        return
    model = SentenceTransformer(MODEL_NAME)
    col = chromadb.PersistentClient(path=str(DB_DIR)).get_collection(COLLECTION)
    print(f"San sang ({col.count()} chunk). Nhap cau hoi, de trong roi Enter de thoat.\n")

    while True:
        q = input("Cau hoi> ").strip()
        if not q:
            break
        vec = model.encode(["query: " + q], normalize_embeddings=True)[0].tolist()
        res = col.query(query_embeddings=[vec], n_results=TOP_K)
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            print(f"\n--- Dieu {meta['dieu']} | do gan: {1 - dist:.3f}")
            print(doc[:400] + ("..." if len(doc) > 400 else ""))
        print()


if __name__ == "__main__":
    main()

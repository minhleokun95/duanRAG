"""Buoc 3+4: Tao embeddings cho cac chunk va luu vao vector DB (Chroma) -> data/chroma/."""
import json
import pathlib
import sys

import chromadb
from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHUNKS = ROOT / "data" / "chunks.json"
DB_DIR = ROOT / "data" / "chroma"
MODEL_NAME = "intfloat/multilingual-e5-small"   # nho, ho tro tieng Viet; sau nay co the doi sang BAAI/bge-m3
COLLECTION = "quy_dinh_hoc_vu"


def main():
    if not CHUNKS.exists():
        print("Chua co data/chunks.json. Hay chay scripts\\chunk.py truoc.")
        return
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    print(f"Doc {len(chunks)} chunk. Dang tai/ nap model {MODEL_NAME} (lan dau se mat vai phut)...")

    model = SentenceTransformer(MODEL_NAME)
    # E5 yeu cau tien to "passage: " cho van ban tai lieu
    texts = ["passage: " + c["text"] for c in chunks]
    vectors = model.encode(texts, normalize_embeddings=True,
                           batch_size=16, show_progress_bar=True)
    print("Kich thuoc vector:", vectors.shape)

    client = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        client.delete_collection(COLLECTION)   # lam moi moi lan chay
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    col.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=vectors.tolist(),
        metadatas=[{"doc": c["doc"], "chuong": c["chuong"], "dieu": c["dieu"]} for c in chunks],
    )
    print(f"Da luu {col.count()} chunk vao {DB_DIR}")


if __name__ == "__main__":
    main()

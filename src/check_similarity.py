import sys
sys.path.insert(0, 'src')
from sentence_transformers import SentenceTransformer
import chromadb
from config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL

embedder = SentenceTransformer(EMBED_MODEL)
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
col = client.get_collection(COLLECTION_NAME)

queries = [
    "Toi duoc nghi bao nhieu ngay phep moi nam",
    "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?",
    "nghi phep",
    "leave days policy",
]

for query in queries:
    qe = embedder.encode(query, normalize_embeddings=True).tolist()
    results = col.query(
        query_embeddings=[qe],
        n_results=3,
        where={"trang_thai": {"$eq": "active"}},
        include=["distances", "metadatas"]
    )
    print(f"\nQuery: '{query}'")
    for i, (dist, meta) in enumerate(zip(results["distances"][0], results["metadatas"][0])):
        sim = round(1 - dist, 4)
        print(f"  [{i+1}] sim={sim} | {meta.get('doc_id')} | {meta.get('don_vi')}")

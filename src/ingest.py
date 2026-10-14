"""
Document ingestion pipeline:
- Parse YAML frontmatter + content from .txt files
- Chunk text with RecursiveCharacterTextSplitter
- Embed with sentence-transformers
- Store in ChromaDB with full metadata
- Deduplicate: archive old versions on re-ingest
"""
import os
import re
import yaml
import uuid
from pathlib import Path
from typing import Optional

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# ── Local import ───────────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    DATA_DIR, CHROMA_DIR, COLLECTION_NAME,
    EMBED_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
)

# ── Init embedding model ───────────────────────────────────────────
print(f"[Ingest] Loading embedding model: {EMBED_MODEL}")
embedder = SentenceTransformer(EMBED_MODEL)

# ── Init ChromaDB ──────────────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

def get_or_create_collection():
    """Get or create ChromaDB collection with cosine similarity."""
    try:
        col = chroma_client.get_collection(COLLECTION_NAME)
        print(f"[Ingest] Using existing collection: {COLLECTION_NAME}")
    except Exception:
        col = chroma_client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"[Ingest] Created new collection: {COLLECTION_NAME}")
    return col


def parse_document(filepath: Path) -> Optional[dict]:
    """Parse YAML frontmatter and content from a .txt file."""
    text = filepath.read_text(encoding="utf-8")

    # Extract YAML frontmatter between --- markers
    pattern = r"^---\n(.*?)\n---\n(.*)$"
    match = re.match(pattern, text, re.DOTALL)
    if not match:
        print(f"[Ingest] WARNING: No frontmatter in {filepath.name}, skipping.")
        return None

    try:
        meta = yaml.safe_load(match.group(1))
        content = match.group(2).strip()
    except yaml.YAMLError as e:
        print(f"[Ingest] ERROR parsing YAML in {filepath.name}: {e}")
        return None

    # Normalize cap_bac to list
    if isinstance(meta.get("cap_bac"), str):
        meta["cap_bac"] = [meta["cap_bac"]]

    return {"metadata": meta, "content": content, "filepath": str(filepath)}


def archive_old_versions(collection, doc_family_id: str, don_vi: str, new_doc_id: str):
    """
    Archive existing active documents with same (doc_family_id, don_vi)
    before inserting the new version. This ensures only 1 active doc per family per unit.
    """
    try:
        results = collection.get(
            where={
                "$and": [
                    {"doc_family_id": {"$eq": doc_family_id}},
                    {"don_vi": {"$eq": don_vi}},
                    {"trang_thai": {"$eq": "active"}},
                ]
            }
        )
        if results and results["ids"]:
            # Filter out the new document itself
            ids_to_archive = [
                id_ for id_, meta in zip(results["ids"], results["metadatas"])
                if meta.get("doc_id") != new_doc_id
            ]
            if ids_to_archive:
                print(f"[Ingest] Archiving {len(ids_to_archive)} old chunks for "
                      f"family='{doc_family_id}' unit='{don_vi}'")
                for chunk_id in ids_to_archive:
                    collection.update(
                        ids=[chunk_id],
                        metadatas=[{"trang_thai": "archived"}]
                    )
    except Exception as e:
        print(f"[Ingest] WARNING during archive: {e}")


def chunk_and_embed(content: str, metadata: dict) -> list[dict]:
    """Split content into chunks, embed each chunk, return list of records."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_text(content)

    records = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{metadata['doc_id']}_chunk_{i}"
        embedding = embedder.encode(chunk, normalize_embeddings=True).tolist()

        # Flatten cap_bac list to string for ChromaDB (doesn't support list values)
        flat_meta = {**metadata}
        flat_meta["cap_bac"] = ",".join(metadata.get("cap_bac", []))
        flat_meta["chunk_index"] = i
        flat_meta["chunk_total"] = len(chunks)

        records.append({
            "id":        chunk_id,
            "embedding": embedding,
            "document":  chunk,
            "metadata":  flat_meta,
        })
    return records


def ingest_file(collection, filepath: Path) -> bool:
    """Parse, chunk, embed and store a single document file."""
    parsed = parse_document(filepath)
    if not parsed:
        return False

    meta    = parsed["metadata"]
    content = parsed["content"]
    doc_id  = meta.get("doc_id", str(uuid.uuid4()))

    print(f"[Ingest] Processing: {filepath.name} -> doc_id={doc_id} "
          f"unit={meta.get('don_vi')} status={meta.get('trang_thai')}")

    # Archive old active versions if this doc is active
    if meta.get("trang_thai") == "active":
        archive_old_versions(
            collection,
            doc_family_id=meta.get("doc_family_id", ""),
            don_vi=meta.get("don_vi", ""),
            new_doc_id=doc_id,
        )

    # Check if already ingested (by doc_id prefix)
    try:
        existing = collection.get(where={"doc_id": {"$eq": doc_id}})
        if existing and existing["ids"]:
            print(f"[Ingest] Already exists, skipping: {doc_id}")
            return False
    except Exception:
        pass

    # Chunk + embed + store
    records = chunk_and_embed(content, meta)
    if not records:
        return False

    collection.add(
        ids        = [r["id"] for r in records],
        embeddings = [r["embedding"] for r in records],
        documents  = [r["document"] for r in records],
        metadatas  = [r["metadata"] for r in records],
    )
    print(f"[Ingest]   → Stored {len(records)} chunks.")
    return True


def ingest_all(data_dir: Path = DATA_DIR, reset: bool = False):
    """Ingest all .txt files from data directory tree."""
    if reset:
        print("[Ingest] Resetting collection...")
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = get_or_create_collection()

    txt_files = sorted(data_dir.rglob("*.txt"))
    print(f"[Ingest] Found {len(txt_files)} documents to process.")

    success = 0
    for fp in txt_files:
        if ingest_file(collection, fp):
            success += 1

    total = collection.count()
    print(f"\n[Ingest] Done. {success}/{len(txt_files)} files ingested. "
          f"Total chunks in DB: {total}")
    return collection


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Delete and recreate collection before ingesting")
    args = parser.parse_args()
    ingest_all(reset=args.reset)

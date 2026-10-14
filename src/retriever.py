"""
Retrieval module:
- Metadata pre-filtering (permission check before vector search)
- Vector similarity search on filtered corpus
- Priority scoring (unit-level specificity)
- Conflict/version resolution
"""
from pathlib import Path
from typing import Optional
import sys

import chromadb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL,
    TOP_K, MIN_SIMILARITY, PRIORITY_SCORE, ORG_ACCESS, CAP_BAC_ACCESS
)

# ── Singletons (loaded once) ───────────────────────────────────────
_embedder   = None
_chroma     = None
_collection = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder

def _get_collection():
    global _chroma, _collection
    if _collection is None:
        _chroma     = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _chroma.get_collection(COLLECTION_NAME)
    return _collection


# ── Core retrieval ────────────────────────────────────────────────
def retrieve(query: str, user_context: dict, top_k: int = TOP_K) -> dict:
    """
    Main retrieval function with permission-aware filtering.

    Args:
        query:        User's question string
        user_context: Dict with keys:
                        - don_vi   : e.g. "gamota"
                        - cap_bac  : e.g. "nhan_vien"
                        - user_name: e.g. "Nguyen Van A" (for display)
        top_k:        Number of results to retrieve before scoring

    Returns:
        dict with keys:
            - chunks       : list of relevant text chunks (after scoring)
            - sources      : list of source metadata dicts
            - debug_info   : diagnostic information
            - access_denied: bool (True if no accessible docs found)
    """
    collection = _get_collection()
    embedder   = _get_embedder()

    don_vi  = user_context.get("don_vi", "tap_doan")
    cap_bac = user_context.get("cap_bac", "nhan_vien")

    # ── STEP 1: Build access list (which units this user can read) ──
    allowed_units  = ORG_ACCESS.get(don_vi, [don_vi, "tap_doan"])
    allowed_levels = CAP_BAC_ACCESS.get(cap_bac, [cap_bac])

    debug = {
        "query":          query,
        "user_context":   user_context,
        "allowed_units":  allowed_units,
        "allowed_levels": allowed_levels,
        "raw_results":    0,
        "after_scoring":  0,
        "filter_used":    {},
    }

    # ── STEP 2: Metadata pre-filter (BEFORE vector search) ──────────
    # Only retrieve active docs from allowed units
    # ChromaDB WHERE clause enforces permission at DB level
    where_filter = {
        "$and": [
            {"don_vi":     {"$in": allowed_units}},
            {"trang_thai": {"$eq": "active"}},
        ]
    }
    debug["filter_used"] = where_filter

    # ── STEP 3: Embed query + vector similarity search ───────────────
    query_embedding = embedder.encode(query, normalize_embeddings=True).tolist()

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 3, collection.count()),  # over-fetch for scoring
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        return {
            "chunks": [], "sources": [], "debug_info": debug,
            "access_denied": False, "error": str(e)
        }

    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]  # cosine distance (lower = more similar)

    debug["raw_results"] = len(docs)

    if not docs:
        return {"chunks": [], "sources": [], "debug_info": debug, "access_denied": False}

    # ── STEP 4: Filter by cap_bac permission ────────────────────────
    filtered = []
    for doc, meta, dist in zip(docs, metas, distances):
        doc_levels = meta.get("cap_bac", "nhan_vien").split(",")
        # Check if user's level is in doc's allowed levels
        if cap_bac in doc_levels or any(lvl in allowed_levels for lvl in doc_levels):
            similarity = 1 - dist  # convert distance to similarity
            if similarity >= MIN_SIMILARITY:
                filtered.append((doc, meta, similarity))

    # ── STEP 5: Priority scoring + dedup per doc_family ─────────────
    # For each doc_family_id, keep only the highest-priority unit's chunks
    family_best: dict[str, tuple] = {}  # family_id → (priority, unit)

    for doc, meta, sim in filtered:
        family_id = meta.get("doc_family_id", meta.get("doc_id", "unknown"))
        unit      = meta.get("don_vi", "tap_doan")
        priority  = PRIORITY_SCORE.get(unit, 1)

        if family_id not in family_best or priority > family_best[family_id][0]:
            family_best[family_id] = (priority, unit)

    # Keep only chunks from the winning unit per family
    scored = []
    for doc, meta, sim in filtered:
        family_id = meta.get("doc_family_id", meta.get("doc_id", "unknown"))
        unit      = meta.get("don_vi", "tap_doan")
        best_unit = family_best.get(family_id, (0, unit))[1]

        if unit == best_unit:
            scored.append({
                "text":       doc,
                "metadata":   meta,
                "similarity": round(sim, 4),
                "priority":   PRIORITY_SCORE.get(unit, 1),
            })

    # Sort by similarity descending, cap at top_k
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    scored = scored[:top_k]
    debug["after_scoring"] = len(scored)

    # ── STEP 6: Deduplicate sources for citation ─────────────────────
    seen_docs = set()
    sources   = []
    for item in scored:
        meta   = item["metadata"]
        doc_id = meta.get("doc_id", "unknown")
        if doc_id not in seen_docs:
            seen_docs.add(doc_id)
            sources.append({
                "doc_id":        doc_id,
                "doc_family_id": meta.get("doc_family_id", ""),
                "don_vi":        meta.get("don_vi", ""),
                "ngay_hieu_luc": meta.get("ngay_hieu_luc", ""),
                "loai_tai_lieu": meta.get("loai_tai_lieu", ""),
                "similarity":    item["similarity"],
            })

    return {
        "chunks":       [item["text"] for item in scored],
        "sources":      sources,
        "debug_info":   debug,
        "access_denied": False,
    }


def check_access(user_context: dict, required_don_vi: str, required_cap_bac: str) -> bool:
    """Check if a user has access to a specific document."""
    don_vi  = user_context.get("don_vi", "")
    cap_bac = user_context.get("cap_bac", "nhan_vien")

    allowed_units  = ORG_ACCESS.get(don_vi, [])
    allowed_levels = CAP_BAC_ACCESS.get(cap_bac, [cap_bac])

    return required_don_vi in allowed_units and required_cap_bac in allowed_levels

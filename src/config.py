"""
Central configuration for Appota Internal Wiki RAG system.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent.parent
DATA_DIR     = BASE_DIR / "data" / "documents"
CHROMA_DIR   = BASE_DIR / "chromadb_store"

# ── ChromaDB ───────────────────────────────────────────────────────
COLLECTION_NAME = "appota_wiki"

# ── Embedding model (local, free) ─────────────────────────────────
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# ── LLM ───────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = "gemini-2.5-flash-lite"

# ── RAG params ────────────────────────────────────────────────────
TOP_K               = 5       # Number of chunks to retrieve
MIN_SIMILARITY      = 0.45    # Below this → treat as "not found"
CHUNK_SIZE          = 500
CHUNK_OVERLAP       = 80

# ── Priority scoring: lower unit level wins (more specific = higher score) ──
PRIORITY_SCORE = {
    "tap_doan":   1,
    "gamota":     2,
    "appota_pay": 2,
    "hr_dept":    3,
    "game_dev":   3,
    "qa_dept":    3,
    "finance":    3,
}

# ── Org hierarchy: which units can access which parent docs ────────
ORG_ACCESS = {
    "tap_doan":   ["tap_doan"],
    "gamota":     ["gamota", "tap_doan"],
    "appota_pay": ["appota_pay", "tap_doan"],
    "hr_dept":    ["hr_dept", "tap_doan"],
    "game_dev":   ["game_dev", "gamota", "tap_doan"],
    "qa_dept":    ["qa_dept", "gamota", "tap_doan"],
    "finance":    ["finance", "appota_pay", "tap_doan"],
}

# ── Cap bac hierarchy: what levels each role can access ───────────
CAP_BAC_ACCESS = {
    "nhan_vien": ["nhan_vien"],
    "team_lead": ["nhan_vien", "team_lead"],
    "manager":   ["nhan_vien", "team_lead", "manager"],
    "director":  ["nhan_vien", "team_lead", "manager", "director"],
}

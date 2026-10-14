"""
Container entrypoint script for Docker.
Handles automatic initial document ingestion and launches Streamlit.
Platform-independent, avoids Windows/Linux CRLF line ending issues.
"""
import os
import sys
import subprocess
from pathlib import Path

CHROMA_DIR = Path("chromadb_store")

def main():
    # If ChromaDB collection not yet initialized in the container, run ingest
    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        print("[Docker Start] Initializing knowledge base into ChromaDB...", flush=True)
        res = subprocess.run([sys.executable, "src/ingest.py", "--reset"])
        if res.returncode != 0:
            print("[Docker Start] Warning: Ingest finished with errors.", flush=True)
    else:
        print("[Docker Start] ChromaDB store already present.", flush=True)

    print("[Docker Start] Launching Streamlit web application on port 8501...", flush=True)
    # Start Streamlit listening on 0.0.0.0
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true"
    ]
    os.execv(sys.executable, cmd)

if __name__ == "__main__":
    main()

"""
ingest.py
Reads the product FAQ markdown file, splits it into chunks (one chunk per
'## ' section, since each section is a self-contained Q&A), embeds each
chunk using a lightweight local sentence-transformer model, and stores the
embeddings in a persistent ChromaDB collection.

Run this once (and again any time the FAQ document changes):
    python ingest.py
"""

import re
import chromadb
from sentence_transformers import SentenceTransformer

FAQ_PATH = "data/product_faq.md"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "product_faq"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # small (~80MB), runs fine on CPU / 8GB RAM


def load_chunks(path: str):
    """Split the markdown file into chunks by '## ' headers.
    Each chunk keeps its heading as context, which improves retrieval quality."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split on level-2 headers, keep the header text attached to its section
    sections = re.split(r"\n(?=## )", text.strip())
    chunks = [s.strip() for s in sections if s.strip() and not s.strip().startswith("# ")]
    return chunks


def build_index():
    print("Loading embedding model (first run downloads ~80MB)...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print(f"Reading and chunking {FAQ_PATH} ...")
    chunks = load_chunks(FAQ_PATH)
    print(f"Found {len(chunks)} chunks.")

    print("Computing embeddings...")
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    print("Writing to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Fresh start each time ingest.py is run
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME)
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
    )

    print(f"Done. Indexed {len(chunks)} chunks into '{COLLECTION_NAME}' at ./{CHROMA_DIR}")


if __name__ == "__main__":
    build_index()

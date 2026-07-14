"""
RAG ingestion pipeline.

Loads personal documents (.md / .txt / .pdf) from ./data_v2, splits them into
overlapping chunks, embeds them with OpenAI's text-embedding-3-small model,
and persists everything into a local ChromaDB collection at ./chroma_db.

Markdown files may include YAML frontmatter (company, topics, skills, etc.).
Those fields are parsed and stored as ChromaDB metadata on every chunk from
the file, enabling metadata-filtered retrieval in the backend.

Underscore-prefixed files (e.g. _meta.md, the human-maintained index) are
skipped — they document the corpus and must not become corpus content.

Run as a standalone script. Both modes fully rebuild the named collection
(the existing collection is always deleted before re-embedding):
    python ingest.py            # rebuild the collection in place
    python ingest.py --rebuild  # additionally wipe the whole ./chroma_db dir
"""

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# Force UTF-8 output on Windows so special characters in chunk previews
# don't crash the console (Windows default is cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import frontmatter as fm
from dotenv import load_dotenv

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ---------- Configuration ----------
DATA_DIR = Path("./data_v2")
CHROMA_DIR = Path("./chroma_db")
METADATA_EXPORT = Path("./chunks_metadata.json")
COLLECTION_NAME = "vaughn_personal_docs"

# Larger chunks preserve full narrative sections (STAR stories, architecture
# explanations) that were previously fragmented at 500 chars (~100 tokens).
# 1800 chars ≈ 450 tokens — keeps most ## sections intact in a single chunk.
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 200

EMBEDDING_MODEL = "text-embedding-3-small"
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


def banner(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------- Frontmatter helpers ----------

def _list_to_meta_str(value) -> str:
    """
    Convert a frontmatter list (e.g. [java, spring_boot]) to a
    comma-separated string. ChromaDB metadata values must be scalar.
    """
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value) if value is not None else ""


def parse_frontmatter(path: Path) -> dict:
    """
    Parse YAML frontmatter from a markdown file and return a flat dict of
    scalar metadata values suitable for ChromaDB storage.

    Fields extracted:
      doc_name    — human-readable document title
      description — one-line summary of the document's contents
      company     — employer or "none" for personal projects
      source      — provenance marker (e.g. "github_dag" for DAG-generated files)
      repo_url    — GitHub repository URL for project files
      topics      — comma-separated topic tags
      skills      — comma-separated skill tags
      story_types — comma-separated story-type tags

    Returns an empty dict for non-markdown files or files without frontmatter.
    """
    if path.suffix.lower() not in {".md", ".txt"}:
        return {}
    try:
        post = fm.load(str(path))
        meta = post.metadata
        result = {}
        if meta.get("name"):
            result["doc_name"] = str(meta["name"])
        if meta.get("description"):
            result["description"] = str(meta["description"])
        if meta.get("company"):
            result["company"] = str(meta["company"])
        if meta.get("source"):
            result["source"] = str(meta["source"])
        if meta.get("repo_url"):
            result["repo_url"] = str(meta["repo_url"])
        if meta.get("topics"):
            result["topics"] = _list_to_meta_str(meta["topics"])
        if meta.get("skills"):
            result["skills"] = _list_to_meta_str(meta["skills"])
        if meta.get("story_types"):
            result["story_types"] = _list_to_meta_str(meta["story_types"])
        return result
    except Exception as e:
        print(f"  [frontmatter] could not parse {path.name}: {e}")
        return {}


# ---------- Document loading ----------

def load_documents(data_dir: Path) -> list:
    """
    Walk `data_dir` and load every supported file with the appropriate
    LangChain loader. Tags each Document with base metadata (filename,
    doc_id) plus any YAML frontmatter fields found in the file.
    """
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory '{data_dir}' does not exist. "
            f"Create it and drop .md/.txt/.pdf files inside, then re-run."
        )

    files = sorted(p for p in data_dir.iterdir() if p.is_file())
    if not files:
        raise FileNotFoundError(
            f"No files found in '{data_dir}'. Add at least one .md/.txt/.pdf "
            f"document and re-run."
        )

    docs = []
    for path in files:
        # Underscore-prefixed files (e.g. _meta.md) are human-facing indexes
        # that describe the corpus — ingesting them would pollute retrieval.
        if path.name.startswith("_"):
            print(f"[skip] {path.name} (underscore-prefixed index file)")
            continue

        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            print(f"[skip] {path.name} (unsupported extension {ext})")
            continue

        try:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[error] could not read {path.name} from disk: {e}")
            continue
        raw_chars = len(raw_text)

        # Parse YAML frontmatter before loading (loader may strip it).
        frontmatter_meta = parse_frontmatter(path)

        try:
            if ext == ".pdf":
                loader = PyPDFLoader(str(path))
            else:
                loader = TextLoader(str(path), encoding="utf-8")

            loaded = loader.load()
        except Exception as e:
            print(f"[error] failed to load {path.name}: {e}")
            continue

        doc_id = path.stem
        for d in loaded:
            d.metadata["filename"] = path.name
            d.metadata["doc_id"] = doc_id
            d.metadata["_raw_char_count"] = raw_chars
            # Merge frontmatter fields — these propagate to every chunk.
            d.metadata.update(frontmatter_meta)

        docs.extend(loaded)

        loaded_chars = sum(len(d.page_content) for d in loaded)
        ratio = (loaded_chars / raw_chars * 100) if raw_chars else 0.0
        fm_keys = list(frontmatter_meta.keys())
        print(f"[load] {path.name}  ({loaded_chars}/{raw_chars} chars, {ratio:.0f}%)"
              f"  frontmatter={fm_keys or 'none'}")

    if not docs:
        raise RuntimeError("No documents were successfully loaded.")

    return docs


# ---------- Chunking ----------

def chunk_documents(docs: list) -> list:
    """
    Split documents into chunks using a header-aware recursive splitter.

    Separators are tried in order: markdown headers first (## / ###), then
    paragraph breaks, then lines, then words. This keeps entire ## sections
    together whenever they fit within CHUNK_SIZE, which preserves STAR
    stories, architecture descriptions, and other narrative units that were
    previously fragmented at 500 chars.

    Each chunk inherits the full metadata of its parent document (including
    any frontmatter fields). A sequential chunk_id is assigned per doc_id.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
        length_function=len,
    )
    chunks = splitter.split_documents(docs)

    counters: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        doc_id = chunk.metadata.get("doc_id", "unknown")
        chunk.metadata["chunk_id"] = counters[doc_id]
        counters[doc_id] += 1

    print(f"[chunk] produced {len(chunks)} chunks across {len(counters)} doc(s)")

    by_file: dict[str, list] = defaultdict(list)
    for chunk in chunks:
        by_file[chunk.metadata.get("filename", "unknown")].append(chunk)

    for filename, file_chunks in by_file.items():
        first_chunk = file_chunks[0].page_content[:120].replace("\n", " ")
        print(f"  -> {filename}: {len(file_chunks)} chunks | first: {first_chunk!r}")

    return chunks


# ---------- Vector store ----------

def build_vectorstore(chunks: list) -> Chroma:
    """Embed chunks with OpenAI and persist them into a local Chroma collection."""
    import chromadb

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    
    incoming = len(chunks)
    print(f"[embed] sending {incoming} chunks to OpenAI for embedding...")

    for c in chunks:
        c.metadata.pop("_raw_char_count", None)

    if os.environ.get("CHROMA_MODE") == "http":

        try:
            client = chromadb.HttpClient(
                host=os.environ.get("CHROMA_HOST"),
                port=int(os.environ.get("CHROMA_PORT", "8001")),
            )
            existing = [c.name for c in client.list_collections()]
            if COLLECTION_NAME in existing:
                client.delete_collection(COLLECTION_NAME)
                print(f"[build] deleted existing collection '{COLLECTION_NAME}'")
        except Exception as e:
            print(f"[build] could not delete existing collection (may not exist): {e}")


        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
            client=chromadb.HttpClient(
                host=os.environ.get("CHROMA_HOST"),
                port=int(os.environ.get("CHROMA_PORT", "8001")),
            ),
        )
        print(f"[store] persisted to ChromaDB at {os.environ.get('CHROMA_HOST')}:{os.environ.get('CHROMA_PORT')}")
    else:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            existing = [c.name for c in client.list_collections()]
            if COLLECTION_NAME in existing:
                client.delete_collection(COLLECTION_NAME)
                print(f"[build] deleted existing collection '{COLLECTION_NAME}'")
        except Exception as e:
            print(f"[build] could not delete existing collection (may not exist): {e}")

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
            persist_directory=str(CHROMA_DIR),
        )
        print(f"[store] persisted to {CHROMA_DIR.resolve()}")


    stored = vectorstore._collection.count()
    
    print(f"[verify] incoming: {incoming}  stored: {stored}")
    if stored != incoming:
        print(f"[verify] WARNING: {incoming - stored} chunks were dropped")

    db_records = vectorstore._collection.get(include=["metadatas"])
    db_by_file: dict[str, int] = defaultdict(int)
    for meta in db_records["metadatas"]:
        db_by_file[meta.get("filename", "unknown")] += 1

    print("[verify] per-file counts in DB:")
    for filename, count in sorted(db_by_file.items()):
        print(f"           {filename}: {count}")

    return vectorstore


# ---------- Metadata export ----------

def export_metadata(chunks: list, path: Path) -> None:
    """Write a JSON file describing every chunk for manual inspection."""
    records = []
    for chunk in chunks:
        text = chunk.page_content
        record = {
            "filename": chunk.metadata.get("filename"),
            "doc_id": chunk.metadata.get("doc_id"),
            "chunk_id": chunk.metadata.get("chunk_id"),
            "char_count": len(text),
            "preview": text[:120].replace("\n", " "),
        }
        # Include frontmatter fields if present.
        for key in ("doc_name", "description", "company", "source", "repo_url",
                    "topics", "skills", "story_types"):
            if key in chunk.metadata:
                record[key] = chunk.metadata[key]
        records.append(record)

    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"[export] wrote {len(records)} chunk records to {path.resolve()}")


# ---------- Smoke test ----------

def test_query(vectorstore: Chroma, query: str) -> None:
    print(f'\nQuery: "{query}"')
    results = vectorstore.similarity_search(query, k=3)
    if not results:
        print("  (no results)")
        return
    for i, doc in enumerate(results, start=1):
        meta = doc.metadata
        snippet = doc.page_content[:200].replace("\n", " ")
        company = meta.get("company", "")
        print(
            f"  #{i}  {meta.get('filename')}  chunk_id={meta.get('chunk_id')}"
            f"  company={company!r}\n      {snippet}..."
        )


# ---------- Entry point ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="RAG ingestion pipeline.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Wipe the existing Chroma collection before ingesting.",
    )
    args = parser.parse_args()

    load_dotenv()

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "ERROR: OPENAI_API_KEY is not set. Copy .env.example to .env and "
            "fill in your key, or export it in your shell."
        )
        return 1

    if args.rebuild and CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)
        print(f"[rebuild] removed existing collection at {CHROMA_DIR}")

    try:
        banner("Step 1: Loading documents")
        docs = load_documents(DATA_DIR)

        banner("Step 2: Chunking documents")
        chunks = chunk_documents(docs)

        banner("Step 3: Embedding & storing in ChromaDB")
        vectorstore = build_vectorstore(chunks)

        banner("Step 4: Exporting chunk metadata")
        export_metadata(chunks, METADATA_EXPORT)

        banner("Step 5: Test queries")
        test_query(vectorstore, "What experience does Vaughn have?")
        test_query(vectorstore, "Tell me about TrackSync at SRC")

        banner("Final summary")
        chunks_by_file: dict[str, int] = defaultdict(int)
        for c in chunks:
            chunks_by_file[c.metadata.get("filename", "unknown")] += 1

        for filename in sorted(chunks_by_file):
            print(f"  {filename}: {chunks_by_file[filename]} chunks")

        print("\nDone.")
        return 0

    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

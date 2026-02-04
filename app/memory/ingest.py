"""
Data Ingestion Script using Semantic Chunking.
Clears existing data and re-ingests with improved chunking.
"""

from pathlib import Path
from app.memory.vector import VectorStore
from app.memory.chunker import SemanticChunker
from app.config.intent_config import invalidate_cache


def ingest_data(data_path: str = "data", clear_existing: bool = True):
    """
    Ingest data from any text files using adaptive semantic chunking.

    Args:
        data_path: Path to data directory
        clear_existing: Whether to clear existing data before ingesting
    """
    # Initialize store and chunker
    store = VectorStore()
    chunker = SemanticChunker(min_chunk_size=100, max_chunk_size=1500)

    # Clear existing data if requested
    if clear_existing:
        store.clear()

    data_dir = Path(data_path)

    if not data_dir.exists():
        print(f"❌ Error: Directory {data_dir} does not exist!")
        print(
            f"💡 Create a '{data_path}' folder and add your personal data files.")
        print(f"   Supported formats: .md, .txt, .yaml, .yml, .json")
        return

    print(f"🤖 Personal RAG Chatbot Data Ingestion")
    print(f"📁 Processing data from: {data_dir.absolute()}")
    print("-" * 60)

    # Collect all chunks
    texts = []
    metadata_list = []

    for chunk in chunker.chunk_directory(data_dir):
        texts.append(chunk.content)
        metadata_list.append(chunk.metadata)

        # Debug output with better formatting
        tech_info = f" [Tech: {chunk.metadata['technologies']}]" if chunk.metadata.get(
            'technologies') else ""
        section_name = chunk.metadata['section'][:50] + "..." if len(
            chunk.metadata['section']) > 50 else chunk.metadata['section']
        print(f"  ✓ {chunk.metadata['type']}: {section_name}{tech_info}")

    # Add to store
    if texts:
        print(f"\n📚 Adding {len(texts)} chunks to vector store...")
        store.add(texts, metadata_list)
        print("-" * 60)
        print(f"✅ Successfully ingested {len(texts)} chunks")
        print(f"📊 Total documents in memory: {store.collection.count()}")

        # Summary by type
        type_counts = {}
        for meta in metadata_list:
            t = meta.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        print(f"\n📈 Data distribution:")
        for t, count in sorted(type_counts.items()):
            print(f"   - {t}: {count} chunks")

        # Invalidate intent config cache to pick up new data types
        invalidate_cache()
        print(f"\n🔄 Intent configuration updated for available data types")

        print(f"\n🚀 Your personal chatbot is ready!")
        print(f"   Start with: uvicorn app.main:app --reload")
    else:
        print("❌ No suitable files found to ingest.")
        print("\n💡 Make sure your data directory contains files with these extensions:")
        print("   .md (Markdown), .txt (Text), .yaml/.yml (YAML), .json (JSON)")
        print("\n📝 Example file structure:")
        print("   data/")
        print("   ├── about_me.md       # Personal summary")
        print("   ├── experience.md     # Work experience")
        print("   ├── projects.md       # Personal projects")
        print("   ├── skills.yaml       # Technical skills")
        print("   └── education.txt     # Educational background")


def main():
    """Main entry point for ingestion script."""
    print("=" * 60)
    ingest_data()
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")

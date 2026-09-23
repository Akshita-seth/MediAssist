# ============================================
# embed_store.py — ADD these imports/functions
# (keep everything already in the file as-is)
# ============================================

from sentence_transformers import SentenceTransformer
import chromadb
from chunker import build_chunks
import os

model = SentenceTransformer('all-MiniLM-L6-v2')

chroma_client = chromadb.PersistentClient(path="data/chroma_db")
collection = chroma_client.get_or_create_collection(name="mediassist_chunks")

# NEW: separate in-memory client for uploaded docs — never touches disk,
# never mixes with the evaluated 24-doc corpus above.
ephemeral_client = chromadb.Client()


def embed_text(text):
    embedding = model.encode(text)
    return embedding


def store_chunks(pdf_path):
    chunks = build_chunks(pdf_path)

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{pdf_path}_{i}"
        embedding = embed_text(chunk["content"]).tolist()

        ids.append(chunk_id)
        embeddings.append(embedding)
        documents.append(chunk["content"])
        filename_only = os.path.basename(pdf_path)
        metadatas.append({"source": filename_only, "section": chunk["section"]})

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    return len(chunks)


def store_all_pdfs(pdf_folder):
    total_chunks = 0
    for filename in os.listdir(pdf_folder):
        if filename.endswith('.pdf'):
            path = os.path.join(pdf_folder, filename)
            count = store_chunks(path)
            total_chunks += count
            print(f"Stored {count} chunks from {filename}")
    return total_chunks


def retrieve(query, source_doc=None, top_k=3):
    query_embedding = embed_text(query).tolist()

    where_filter = {"source": source_doc} if source_doc else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )
    return results


# ---- NEW: ephemeral (upload-scoped) versions ----

def store_chunks_ephemeral(pdf_path, collection_name):
    """
    Same pipeline as store_chunks(), but writes into a session-scoped,
    in-memory collection instead of the persistent evaluated corpus.
    """
    coll = ephemeral_client.get_or_create_collection(name=collection_name)
    chunks = build_chunks(pdf_path)

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{pdf_path}_{i}"
        embedding = embed_text(chunk["content"]).tolist()

        ids.append(chunk_id)
        embeddings.append(embedding)
        documents.append(chunk["content"])
        filename_only = os.path.basename(pdf_path)
        metadatas.append({"source": filename_only, "section": chunk["section"]})

    coll.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    return len(chunks)


def retrieve_ephemeral(query, collection_name, source_doc=None, top_k=3):
    coll = ephemeral_client.get_or_create_collection(name=collection_name)
    query_embedding = embed_text(query).tolist()

    where_filter = {"source": source_doc} if source_doc else None

    results = coll.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )
    return results


if __name__ == "__main__":
    results = retrieve(
        "What was the patient's hemoglobin level?",
        source_doc="discharge_01.pdf"
    )
    for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
        print(f"[{dist:.3f}] ({meta['section']}, {meta['source']})")
        print(f"  {doc}")
        print()
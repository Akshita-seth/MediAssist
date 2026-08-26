from sentence_transformers import SentenceTransformer
import chromadb
from chunker import build_chunks
import os

model = SentenceTransformer('all-MiniLM-L6-v2')

chroma_client = chromadb.PersistentClient(path="data/chroma_db")
collection = chroma_client.get_or_create_collection(name="mediassist_chunks")


def embed_text(text):
    embedding = model.encode(text)
    return embedding


def store_chunks(pdf_path):
    chunks = build_chunks(pdf_path)

    ids = []  #unique identifiers for each chunk
    embeddings = []  #embedding vectors for each chunk
    documents = []   #the actual text content of each chunk
    metadatas = []   #metadata associated with each chunk, such as source and section

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

# FOR STORING ALL PDFS IN THE FOLDER [Only gets called from just below main]
def store_all_pdfs(pdf_folder):
    total_chunks = 0
    for filename in os.listdir(pdf_folder):
        if filename.endswith('.pdf'):
            path = os.path.join(pdf_folder, filename)
            count = store_chunks(path)
            total_chunks += count
            print(f"Stored {count} chunks from {filename}")
    return total_chunks

# TESTING FOR all PDFs in the folder storef in DB or not
# if __name__ == "__main__":
#     total = store_all_pdfs("data/raw_pdfs")
#     print(f"\nTotal chunks stored: {total}")
#     print("Total items in collection:", collection.count())


def retrieve(query, source_doc=None, top_k=3):
    query_embedding = embed_text(query).tolist()
    
    where_filter = {"source": source_doc} if source_doc else None
    
    results = collection.query(
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



import chromadb
import datetime

def get_next_version(collection, doc_id):
    # Use .get() to just fetch metadata, without requiring any query vector
    results = collection.get(
        where={"doc_id": doc_id},
        include=["metadatas"]
    )
    versions = [meta["version"] for meta in results["metadatas"] if "version" in meta]
    return max(versions, default=0) + 1


def save_to_chromadb(doc_id, version, stage, text, is_final=False, collection=None):
    if collection is None:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection(name="book_chapters")
    timestamp = datetime.datetime.now().isoformat()
    collection.add(
        documents=[text],
        ids=[f"{doc_id}_v{version}_{stage}"],
        metadatas=[{
            "doc_id": doc_id,
            "version": version,
            "stage": stage,
            "timestamp": timestamp,
            "is_final": is_final,
        }],
    )

def save_initial_versions(doc_id):
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="book_chapters")
    with open(f"output/{doc_id}.txt", "r", encoding="utf-8") as f:
        og_text = f.read()
    with open(f"output/{doc_id}_spun.txt", "r", encoding="utf-8") as f:
        spun_text = f.read()
    with open(f"output/{doc_id}_reviewed.txt", "r", encoding="utf-8") as f:
        reviewed_text = f.read()
    save_to_chromadb(doc_id, 1, "og", og_text, is_final=False, collection=collection)
    save_to_chromadb(doc_id, 2, "spun", spun_text, is_final=False, collection=collection)
    save_to_chromadb(doc_id, 3, "reviewed", reviewed_text, is_final=False, collection=collection)
    print(f"Initial versions for {doc_id} saved to ChromaDB.")

import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="book_chapters")
results = collection.get(include=['metadatas', 'documents'])

print("Number of documents:", len(results['documents']))
for i in range(len(results['documents'])):
    print(f"ID: {results['ids'][i]}")
    print(f"Metadata: {results['metadatas'][i]}")
    # Don't print the text/document itself
    print('-' * 40)
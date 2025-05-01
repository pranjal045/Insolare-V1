from sentence_transformers import SentenceTransformer
import json

def generate_embeddings(texts, model_name='all-MiniLM-L6-v2'):
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts)
    return embeddings

if __name__ == '__main__':
    texts = ["Sample text for embedding generation.", "Another document text."]
    embeddings = generate_embeddings(texts)
    # Save embeddings for further use (e.g., in Pinecone or FAISS)
    with open("embeddings.json", "w") as f:
        json.dump(embeddings.tolist(), f)
    print("Embeddings generated and saved.")
import os
from sentence_transformers import SentenceTransformer
import numpy as np

# Initialize the BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Folders
input_dir = '/workspaces/Main-Insolare-/normalized_text'
chunk_output_dir = './chunked_text'
embedding_output_dir = './embeddings'

os.makedirs(chunk_output_dir, exist_ok=True)
os.makedirs(embedding_output_dir, exist_ok=True)

def bert_based_chunking(text, chunk_size=100):
    sentences = text.split('.')
    chunks = []
    current_chunk = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        current_chunk.append(sentence)
        if len(' '.join(current_chunk).split()) >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def get_embeddings(chunks):
    return model.encode(chunks)

# 👇 Add this to expose the function for run_pipeline.py
chunk_text_semantically = bert_based_chunking

if __name__ == '__main__':
    for filename in os.listdir(input_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(input_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()

            chunks = bert_based_chunking(text)
            embeddings = get_embeddings(chunks)

            # Save chunks
            chunk_file = os.path.join(chunk_output_dir, filename)
            with open(chunk_file, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(chunk.strip() + '\n---\n')

            # Save embeddings
            emb_file = os.path.join(embedding_output_dir, filename.replace('.txt', '.npy'))
            np.save(emb_file, embeddings)

            print(f"✅ Chunked: {filename} into {len(chunks)} chunks.")

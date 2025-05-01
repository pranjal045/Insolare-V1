import os
import json
import numpy as np

def load_embeddings_and_chunks(embeddings_dir='/workspaces/Main-Insolare-/embeddings', chunks_dir='/workspaces/Main-Insolare-/chunked_text'):
    data = []
    for file in os.listdir(embeddings_dir):
        if file.endswith('.npy'):
            embedding_path = os.path.join(embeddings_dir, file)
            chunks_path = os.path.join(chunks_dir, file.replace('.npy', '.json'))

            if os.path.exists(chunks_path):
                embeddings = np.load(embedding_path)
                with open(chunks_path, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                data.append({
                    'file_name': file.replace('.npy', ''),
                    'embeddings': embeddings,
                    'chunks': chunks
                })
    return data

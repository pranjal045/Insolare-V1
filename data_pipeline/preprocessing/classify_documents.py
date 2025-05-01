import os
import json
from transformers import pipeline
from tqdm import tqdm

# Define your document type labels
CANDIDATE_LABELS = [
    "EPC Agreement",
    "Power Purchase Agreement (PPA)",
    "Tender Document",
    "Deed of Adherence",
    "Memorandum of Understanding (MoU)",
    "Technical Specification",
    "Channel Partner Agreement"
]

# Set up HuggingFace zero-shot classification pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def classify_chunks(chunks, labels=CANDIDATE_LABELS):
    """Classifies each chunk and returns predicted labels with scores."""
    predictions = []
    for chunk in chunks:
        result = classifier(chunk, candidate_labels=labels)
        predictions.append(result)
    return predictions

def majority_vote(predictions):
    """Aggregate predictions across chunks using majority vote."""
    if not predictions:
        return "Unknown" # Handle case with no predictions
	
    label_scores = {}
    for result in predictions:
        label = result['labels'][0]
        score = result['scores'][0]
        if label not in label_scores:
            label_scores[label] = 0
        label_scores[label] += score
    # Check if any labels were found
    if not label_scores:
        return "Unknown" 
    return max(label_scores, key=label_scores.get)

# New function for pipeline integration
def classify_single_document(chunks_list, labels=CANDIDATE_LABELS):
    """Classifies a single document based on its list of text chunks."""
    if not chunks_list:
        return "Unknown" # Handle empty input
    predictions = classify_chunks(chunks_list, labels=labels)
    final_label = majority_vote(predictions)
    return final_label

def load_chunks(folder_path):
    """Load chunked text from folder as dict: filename -> [chunks]"""
    chunked_docs = {}
    for fname in os.listdir(folder_path):
        if fname.endswith('.txt'):
            file_path = os.path.join(folder_path, fname)
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                # Assuming chunks are split by consistent delimiter, e.g., '\n\n' or '---'
                # Let's try splitting by double newline first, then '---'
                potential_chunks = text.split('\n\n')
                if len(potential_chunks) <= 1:
                    potential_chunks = text.split('---') # Fallback to '---'
                
                chunked_docs[fname] = [chunk.strip() for chunk in potential_chunks if chunk.strip()]
    return chunked_docs

def classify_documents(chunked_folder, output_path='document_type_labels.json'):
    chunked_docs = load_chunks(chunked_folder)
    results = {}

    print(f"🔍 Classifying {len(chunked_docs)} documents...")
    for doc_name, chunks in tqdm(chunked_docs.items()):
        predictions = classify_chunks(chunks)
        label = majority_vote(predictions)
        results[doc_name] = label

    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Classification completed. Results saved to `{output_path}`")

if __name__ == '__main__':
    # Example usage for standalone script
    # Ensure 'chunked_text' directory exists and contains chunked .txt files
    if not os.path.exists('chunked_text'):
        print("Error: 'chunked_text' directory not found. Please create it and add chunked files.")
    else:
        classify_documents('chunked_text')

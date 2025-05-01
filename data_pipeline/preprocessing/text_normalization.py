import os
import re
from pathlib import Path

# Set BASE_DIR to the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTRACTED_DIR = BASE_DIR / "input_texts/extracted_text"
NORMALIZED_DIR = BASE_DIR / "normalized_text"

os.makedirs(NORMALIZED_DIR, exist_ok=True)

def remove_boilerplate(text):
    # Example: remove headers, footers, disclaimers
    text = re.sub(r'(?i)(header:|footer:|disclaimer:).*', '', text)
    return text

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'\b(\d{1,2}\/\d{1,2}\/\d{2,4})\b', 'DATE', text)  # Normalize dates
    text = re.sub(r'[$€£]\s?\d+(\.\d+)?', 'CURRENCY', text)          # Normalize currency
    text = re.sub(r'\s+', ' ', text).strip()                         # Clean extra spaces
    return text

def process_files():
    for file_name in os.listdir(EXTRACTED_DIR):
        if file_name.endswith(".txt"):
            input_path = os.path.join(EXTRACTED_DIR, file_name)
            output_path = os.path.join(NORMALIZED_DIR, file_name)

            with open(input_path, 'r', encoding='utf-8') as infile:
                raw_text = infile.read()

            cleaned = remove_boilerplate(raw_text)
            normalized = normalize_text(cleaned)

            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write(normalized)

            print(f"✅ Normalized: {output_path}")

if __name__ == '__main__':
    process_files()

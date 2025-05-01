import os
from docx import Document

INPUT_DIR = "/workspaces/Main-Insolare-/raw_document"
OUTPUT_DIR = "/workspaces/Main-Insolare-/extracted_text"

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def save_text_to_file(text, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".docx"):
            input_path = os.path.join(INPUT_DIR, filename)
            output_filename = os.path.splitext(filename)[0] + ".txt"
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            text = extract_text_from_docx(input_path)
            save_text_to_file(text, output_path)
            print(f"✅ Saved: {output_path}")

if __name__ == "__main__":
    main()

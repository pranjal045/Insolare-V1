import os
import sys
import json
import logging
from pathlib import Path

# 👇 Ensure proper module imports within Codespaces
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Optional: PDF support
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logging.warning("PyMuPDF not installed. PDF support disabled. Use: pip install pymupdf")

# ✅ Updated imports with module-qualified paths
from data_pipeline.preprocessing.ocr_processing import extract_text_from_docx
from data_pipeline.preprocessing.text_normalization import normalize_text
from data_pipeline.preprocessing.chunking_strategies import chunk_text_semantically
from data_pipeline.preprocessing.classify_documents import classify_single_document
from data_pipeline.preprocessing.extract_fields import extract_fields_from_text

# --- Config ---
BASE_DIR = Path("/workspaces/Insolare-V1")
INPUT_DIR = BASE_DIR / "raw_document"
OUTPUT_DIR = BASE_DIR / "structured_output"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- PDF Text Extraction ---
def extract_text_from_pdf(file_path: Path) -> str:
    if not fitz:
        raise ImportError("PyMuPDF not installed. Cannot extract PDF text.")
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

# --- Main Pipeline ---
def run_pipeline(input_file_path: Path, output_dir: Path):
    logging.info(f"🔍 Processing: {input_file_path.name}")
    results = {
        "source_file": input_file_path.name,
        "raw_text": None,
        "normalized_text": None,
        "chunks": None,
        "document_type": None,
        "extracted_fields": None,
        "error": None
    }

    try:
        # Step 1: Text Extraction
        if input_file_path.suffix == ".docx":
            raw_text = extract_text_from_docx(str(input_file_path))
        elif input_file_path.suffix == ".pdf":
            raw_text = extract_text_from_pdf(input_file_path)
        else:
            raise ValueError(f"Unsupported file format: {input_file_path.suffix}")

        if not raw_text.strip():
            raise ValueError("No text extracted.")

        results["raw_text"] = raw_text
        logging.info(f"📝 Text extracted: {raw_text[:150]}...")

        # Step 2: Text Normalization
        cleaned_text = normalize_text(raw_text)
        results["normalized_text"] = cleaned_text
        logging.info("✅ Text normalized")

        # Step 3: Chunking
        chunks = chunk_text_semantically(cleaned_text)
        results["chunks"] = chunks
        logging.info(f"🧩 {len(chunks)} chunks created")

        # Step 4: Classification
        doc_type = classify_single_document(chunks)
        results["document_type"] = doc_type
        logging.info(f"📂 Document classified as: {doc_type}")

        # Step 5: Field Extraction
        extracted = extract_fields_from_text(cleaned_text)
        results["extracted_fields"] = extracted
        logging.info("🔍 Key fields extracted")

    except Exception as e:
        logging.error(f"❌ Pipeline failed: {e}", exc_info=True)
        results["error"] = str(e)

    # Step 6: Save Results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_file_path.stem}.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        logging.info(f"📁 Output saved: {output_path}")
    except Exception as e:
        logging.error(f"❌ Failed to save output: {e}")

    logging.info(f"✅ Finished processing: {input_file_path.name}")
    return results

# --- Main Runner ---
if __name__ == "__main__":
    logging.info("🚀 Starting Pipeline")
    if not INPUT_DIR.exists():
        logging.error(f"Missing input dir: {INPUT_DIR}")
        exit(1)

    supported = [".docx", ".pdf"]
    files = [f for f in INPUT_DIR.iterdir() if f.is_file() and f.suffix in supported]

    if not files:
        logging.warning("No files found to process.")
    else:
        for file in files:
            run_pipeline(file, OUTPUT_DIR)

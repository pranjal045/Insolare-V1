from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from schemas import DocumentRequest, DocumentResponse
from validation_workflow import validate_document
import json
import os

app = FastAPI(title="InSolare LLM Document Processing API")

# === Existing Endpoint: Process Document ===
@app.post("/process", response_model=DocumentResponse)
async def process_document(request: DocumentRequest):
    processed_data = validate_document(request.text)
    return DocumentResponse(result=processed_data)

# === New Endpoint: Mark Paid Tenders ===
LOG_PATH = "/workspaces/Main-Insolare-/data_pipeline/ingestion/tender_log.json"

class PaymentRequest(BaseModel):
    doc_id: str  # Must match key in tender_log.json

@app.post("/mark-as-paid/")
def mark_as_paid(data: PaymentRequest):
    if not os.path.exists(LOG_PATH):
        raise HTTPException(status_code=404, detail="Log not found")

    with open(LOG_PATH, "r") as f:
        log = json.load(f)

    if data.doc_id not in log:
        raise HTTPException(status_code=404, detail="Document not found in log")

    log[data.doc_id]["paid"] = True
    log[data.doc_id]["downloaded"] = True

    # (Optional) Trigger run_pipeline(file_path) if downloaded after payment

    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=4)

    return {"message": f"{data.doc_id} marked as paid and ready for processing."}

# === Run with Uvicorn ===
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

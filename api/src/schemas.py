from pydantic import BaseModel

class DocumentRequest(BaseModel):
    text: str

class DocumentResponse(BaseModel):
    result: dict
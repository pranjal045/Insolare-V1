# API Specification

## POST /process

### Request Body
- **text** (string): The raw document text.

### Response
- **result** (object): Contains the extracted clauses, classification, and compliance details.

Example:
```json
{
  "result": {
    "clauses": ["Termination clause", "Penalty clause"],
    "compliance": "MNRE regulations found",
    "classification": "PPA Contract"
  }
}
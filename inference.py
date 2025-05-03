import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSequenceClassification

# Set model and tokenizer paths
finetuned_path = "finetuned_model"
base_model_name = "distilbert-base-uncased"

def get_tokenizer():
    # Try to load tokenizer from finetuned_model, else fallback to base model
    try:
        return AutoTokenizer.from_pretrained(finetuned_path)
    except Exception:
        return AutoTokenizer.from_pretrained(base_model_name)

def get_model():
    # Try to load model from finetuned_model
    try:
        return AutoModelForCausalLM.from_pretrained(finetuned_path)
    except Exception:
        # If fails, try sequence classification (for distilbert)
        return AutoModelForSequenceClassification.from_pretrained(finetuned_path)

tokenizer = get_tokenizer()
model = get_model()

def generate_response(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model(**inputs)
    logits = outputs.logits
    predicted_class_id = logits.argmax().item()
    return f"Predicted class: {predicted_class_id}"

if __name__ == "__main__":
    while True:
        user_input = input("Enter your prompt (or type 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        response = generate_response(user_input)
        print("Model Response:", response)
import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import ast

# Load model and tokenizer only once when the module is imported
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device set to use {device}")

model_name = "gpt2"  # You can try other models too
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
model.eval()

def extract_fields_from_text(text_input: str) -> dict:
    """
    Extracts structured fields like name, email, and city from raw text using a language model.
    Handles long texts by splitting into smaller chunks.
    """
    prompt_template = """Extract the customer name, email, and city from the following text:\n\n{text}\n\nRespond only with a JSON object in the format:\n{{\n  \"name\": \"\",\n  \"email\": \"\",\n  \"city\": \"\"\n}}"""
    max_length = getattr(model.config, 'n_positions', 1024)
    # Reserve some tokens for the prompt instructions
    reserved_tokens = 100
    chunk_size = max_length - reserved_tokens
    # Tokenize the text and split into chunks
    input_ids = tokenizer.encode(text_input, add_special_tokens=False)
    chunks = [input_ids[i:i+chunk_size] for i in range(0, len(input_ids), chunk_size)]
    for chunk in chunks:
        chunk_text = tokenizer.decode(chunk)
        prompt = prompt_template.format(text=chunk_text)
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        # Truncate if needed
        if inputs['input_ids'].shape[1] > max_length:
            inputs['input_ids'] = inputs['input_ids'][:, :max_length]
            if 'attention_mask' in inputs:
                inputs['attention_mask'] = inputs['attention_mask'][:, :max_length]
        outputs = model.generate(**inputs, max_new_tokens=100)
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print("\n--- Model Output ---")
        print(generated_text)
        json_match = re.search(r"\{.*?\}", generated_text, re.DOTALL)
        if json_match:
            try:
                extracted = ast.literal_eval(json_match.group())
                # Return the first valid extraction
                if any(extracted.values()):
                    return extracted
            except Exception as e:
                print("❌ Failed to parse dictionary:", e)
    print("❌ No dictionary-like structure found in model output.")
    return {}

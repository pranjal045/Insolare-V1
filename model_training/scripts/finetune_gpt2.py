import os
import json
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling, LineByLineTextDataset
import torch

def get_dataset(tokenizer, data_dir, block_size=128):
    all_text = ""
    file_count = 0
    text_count = 0
    for file in Path(data_dir).glob("*.json"):
        file_count += 1
        with open(file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if "raw_text" in data and data["raw_text"] and isinstance(data["raw_text"], str) and data["raw_text"].strip():
                    all_text += data["raw_text"].strip() + "\n"
                    text_count += 1
                else:
                    print(f"No 'raw_text' found or empty in: {file}")
            except Exception as e:
                print(f"Error reading {file}: {e}")
    print(f"Found {file_count} JSON files. Used {text_count} files with non-empty 'raw_text'. Total text length: {len(all_text)} characters.")
    # Save to a temporary file for LineByLineTextDataset
    temp_path = "temp_gpt2_train.txt"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(all_text)
    dataset = LineByLineTextDataset(
        tokenizer=tokenizer,
        file_path=temp_path,
        block_size=block_size
    )
    return dataset

def main():
    model_name = "gpt2"
    data_dir = "structured_output"  # Use workspace root relative path
    output_dir = "finetuned_model"
    epochs = 3
    batch_size = 2

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    # Add pad token if missing
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        model.resize_token_embeddings(len(tokenizer))

    train_dataset = get_dataset(tokenizer, data_dir)
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm=False
    )

    training_args = TrainingArguments(
        output_dir=output_dir,
        overwrite_output_dir=True,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        save_steps=10,
        save_total_limit=2,
        prediction_loss_only=True,
        logging_steps=5,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=train_dataset,
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Model and tokenizer saved to {output_dir}")

if __name__ == "__main__":
    main()

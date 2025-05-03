import json
import yaml
import glob
import os
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
from datasets import Dataset

def load_configs():
    with open("model_training/config/base_model.yaml", 'r') as f:
        base_config = yaml.safe_load(f)
    with open("model_training/config/training_params.json", 'r') as f:
        training_params = json.load(f)
    return base_config, training_params

def main():
    base_config, training_params = load_configs()
    model_name = base_config["model_name"]
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Dynamically adjust path for Colab or local
    if os.path.exists("/content/Insolare-V1/structured_output"):
        data_dir = "/content/Insolare-V1/structured_output"
    else:
        data_dir = "/workspaces/Insolare-V1/structured_output"

    json_files = glob.glob(os.path.join(data_dir, '*.json'))
    print(f"🗂️ Found {len(json_files)} JSON files in {data_dir}")

    records = []
    for file in json_files:
        with open(file, 'r') as f:
            try:
                d = json.load(f)
                if d.get('normalized_text') and d.get('document_type'):
                    records.append({
                        'text': d['normalized_text'],
                        'label': d['document_type']
                    })
                else:
                    print(f"⚠️ Skipping {file}: Missing required fields")
            except Exception as e:
                print(f"❌ Error parsing {file}: {e}")

    if not records:
        raise ValueError("🚫 No valid records found in structured_output.")

    label_set = sorted(list(set(r['label'] for r in records)))
    label2id = {label: i for i, label in enumerate(label_set)}
    num_labels = len(label2id)
    for r in records:
        r['label'] = label2id[r['label']]

    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)
    dataset = Dataset.from_list(records)
    dataset = dataset.train_test_split(test_size=0.2, seed=42)

    def tokenize_fn(x):
        return tokenizer(x['text'], truncation=True, padding='max_length')

    tokenized_dataset = dataset.map(tokenize_fn, batched=True)

    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=training_params["epochs"],
        per_device_train_batch_size=training_params["batch_size"]
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"]
    )

    trainer.train()
    model.save_pretrained("./finetuned_model")
    print("✅ Fine-tuning complete. Model saved to ./finetuned_model")

if __name__ == '__main__':
    main()

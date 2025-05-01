import json
import yaml
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
import datasets

def load_configs():
    with open("configs/base_model.yml", 'r') as f:
        base_config = yaml.safe_load(f)
    with open("configs/training_params.json", 'r') as f:
        training_params = json.load(f)
    return base_config, training_params

def main():
    base_config, training_params = load_configs()
    model_name = base_config["model_name"]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

    # Load dataset (example using Hugging Face datasets)
    dataset = datasets.load_dataset("imdb")  # Replace with your labeled dataset
    tokenized_dataset = dataset.map(lambda x: tokenizer(x['text'], truncation=True, padding='max_length'), batched=True)

    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=training_params["epochs"],
        per_device_train_batch_size=training_params["batch_size"],
        evaluation_strategy="epoch"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"]
    )

    trainer.train()
    model.save_pretrained("./finetuned_model")

if __name__ == '__main__':
    main()
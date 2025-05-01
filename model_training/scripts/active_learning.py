import random

def select_uncertain_samples(predictions, threshold=0.6):
    # Assume predictions is a list of tuples (sample, confidence_score)
    uncertain = [sample for sample, score in predictions if score < threshold]
    return uncertain

def update_training_data(uncertain_samples, expert_labels):
    # Integrate expert labels into the training dataset (simplified example)
    updated_dataset = []
    for sample in uncertain_samples:
        label = expert_labels.get(sample, None)
        if label is not None:
            updated_dataset.append((sample, label))
    return updated_dataset

if __name__ == '__main__':
    # Example usage
    sample_predictions = [("Document A", 0.55), ("Document B", 0.8)]
    uncertain = select_uncertain_samples(sample_predictions)
    print("Uncertain samples:", uncertain)
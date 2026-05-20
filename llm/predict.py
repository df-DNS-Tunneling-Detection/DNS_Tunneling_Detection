"""Run inference on new DNS queries with the fine-tuned DistilBERT.

Usage:
    python predict.py "mail.google.com"
    python predict.py --queries queries.txt
    python predict.py --csv ../data/raw/sample.csv
"""

import argparse
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "models" / "distilbert"


def load_model(model_dir: str):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device)
    model.eval()
    return model, tokenizer, device


def predict_queries(queries: list[str], model, tokenizer, device) -> list[dict]:
    """Predict on a list of query strings. Returns list of dicts."""
    results = []
    batch_size = 64

    for i in range(0, len(queries), batch_size):
        batch = queries[i : i + batch_size]
        enc = tokenizer(batch, padding=True, truncation=True, max_length=128,
                        return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1)

        for q, prob in zip(batch, probs):
            pred = prob.argmax().item()
            results.append({
                "query": q,
                "prediction": "tunneling" if pred == 1 else "benign",
                "confidence": prob[pred].item(),
                "prob_benign": prob[0].item(),
                "prob_tunneling": prob[1].item(),
            })

    return results


def main():
    parser = argparse.ArgumentParser(description="Predict DNS tunneling with DistilBERT.")
    parser.add_argument("query", nargs="?", help="Single query string to classify.")
    parser.add_argument("--queries", help="File with one query per line.")
    parser.add_argument("--csv", help="CSV file with a 'query' column.")
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL))
    args = parser.parse_args()

    # Collect queries
    queries = []
    if args.query:
        queries.append(args.query)
    if args.queries:
        with open(args.queries) as f:
            queries.extend(line.strip() for line in f if line.strip())
    if args.csv:
        df = pd.read_csv(args.csv)
        queries.extend(df["query"].astype(str).tolist())

    if not queries:
        parser.print_help()
        return

    model, tokenizer, device = load_model(args.model_dir)
    results = predict_queries(queries, model, tokenizer, device)

    print(f"\n{'QUERY':<70} {'PRED':>10} {'CONF':>8} {'P_TUNNEL':>10}")
    print("-" * 102)
    for r in results:
        print(f"{r['query']:<70} {r['prediction']:>10} {r['confidence']:>8.4f} {r['prob_tunneling']:>10.4f}")

    n_tunnel = sum(1 for r in results if r["prediction"] == "tunneling")
    print(f"\nTotal: {len(results)} queries | {n_tunnel} tunneling | {len(results) - n_tunnel} benign")


if __name__ == "__main__":
    main()

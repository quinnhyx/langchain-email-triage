"""Evaluate a fixed quick subset or the full benchmark, with explicit cache reuse."""

import argparse
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from test_emails import test_emails


QUICK_IDS = (1, 3, 6, 7, 8, 11, 16, 18, 29, 30, 35, 39, 44)
PROJECT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_DIR / "results"
LABELS = {
    "category": ("job", "shopping", "newsletter", "personal", "other"),
    "action": ("reply", "read", "ignore"),
    "priority": ("high", "medium", "low"),
}


def select_cases(mode):
    """Reference the frozen dataset; quick mode has no separate labels."""
    if mode == "full":
        return list(test_emails)
    if mode != "quick":
        raise ValueError(f"Unknown evaluation mode: {mode}")
    by_id = {case["id"]: case for case in test_emails}
    missing = set(QUICK_IDS) - by_id.keys()
    if missing:
        raise ValueError(f"Quick IDs missing from dataset: {sorted(missing)}")
    return [by_id[case_id] for case_id in QUICK_IDS]


def build_cache_metadata(mode, cases):
    """Fingerprint inputs and production source without importing the classifier."""
    source = (PROJECT_DIR / "email_triage.py").read_bytes()
    # Read the default model name without importing/constructing an Ollama client.
    tree = ast.parse(source)
    triage_class = next(node for node in tree.body
                        if isinstance(node, ast.ClassDef) and node.name == "EmailTriage")
    constructor = next(node for node in triage_class.body
                       if isinstance(node, ast.FunctionDef) and node.name == "__init__")
    defaults = dict(zip(
        [arg.arg for arg in constructor.args.args][-len(constructor.args.defaults):],
        constructor.args.defaults,
    ))
    model_name = ast.literal_eval(defaults["model_name"])
    serialized_cases = json.dumps(cases, sort_keys=True, ensure_ascii=False)
    return {
        "cache_version": 1,
        "mode": mode,
        "model_name": model_name,
        "case_count": len(cases),
        "evaluated_ids": [case["id"] for case in cases],
        "inputs_sha256": hashlib.sha256(serialized_cases.encode("utf-8")).hexdigest(),
        "classifier_sha256": hashlib.sha256(source).hexdigest(),
    }


def run_inference(cases):
    """Only this function imports/constructs the production classifier."""
    from email_triage import EmailTriage

    triage = EmailTriage()
    predictions = []
    for case in cases:
        print(f'Analyzing email {case["id"]}: {case["subject"]}', flush=True)
        result = triage.analyze(subject=case["subject"], body=case["body"])
        row = {"id": case["id"], "subject": case["subject"]}
        for label in LABELS:
            row[f"expected_{label}"] = case[f"expected_{label}"]
            row[f"predicted_{label}"] = getattr(result, label)
        row.update(reason=result.reason, suggested_reply=result.suggested_reply)
        predictions.append(row)
    return predictions


def validate_predictions(predictions, cases):
    """Reject incomplete/malformed caches and mismatched benchmark labels."""
    if not isinstance(predictions, list) or len(predictions) != len(cases):
        raise ValueError("Prediction count does not match selected cases.")
    for row, case in zip(predictions, cases):
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            raise ValueError("Each prediction must have an integer ID.")
        if row["id"] != case["id"] or row.get("subject") != case["subject"]:
            raise ValueError("Prediction IDs/order/subjects do not match selected cases.")
        for label, allowed in LABELS.items():
            if row.get(f"expected_{label}") != case[f"expected_{label}"]:
                raise ValueError(f"Cached expected {label} differs for ID {case['id']}.")
            if row.get(f"predicted_{label}") not in allowed:
                raise ValueError(f"Invalid predicted {label} for ID {case['id']}.")


def save_predictions(path, metadata, predictions):
    """Replace a mode's cache only after all inference has completed."""
    payload = {
        "metadata": {**metadata, "created_at_utc": datetime.now(timezone.utc).isoformat()},
        "predictions": predictions,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    temporary_path.replace(path)


def load_predictions(path, metadata, cases):
    """Explicit cache reuse never falls back to inference."""
    if not path.is_file():
        raise ValueError(f"Cache not found: {path}. Run --{metadata['mode']} without --use-cache first.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"Invalid cache JSON: {path}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("metadata"), dict):
        raise ValueError("Cache must contain metadata and predictions.")
    cached_metadata = payload["metadata"]
    mismatches = [key for key, value in metadata.items() if cached_metadata.get(key) != value]
    if mismatches:
        raise ValueError(f"Cache is stale or incompatible ({', '.join(mismatches)}). "
                         f"Run --{metadata['mode']} without --use-cache to refresh it.")
    predictions = payload.get("predictions")
    validate_predictions(predictions, cases)
    return predictions


def compute_metrics(predictions):
    """Calculate all metrics from predictions alone; no model dependency."""
    if not predictions:
        raise ValueError("Cannot evaluate an empty prediction list.")
    df = pd.DataFrame(predictions)
    correct = pd.DataFrame({
        label: df[f"expected_{label}"] == df[f"predicted_{label}"] for label in LABELS
    })
    errors = {label: df[~correct[label]] for label in LABELS}
    matrices = {
        label: pd.crosstab(
            df[f"expected_{label}"], df[f"predicted_{label}"],
            rownames=["Expected"], colnames=["Predicted"],
        ) for label in LABELS
    }
    return {
        "total": len(df),
        "accuracy": {label: float(correct[label].mean()) for label in LABELS},
        "exact_match_accuracy": float(correct.all(axis=1).mean()),
        "confusion_matrices": matrices,
        "errors": errors,
        "action_error_patterns": errors["action"][["expected_action", "predicted_action"]].value_counts(),
        "critical_errors": df[(df["expected_action"] == "reply") & (df["predicted_action"] == "ignore")],
    }


def print_report(metrics):
    """Print the original report sections plus exact-match accuracy."""
    print(f"\nACCURACY ({metrics['total']} emails)")
    for label, accuracy in metrics["accuracy"].items():
        print(f"{label.title()} Accuracy: {accuracy:.2%}")
    print(f"Exact Match Accuracy: {metrics['exact_match_accuracy']:.2%}")
    for label in LABELS:
        print(f"\n{label.upper()} CONFUSION MATRIX")
        print(metrics["confusion_matrices"][label])
    for label in LABELS:
        print(f"\n{label.upper()} ERRORS")
        errors = metrics["errors"][label]
        columns = ["id", "subject", f"expected_{label}", f"predicted_{label}"]
        print("None" if errors.empty else errors[columns].to_string(index=False))
    print("\nACTION ERROR PATTERNS")
    patterns = metrics["action_error_patterns"]
    print("None" if patterns.empty else patterns)
    print("\nCRITICAL ERRORS (reply -> ignore)")
    critical = metrics["critical_errors"]
    columns = ["id", "subject", "expected_action", "predicted_action"]
    print("None" if critical.empty else critical[columns].to_string(index=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--quick", dest="mode", action="store_const", const="quick",
                       help="Evaluate the fixed 13-case regression subset.")
    modes.add_argument("--full", dest="mode", action="store_const", const="full",
                       help="Evaluate all 45 benchmark cases (default).")
    parser.set_defaults(mode="full")
    parser.add_argument("--use-cache", action="store_true",
                        help="Report cached predictions only; never call Ollama.")
    args = parser.parse_args(argv)
    try:
        cases = select_cases(args.mode)
        metadata = build_cache_metadata(args.mode, cases)
        path = RESULTS_DIR / f"{args.mode}_predictions.json"
        source = "cache" if args.use_cache else "inference"
        print(f"Mode: {args.mode} | Source: {source} | Cases: {len(cases)}")
        print(f"IDs: {metadata['evaluated_ids']}")
        if args.use_cache:
            predictions = load_predictions(path, metadata, cases)
        else:
            predictions = run_inference(cases)
            validate_predictions(predictions, cases)
            save_predictions(path, metadata, predictions)
            print(f"Saved predictions: {path}")
        print_report(compute_metrics(predictions))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Evaluation failed: {exc}\n")


if __name__ == "__main__":
    main()

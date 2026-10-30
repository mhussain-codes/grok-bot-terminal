import json
from typing import Dict

def generate_calibration_report(jsonl_path: str) -> Dict:
    records = []
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except FileNotFoundError:
        return {"error": "No calibration logs found."}

    pairs = []
    for r in records:
        if r.get("realized_outcome") is not None:
            answers = r.get("answers", {})
            for _, val in answers.items():
                if "prob" in val:
                    pairs.append((val["prob"], r["realized_outcome"]))
                elif "confidence" in val:
                    pairs.append((val["confidence"], r["realized_outcome"]))

    if not pairs:
        return {"status": "insufficient_data", "total_records": len(records)}

    brier_score = sum((p - a) ** 2 for p, a in pairs) / len(pairs)

    buckets = {i: {"count": 0, "sum_p": 0.0, "actual_wins": 0} for i in range(10)}
    for p, a in pairs:
        idx = min(int(p * 10), 9)
        buckets[idx]["count"] += 1
        buckets[idx]["sum_p"] += p
        buckets[idx]["actual_wins"] += a

    lines = [
        "=== CALIBRATION REPORT ===",
        f"Total Samples: {len(pairs)} | Brier Score: {brier_score:.4f} (lower is better, 0.0=perfect)\n",
        "Bucket    | Pred Mean | Actual Rate | Count | Reliability Visual",
        "----------|-----------|-------------|-------|--------------------"
    ]
    for idx, b in buckets.items():
        cnt = b["count"]
        if cnt > 0:
            mean_p = b["sum_p"] / cnt
            actual_rate = b["actual_wins"] / cnt
            bar = "#" * int(actual_rate * 20)
            lines.append(f"{idx/10:.1f}-{(idx+1)/10:.1f}  |   {mean_p:.3f}   |    {actual_rate:.3f}    | {cnt:5d} | {bar}")

    return {"brier_score": brier_score, "chart": "\n".join(lines), "records": len(pairs)}

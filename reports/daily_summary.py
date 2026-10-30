import json

def generate_daily_summary(log_path: str, broker_history: list) -> str:
    total_decisions = 0
    risk_vetoes = {}
    actions_taken = {}

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                total_decisions += 1
                veto = r.get("risk_veto")
                if veto:
                    risk_vetoes[veto] = risk_vetoes.get(veto, 0) + 1
                act = r.get("policy_action", "HOLD")
                actions_taken[act] = actions_taken.get(act, 0) + 1
    except FileNotFoundError:
        pass

    total_trades = len(broker_history)
    total_fees = sum(t.get("fee_usd", 0.0) for t in broker_history)
    net_pnl = sum(t.get("net_pnl", 0.0) for t in broker_history)

    summary = [
        "=========================================",
        "        24/7 AI DESK DAILY SUMMARY       ",
        "=========================================",
        f"Decisions Evaluated: {total_decisions}",
        f"Trades Executed:     {total_trades}",
        f"Net PnL After Fees:  ${net_pnl:.2f}",
        f"Total Fees Incurred: ${total_fees:.2f}",
        "\n[Actions Taken by Policy]:"
    ]
    for act, cnt in actions_taken.items():
        summary.append(f"  - {act}: {cnt}")

    summary.append("\n[Risk Vetoes Fired (Hard Stops)]:")
    if risk_vetoes:
        for veto, count in risk_vetoes.items():
            summary.append(f"  - {veto}: {count}")
    else:
        summary.append("  - None (All cleared)")

    return "\n".join(summary)

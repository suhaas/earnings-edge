"""Check eval regression against baseline."""

import json
import sys


def check_regression(report_file: str) -> int:
    """Exit with code 1 if regression detected."""
    with open(report_file) as f:
        report = json.load(f)
    
    if report.get("delta", 0) < 0:
        print(f"❌ Eval regression detected: {report['delta']:.3f}")
        return 1
    
    print(f"✅ Eval passed: {report['current_score']:.3f}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_eval_regression.py <report_file>")
        sys.exit(1)
    sys.exit(check_regression(sys.argv[1]))

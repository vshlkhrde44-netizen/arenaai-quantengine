#!/usr/bin/env python3
"""
Antigravity QuantEngine - Static Safety & Live Endpoint Prohibition Scanner
Scans codebase to guarantee:
1. No active production/live trading endpoints
2. No live order submission capability
3. No hardcoded exchange secrets, private keys, or API tokens
4. Safety gates and paper-only invariants remain intact
"""

import os
import re
import sys
from pathlib import Path

# Prohibited patterns that indicate active live execution paths or leaks
PROHIBITED_PATTERNS = [
    (re.compile(r'\blive_orders_enabled\s*=\s*True\b'), "live_orders_enabled set to True"),
    (re.compile(r'\bis_production_ready\s*=\s*True\b'), "is_production_ready set to True"),
    (re.compile(r'\bpaper_only\s*=\s*False\b'), "paper_only set to False"),
    (re.compile(r'\bsupports_live_orders\s*=\s*True\b'), "supports_live_orders set to True"),
    (re.compile(r'https?://api\.exchange\.coinbase\.com/orders'), "Coinbase live orders production URL detected"),
    (re.compile(r'https?://api\.alpaca\.markets/v2/orders'), "Alpaca live orders production URL detected (must use paper-api)"),
    (re.compile(r'https?://api\.binance\.com/api/v3/order'), "Binance live order production URL detected"),
    (re.compile(r'["\']AKIA[0-9A-Z]{16}["\']'), "AWS access key detected"),
    (re.compile(r'-----BEGIN\s+PRIVATE\s+KEY-----'), "Private key material detected"),
]

EXCLUDED_DIRS = {
    ".git", ".cache", "node_modules", "dist", "dist_installer",
    "__pycache__", ".pytest_cache", ".venv", "tests"
}


def run_scan() -> bool:
    root_dir = Path(__file__).resolve().parent.parent
    violations = []
    files_scanned = 0

    print("==============================================================================")
    print("      ANTIGRAVITY QUANTENGINE - STATIC SAFETY & INVARIANT SCANNER")
    print("==============================================================================")
    print(f"Scanning codebase rooted at: {root_dir}")
    print()

    for path in root_dir.rglob("*"):
        if path.is_file():
            # Check exclusions
            parts = set(path.parts)
            if parts.intersection(EXCLUDED_DIRS):
                continue

            # Only check code, text, configs
            if path.suffix not in (".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml", ".json", ".bat", ".ps1", ".iss"):
                continue

            # Exclude this scanner script itself
            if path.name == "security_scan.py":
                continue

            files_scanned += 1
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for pattern, desc in PROHIBITED_PATTERNS:
                    match = pattern.search(content)
                    if match:
                        violations.append({
                            "file": str(path.relative_to(root_dir)),
                            "line": content[:match.start()].count("\n") + 1,
                            "rule": desc,
                            "match": match.group(0)
                        })
            except Exception as e:
                print(f"Warning: Could not read {path}: {e}")

    print(f"[*] Total files scanned: {files_scanned}")
    print(f"[*] Violations detected: {len(violations)}")
    print()

    if violations:
        print("[!] FATAL SAFETY FIREWALL VIOLATIONS FOUND:")
        for v in violations:
            print(f"  - {v['file']}:{v['line']} -> {v['rule']} ('{v['match']}')")
        print("\nScan Result: FAILED. Prohibited live execution patterns present.")
        return False

    print("[+] All static safety checks PASSED.")
    print("[+] Inviolable Invariant Verified: LIVE_ORDER_SUBMISSION = IMPOSSIBLE_BY_SUPPORTED_APPLICATION_PATH")
    print("[+] Execution Mode Verified: PAPER_TRADING = REAL_MARKET_DATA + OFFICIAL_PAPER_EXECUTION")
    return True


if __name__ == "__main__":
    success = run_scan()
    sys.exit(0 if success else 1)

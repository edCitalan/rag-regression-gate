"""Offline CI entry point: tests, candidate gate, and dashboard artifact."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, default=ROOT/'data/candidate_predictions.jsonl')
    args = parser.parse_args()
    tests = subprocess.run([sys.executable,'-S','-m','unittest','discover','-s',str(ROOT),'-v'])
    gate = subprocess.run([sys.executable,'-S',str(ROOT/'ci_gate.py'),'--predictions',str(args.predictions),
                           '--output',str(ROOT/'reports/candidate.json')])
    dashboard = subprocess.run([sys.executable,'-S',str(ROOT/'build_dashboard.py'),'--predictions',str(args.predictions)]) if gate.returncode in (0,1) else None
    return gate.returncode or tests.returncode or (dashboard.returncode if dashboard else 0)

if __name__ == '__main__':
    sys.exit(main())

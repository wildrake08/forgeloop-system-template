"""Minimal replaceable application starter."""
import argparse
import json

def calculate(a, b):
    return a + b

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--a", type=int, default=2)
    parser.add_argument("--b", type=int, default=3)
    args = parser.parse_args()
    healthy = calculate(2, 3) == 5
    print(json.dumps({"healthy": healthy, "result": calculate(args.a, args.b)}))
    return 0 if healthy else 1

if __name__ == "__main__":
    raise SystemExit(main())

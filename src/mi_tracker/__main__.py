import argparse
import json
from .core import collect

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/tracker.sqlite")
    parser.add_argument("--out", default="docs/data")
    parser.add_argument("--per-page", type=int, default=10)
    parser.add_argument("--max-pages", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(collect(args.db, args.out, args.per_page, args.max_pages), indent=2))

if __name__ == "__main__":
    main()

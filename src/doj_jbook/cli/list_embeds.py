from __future__ import annotations

import argparse
from doj_jbook.etl import list_embedded_files


def main():
    ap = argparse.ArgumentParser(description="List embedded files in a PDF")
    ap.add_argument("--pdf", required=True)
    args = ap.parse_args()
    files = list_embedded_files(args.pdf)
    if not files:
        print("No embedded files found.")
        return
    for f in files:
        print(f)


if __name__ == "__main__":
    main()


"""
One-time repair for a mojibake pattern baked into several files by
whatever process originally scaffolded this project: a real em dash
(U+2014, UTF-8 bytes E2 80 94) got its raw bytes misread as
Windows-1252/cp1252 and re-encoded, producing three separate wrong
characters (displays as "â€"") wherever an em dash should be. Confirmed
via scripts/audit output on 2026-08-20 that this is baked into the
SOURCE FILES themselves (not a DB/connection charset issue - see
app/database.py's charset= fix, which is good practice regardless but
was NOT the actual cause here).

Walks the repo (excluding venv/.git/__pycache__), replaces every
occurrence of the corrupted byte sequence with a real em dash, and
reports what it touched. Safe to re-run - it's a no-op once clean.

    python scripts/fix_mojibake.py
"""
import os

CORRUPTED = b"\xc3\xa2\xe2\x82\xac\xe2\x80\x9d"  # "â€"" - misread em dash
FIXED = "—".encode("utf-8")  # real em dash, U+2014

SKIP_DIRS = {"venv", ".git", "__pycache__", "models_store", "data", "reports"}
EXTENSIONS = (".py", ".md", ".txt")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    touched = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(EXTENSIONS):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, "rb") as f:
                data = f.read()
            count = data.count(CORRUPTED)
            if count:
                data = data.replace(CORRUPTED, FIXED)
                with open(path, "wb") as f:
                    f.write(data)
                rel = os.path.relpath(path, root)
                touched.append((rel, count))
                print(f"Fixed {count} occurrence(s) in {rel}")

    if not touched:
        print("No corrupted em dashes found - already clean.")
    else:
        print(f"\nTotal: {sum(c for _, c in touched)} occurrence(s) across {len(touched)} file(s).")


if __name__ == "__main__":
    main()

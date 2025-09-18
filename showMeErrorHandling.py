import csv
import os
import ast
import inspect

INPUT_CSV = "returnValAnalysis.csv"
DEFAULT_CONTEXT = 10

import re

def extract_function_from_file(filepath, line_number, context=10):
    """
    Returns 10 lines before and after the given line number from the file.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        if line_number < 1 or line_number > len(lines):
            return f"!! Line number {line_number} is out of range."

        start = max(0, line_number - context - 1)  # 0-based indexing
        end = min(len(lines), line_number + context)

        snippet = lines[start:end]
        return "".join(f"{i + 1:5d}: {line}" for i, line in enumerate(snippet, start=start))

    except Exception as e:
        return f"!! Could not read {filepath}: {e}"

def main():
    input_filename = INPUT_CSV
    output_csv = input("Enter filename to save reviewed entries (e.g., reviewed.csv): ").strip()

    # Load existing reviews (if file exists)
    reviewed_entries = set()
    if os.path.isfile(output_csv):
        with open(output_csv, newline='', encoding="utf-8") as existing_file:
            reader = csv.DictReader(existing_file)
            for row in reader:
                reviewed_entries.add((row["file path"].strip(), row["line number"].strip()))

    # Open output in append mode
    with open(output_csv, "a", newline='', encoding="utf-8") as outfile, \
         open(input_filename, newline='', encoding="utf-8") as infile:

        reader = csv.DictReader(infile)

        # If the file was just created, write headers
        if os.path.getsize(output_csv) == 0:
            writer = csv.writer(outfile)
            writer.writerow(["file path", "line number", "label"])
        else:
            writer = csv.writer(outfile)

        for row in reader:
            if not row or all(v is None or str(v).strip() == "" for v in row.values()):
                continue  # Skip empty or completely blank row
            if row.get(" error handling ", "") == None:
                continue
            if row.get(" error handling ", "").strip() != "Needs Manual Analysis":
                continue

            filepath = row[" file name"].strip()
            line_number_str = row[" line number"].strip()

            # Skip if already reviewed
            if (filepath, line_number_str) in reviewed_entries:
                continue

            try:
                line_number = int(line_number_str)
            except ValueError:
                continue  # skip bad row

            print("=" * 80)
            print(f"File: {filepath}")
            print(f"Function: {row.get('function name')}")
            print(f"Line number: {line_number}\n")

            print(extract_function_from_file(filepath, line_number))

            while True:
                label = input("Is this error handling? (y/n/?/s = skip): ").strip().lower()
                if label in {"y", "n", "?", "s"}:
                    break
                print("Please type: y / n / ? / s")

            if label == "s":
                continue  # skip writing this entry

            full_label = {"y": "yes", "n": "no", "?": "not sure"}[label]
            writer.writerow([filepath, line_number_str, full_label])

    print(f"\nFinished! Saved reviewed entries to {output_csv}")


if __name__ == "__main__":
    main()

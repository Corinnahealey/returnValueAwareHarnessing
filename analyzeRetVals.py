import argparse
import sys
import os 
import multiprocessing
import sys
import process_mx
import engine
import extractRetvals as extract
import os
import collections


def write_to_csv(line, file_name):
    with open(file_name, 'a') as f:
        f.write(line + '\n')


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze a Library DB file and output return value analysis to CSV."
    )

    parser.add_argument(
        "-p", "--path",
        type=str,
        help="Path to the Library DB file"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output CSV file (default: returnValAnalysis.csv)",
        default="returnValAnalysis.csv"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

   
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if not args.path:
        print("Error: -p / --path is required.\n")
        parser.print_help()
        sys.exit(1)

    return args





def main():
    args = parse_args()

    if args.verbose:
        print(f"[VERBOSE] DB Path: {args.path}")
        print(f"[VERBOSE] Output file: {args.output}")

    # Example usage:
    sample_line = "Int Value, Depth, Token Str, In Loop, In Conditional, Is Var, Is Callexpr, Is Enum, Error Func Called, Callexprs in Block, Is Last, Is Error Handling *manual analysis* "
    if not os.path.isfile(args.output) or os.path.getsize(args.output) == 0:
        write_to_csv(sample_line, args.output)
    
    idx = process_mx.Index_Target_Header(args.path, ["document.h", "parser.h", "unicode.h"], False)
    function_list, macros, enums, fps, aliases = idx.extractArtifacts()
    compatibility = engine.CheckCompatibility(idx.index, aliases, enums, "", False, False)
    functions = engine.APIfunctions()
    compatibility.process_functions(functions, function_list, "")

    funcs = functions.getAllFunctions()
    extracted = extract.ExtractLib(idx.index, args.path)
    separator = "\n"
 
    for fun in extracted: 
        write_to_csv(separator.join(str(item) for item in extracted[fun].retlist ), args.output)
    if args.verbose:
        print(f"[VERBOSE] Wrote header to {args.output}")


if __name__ == "__main__":
    main()

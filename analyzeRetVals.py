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
import csv
import multiplier as mx
import getLibs
import re
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
        help="Path to the object to analyze"
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


def check_union_range(value, range_expr):
    import re
    val = int(value)
    ranges = re.findall(r'\[(\d+),\s*(\d+)\]', range_expr)
    for start, end in ranges:
        if int(start) <= val <= int(end):
            return True
    return False




def main():
    args = parse_args()

    if args.verbose:
        print(f"[VERBOSE] DB Path: {args.path}")
        print(f"[VERBOSE] Output file: {args.output}")
    obj = extract.Retval(1, 1, "")
    
    # Example usage:
    sample_line = "Int Value, Depth, Token Str, In Loop, In Conditional, Is Var, Is Callexpr, Is Enum, Error Func Called, Callexprs in Block, Is Last, Is Error Handling *manual analysis* "

    libs = getLibs.load_tasks_from_file(args.path)
    lib1 = libs[0]

    if not os.path.isfile(args.output) or os.path.getsize(args.output) == 0:
        write_to_csv( obj.get_formatted_keys() + " , Is Error Handling (Manual Inspection) , ", args.output)
    idx = process_mx.Index_Target_Header(lib1["db_path"], lib1["headers"], False)
    function_list, macros, enums, fps, aliases = idx.extractArtifacts()
    compatibility = engine.CheckCompatibility(idx.index, aliases, enums, "", False, False)
    functions = engine.APIfunctions()
    compatibility.process_functions(functions, function_list, "")

    funcs = functions.getAllFunctions()

    extracted = extract.ExtractLib(idx.index, lib1["db_path"], lib1["functions"])
    separator = "\n"
    #print(dir(mx.ast.ReturnStmt))
    for fun in extracted:
    # Write return list to CSV
        for func in lib1["functions"]:
            name = func["name"]
            condition = func["expected"]
            #If we have information about what the return values SHOULD be 
            if fun.strip() != name.strip():
                continue
                
            expr_op, expr_val = condition if isinstance(condition, tuple) else (condition, None)

            match = None  # Default

            for ret in extracted[fun].retlist:
                if ret.intValue is not None:
                    try:
                        intval = int(ret.intValue)
                        expr_val_int = int(expr_val) if expr_val is not None else None

                        if expr_op == "!=" and expr_val is not None:
                            match = intval != expr_val_int
                        elif expr_op == "==" and expr_val is not None:
                            match = intval == expr_val_int
                        elif expr_op == ">" and expr_val is not None:
                            match = intval > expr_val_int
                        elif expr_op == "<" and expr_val is not None:
                            match = intval < expr_val_int
                        elif expr_op == ">=" and expr_val is not None:
                            match = intval >= expr_val_int
                        elif expr_op == "<=" and expr_val is not None:
                            match = intval <= expr_val_int
                        elif expr_op == "!" and expr_val is None:
                            match = not bool(intval)
                        elif expr_op.startswith("[") and "U" in expr_op:
                            match = check_union_range(intval, expr_op)
                    except ValueError:
                        # Handle the case where expr_val isn't a valid int
                        match = None

                elif ret.token_str is not None and str(ret.token_str).strip().lstrip().strip('"').strip("'").lstrip() == "":
                    tokenVal = str(ret.token_str).strip().lstrip().strip('"').strip("'").lstrip()
                    if expr_op == "!=" and expr_val is not None:
                        match = tokenVal != expr_val
                    elif expr_op == "==" and expr_val is not None:
                        match = tokenVal == expr_val
                    elif expr_op == "!" and expr_val is None:
                        match = not bool(tokenVal)
                if match is not None:
                    ret.error_handling = str(match)
        
        for ret in extracted[fun].retlist:
            if not ret.is_callexpr and ( str(ret.libName) in str(ret.fileName)):
                line = str(ret)  # Or build a more specific string if needed
                write_to_csv(line, args.output)


       
       
                    

    if args.verbose:
        print(f"[VERBOSE] Wrote header to {args.output}")


if __name__ == "__main__":
    main()


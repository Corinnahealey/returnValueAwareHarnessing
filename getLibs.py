import ast
from typing import Any, List, Dict, Optional


def load_tasks_from_file(filename: str) -> List[Dict[str, Any]]:
    """
    Reads a file with 'tasks = [...]' definition and returns a list of dictionaries:
    [
        {
            "db_path": str,
            "headers": [str, ...],
            "functions": [
                {"name": str, "expected": Any, "extra": Optional[Any]},
                ...
            ]
        }
    ]
    """
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    # Safely parse using AST
    parsed = ast.parse(content, mode="exec")

    tasks_value = None
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "tasks":
                    tasks_value = ast.literal_eval(node.value)

    if tasks_value is None:
        raise ValueError("No 'tasks' variable found in file.")

    results: List[Dict[str, Any]] = []
    for db_path, headers, funcs in tasks_value:
        func_list = []
        for f in funcs:
            if len(f) == 2:
                name, expected = f
                extra = None
            elif len(f) == 3:
                name, expected, extra = f
            else:
                raise ValueError(f"Unexpected function tuple: {f}")
            func_list.append({
                "name": name,
                "expected": expected,
            })

        results.append({
            "db_path": db_path,
            "headers": headers,
            "functions": func_list
        })

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python my_parser.py <tasks_file.py>")
        sys.exit(1)

    path = sys.argv[1]
    tasks = load_tasks_from_file(path)
    from pprint import pprint
    pprint(tasks)

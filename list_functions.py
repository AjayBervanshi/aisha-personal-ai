import ast
import os
import glob

def get_functions_from_file(filepath):
    functions = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return functions

all_files = glob.glob('src/**/*.py', recursive=True)
all_files.extend(glob.glob('scripts/**/*.py', recursive=True))

function_map = {}
total_funcs = 0

for filepath in all_files:
    if '__pycache__' in filepath:
        continue
    funcs = get_functions_from_file(filepath)
    if funcs:
        function_map[filepath] = funcs
        total_funcs += len(funcs)

with open('FUNCTION_ANALYSIS.md', 'w', encoding='utf-8') as out:
    out.write("# Aisha Codebase Function Analysis\n\n")
    out.write(f"**Total Functions Found:** {total_funcs}\n\n")
    for filepath, funcs in sorted(function_map.items()):
        out.write(f"## {filepath}\n")
        for func in funcs:
            out.write(f"- [ ] `{func}`\n")
        out.write("\n")

print(f"Mapped {total_funcs} functions across {len(function_map)} files. Saved to FUNCTION_ANALYSIS.md")

import subprocess
from crewai.tools import tool

@tool("Run Python Tests")
def run_python_tests(test_file_path: str) -> str:
    """Runs a specific Python test file and returns the output. Use this to verify code fixes. Provide path like tests/test_weather.py"""
    try:
        result = subprocess.run(
            ["python", "-m", "unittest", test_file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Return both stdout and stderr since unittest outputs to stderr
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            return f"Tests PASSED:\n{output}"
        else:
            return f"Tests FAILED:\n{output}"
    except subprocess.TimeoutExpired:
        return "Error: Test execution timed out after 30 seconds."
    except Exception as e:
        return f"Error running tests: {e}"

@tool("Check Syntax")
def check_python_syntax(file_path: str) -> str:
    """Checks the syntax of a Python file without executing it. Always run this before running tests."""
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", file_path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return f"Syntax is valid for {file_path}"
        return f"Syntax Error in {file_path}:\n{result.stderr}"
    except Exception as e:
        return f"Error checking syntax: {e}"

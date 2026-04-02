"""
Jules Tool integration for Aisha.
This allows Aisha to invoke Jules on demand.
"""
from src.core.jules_subagent import jules

def run_jules_diagnostic():
    """
    Run the Google Jules sub-agent to scan the codebase for bugs and optimizations.
    Returns a string summary of the findings.
    """
    try:
        report = jules.run_full_scan()
        num_files_with_issues = len(report["findings"])
        return f"Jules scan complete. Found issues in {num_files_with_issues} files. A detailed JSON report has been generated in the aisha_patches directory."
    except Exception as e:
        return f"Error running Jules: {e}"

# If you have a skill_registry, you would register it like this:
# skill_registry.register("run_jules_diagnostic", run_jules_diagnostic)

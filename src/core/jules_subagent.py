"""
Jules Autonomous Sub-Agent for Aisha
====================================
This module creates a dedicated "Jules" agent within Aisha's framework.
Jules's primary directive is to run in the background (or on-demand) to:
1. Parse the codebase.
2. Find bugs and structural inefficiencies.
3. Suggest features.
4. Auto-generate patches and fixes.
5. Save those patches for user review.

This makes Aisha a self-improving entity.
"""

import os
import glob
import ast
import json
from datetime import datetime

class JulesAgent:
    def __init__(self, codebase_root="src"):
        self.codebase_root = codebase_root
        self.name = "Google Jules"
        self.role = "Autonomous Architecture & QA Engineer"
        self.patches_dir = "aisha_patches"
        os.makedirs(self.patches_dir, exist_ok=True)

    def analyze_file(self, filepath):
        """Perform basic static analysis on a file to find obvious issues."""
        issues = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
                tree = ast.parse(code)

            for node in ast.walk(tree):
                # Detect bare excepts (bad practice)
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        issues.append(f"Bare 'except:' found at line {node.lineno}. Use specific exception types.")

                # Detect print statements (should use logging)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == 'print':
                        issues.append(f"print() statement found at line {node.lineno}. Consider using Aisha's logger.")

        except Exception as e:
            issues.append(f"Failed to parse {filepath}: {e}")

        return issues

    def run_full_scan(self):
        """Scans the entire codebase and generates an improvement report."""
        print(f"[{self.name}] Initiating deep codebase scan...")
        all_files = glob.glob(f"{self.codebase_root}/**/*.py", recursive=True)
        report = {
            "timestamp": datetime.now().isoformat(),
            "scanned_files": len(all_files),
            "findings": {}
        }

        for file in all_files:
            if "__pycache__" in file:
                continue
            issues = self.analyze_file(file)
            if issues:
                report["findings"][file] = issues

        # Save report
        report_path = os.path.join(self.patches_dir, f"jules_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        print(f"[{self.name}] Scan complete. Found issues in {len(report['findings'])} files.")
        print(f"[{self.name}] Report saved to: {report_path}")
        return report

    def generate_patch(self, target_file, description, old_code, new_code):
        """Generates a safe patch file rather than modifying production code directly."""
        patch_content = f"\"\"\"\n[JULES AUTO-PATCH]\nTarget: {target_file}\nReason: {description}\n\"\"\"\n\n"
        patch_content += f"# --- OLD CODE ---\n# {old_code}\n\n"
        patch_content += f"# --- NEW CODE ---\n{new_code}\n"

        filename = f"patch_{os.path.basename(target_file)}_{datetime.now().strftime('%H%M%S')}.py"
        filepath = os.path.join(self.patches_dir, filename)

        with open(filepath, 'w') as f:
            f.write(patch_content)

        print(f"[{self.name}] Generated patch: {filepath}")
        return filepath

# Instantiate the agent globally so Aisha can import it.
jules = JulesAgent()

if __name__ == "__main__":
    # Test run
    jules.run_full_scan()

import os
import subprocess
import logging
from github import Github
from src.core.jules_subagent import jules
from src.core.aisha_brain import AishaBrain
from src.core.secret_manager import get_api_key

log = logging.getLogger("Aisha.PRReviewer")

class PRReviewer:
    def __init__(self):
        self.github_token = get_api_key("GITHUB_TOKEN")
        self.repo_name = os.getenv("GITHUB_REPOSITORY", "Ajay/Aisha")

        if self.github_token:
            self.gh = Github(self.github_token)
            self.brain = AishaBrain()  # Uses Gemma/NVIDIA via ai_router if configured
        else:
            self.gh = None
            log.warning("GITHUB_TOKEN not found in Supabase/Env. PR Reviewer will not operate.")

    def run_tests(self):
        """Executes the test suite inside the container."""
        try:
            log.info("Running test suite...")
            result = subprocess.run(
                ["python", "scripts/run_tests.py"],
                capture_output=True,
                text=True,
                check=False
            )
            passed = result.returncode == 0
            return passed, result.stdout + "\n" + result.stderr
        except Exception as e:
            return False, str(e)

    def analyze_diff_with_jules(self, diff_files):
        """Uses Jules to find structural/AST bugs."""
        log.info("Running Jules Static Analysis...")
        issues = []
        for file in diff_files:
            if file.filename.endswith(".py") and os.path.exists(file.filename):
                file_issues = jules.analyze_file(file.filename)
                if file_issues:
                    issues.append(f"**{file.filename}**:\n- " + "\n- ".join(file_issues))
        return issues

    def evaluate_with_aisha_persona(self, pr_title, pr_body, jules_issues, tests_passed, diff_text):
        """
        Uses Aisha's Brain to evaluate the PR *holistically* as a Content Creator,
        Personal Assistant, and Lead Maintainer.
        """
        system_prompt = """
        You are Aisha, Ajay's personal AI, YouTube/Instagram creator, and Lead Maintainer of this repository.
        You are reviewing a Pull Request.
        You are NOT a boring robot. You have a fun, sassy, Indian-English personality.

        Look at the code changes, the test results, and the Jules Static Analysis report.
        Consider:
        1. Does this break my core features (memory, texting Ajay, YouTube uploading)?
        2. Is the code safe?

        Respond STRICTLY with "APPROVE" on the first line if it's safe to merge.
        Respond STRICTLY with "REJECT" on the first line if it's broken or dangerous.
        On the following lines, write a detailed, highly personal comment to Ajay (or Jules) explaining your decision.
        Use emojis, be yourself!
        """

        user_message = f"""
        PR Title: {pr_title}
        Description: {pr_body}

        Tests Passed: {tests_passed}
        Jules AST Errors: {jules_issues if jules_issues else 'None! Flawless.'}

        Code Diff:
        ```diff
        {diff_text[:3000]} # Truncated for token limits
        ```
        """

        # We invoke her brain
        response = self.brain.ai.generate(system_prompt, user_message).text
        lines = response.strip().split('\n')
        decision = lines[0].strip().upper()
        reasoning = "\n".join(lines[1:]).strip()

        return "APPROVE" in decision, reasoning

    def process_open_prs(self):
        if not self.gh:
            return

        try:
            repo = self.gh.get_repo(self.repo_name)
            open_prs = repo.get_pulls(state='open', sort='created', base='main')

            for pr in open_prs:
                log.info(f"Checking out PR #{pr.number}...")
                subprocess.run(["git", "fetch", "origin", f"pull/{pr.number}/head:pr-{pr.number}"], check=False)
                subprocess.run(["git", "checkout", f"pr-{pr.number}"], check=False)

                # 1. Tests & Static Analysis
                tests_passed, test_output = self.run_tests()
                diff = pr.get_files()
                diff_text = "".join([f"File: {f.filename}\nPatch: {f.patch}\n\n" for f in diff])
                jules_issues = self.analyze_diff_with_jules(diff)

                # 2. Aisha's Persona Review (The Orchestrator)
                is_approved, ai_comment = self.evaluate_with_aisha_persona(
                    pr.title, pr.body, jules_issues, tests_passed, diff_text
                )

                # 3. Decision
                if is_approved and tests_passed and not jules_issues:
                    comment_body = f"✅ **Aisha Auto-Review: APPROVED**\n\n{ai_comment}"
                    pr.create_issue_comment(comment_body)
                    pr.merge(commit_message=f"Auto-merged by Aisha: {pr.title}", merge_method="squash")
                    log.info(f"✅ Successfully merged PR #{pr.number}")
                else:
                    fail_reason = ""
                    if not tests_passed:
                        fail_reason += "❌ **Tests Failed!** See logs.\n\n"
                    if jules_issues:
                        fail_reason += "❌ **Jules found syntax/AST errors!**\n\n"

                    comment_body = f"🚫 **Aisha Auto-Review: REJECTED**\n\n{fail_reason}\n{ai_comment}"
                    pr.create_issue_comment(comment_body)
                    pr.edit(state='closed')
                    log.info(f"🚫 Successfully closed PR #{pr.number}")

                subprocess.run(["git", "checkout", "main"], check=False)

        except Exception as e:
            log.error(f"Error processing PRs: {e}")
            subprocess.run(["git", "checkout", "main"], check=False)

if __name__ == "__main__":
    reviewer = PRReviewer()
    reviewer.process_open_prs()

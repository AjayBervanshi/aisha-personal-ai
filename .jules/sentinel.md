## 2024-05-24 - Remove Hardcoded Defaults
**Vulnerability:** Found hardcoded fallback passwords and default email addresses in configuration dictionaries in `src/skills/auto_error_logger.py` and `src/skills/auto_error_notifier.py`.
**Learning:** Defaulting to placeholder strings like `'password'` or dummy webhook URLs can lead to accidental data leakage or false positives in security scanners, as applications might attempt real operations with these dummy credentials.
**Prevention:** Always retrieve secrets and configurations securely using `os.environ.get()` and handle `None` gracefully instead of providing hardcoded dummy values.
## 2026-04-02 - Fix Command Injection in Self-Audit

**Vulnerability:**
Using `subprocess.Popen` with string injection (an f-string containing paths passed to `python -c`) could allow unexpected execution if path variables contained shell metacharacters or single quotes, enabling potential code execution outside the intended module context.

**Learning:**
Direct code evaluation via `python -c` in subprocesses is inherently risky when combined with dynamic strings or string formatting, as standard quoting is often insufficient to prevent injection.

**Prevention:**
Always invoke Python modules directly using the `-m` flag (e.g., `python -m <module_name>`) and ensure the target module has a proper `if __name__ == '__main__':` block to handle standalone execution safely.

# /analyze-codebase — Full Structural Analysis

Run a complete analysis of the Aisha codebase for quality, security, and architecture.

## Steps
1. Map project structure: `find src/ -name "*.py" | head -50`
2. Count lines per module: `wc -l src/**/*.py`
3. Check for security issues:
   - Hardcoded secrets (`grep -r "api_key\s*=" src/ | grep -v "os.getenv"`)
   - SQL injection risks
   - Missing input validation
4. Check for broken imports: `python -m py_compile` on each file
5. Identify circular dependencies
6. Check Supabase table usage vs defined tables
7. Review autonomous loop job registration
8. Output structured report with severity ratings

## Output Format
```
SECURITY: [CRITICAL/HIGH/MEDIUM/LOW] — description
QUALITY: [HIGH/MEDIUM/LOW] — description
ARCHITECTURE: [observation]
ACTION REQUIRED: [specific steps]
```

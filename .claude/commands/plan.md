# /plan — Doc-Driven Feature Planning

Create a structured plan document for a feature before any code is written.

## Usage
`/plan <feature description>`

## Steps
1. Create `docs/plans/PLAN-<timestamp>-<slug>.md`
2. Document:
   - **Goal**: What we're building and why
   - **Scope**: What's in / out of scope
   - **Affected files**: Which source files will change
   - **DB changes**: Any new Supabase tables/columns/RLS needed
   - **API dependencies**: New external APIs required
   - **Implementation steps**: Ordered, atomic tasks
   - **Test plan**: How to verify it works
   - **Rollback plan**: How to undo if broken
3. Review with user before proceeding to `/implement`

## Rules
- No code written during planning
- Flag if any step requires manual action (Render env vars, Supabase Dashboard)
- Estimate complexity: S/M/L/XL

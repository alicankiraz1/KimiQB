# Session Spec: Step 1.5 Autopsy

Stage ID: `step15`

Purpose: compile a Session prompt that reviews an existing or partially built repository and creates `Planner-docs/Autopsy.md` plus optional comprehension artifacts.

Required source references:
- `references/Autopsy-Planner.md`
- `references/project-ontology.md`
- `references/project-comprehension-methods.md`
- `references/probe-policy.md`

Safety:
- Read-only repository inspection before writing planner docs.
- No product implementation, dependency installation, commit, push, PR, deploy, or external mutation.
- File boundary is `Planner-docs/`.

Ready condition:
- Session prompt states whether Step 1.5 applies and names the planner-doc files that may be written.

Perform an informed perusal of the specified file or domain.

Read the procedure doc at `docs/procedures/perusal.md` for what to look for, agent configuration, and reporting format.

Target: $ARGUMENTS

Steps:
1. Identify the relevant charter for the target file/domain
2. Load the charter and cross_cutting.md
3. Dispatch a Haiku agent to read the source code against the architectural context
4. Report findings (drift, misplacement, undocumented patterns, vestigial code)

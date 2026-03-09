# [Domain Name] — [one-line description]

Last verified: YYYY-MM-DD
Files covered: [file paths]

---

## [Section Name]

### function_or_class_name [Lnnn]
File: path/to/file.py
[One paragraph: what it does, parameters, return value, side effects]
[Key implementation notes that prevent mistakes]
→ see other_charter.md `related_function` (cross-reference)

### AnotherFunction [Lnnn]
...

---

## Formatting Rules

- **Line references**: `[Lnnn]` after function/class name = approximate line number
- **Cross-references**: `→ see charter.md` links to other charters
- **Access patterns**: (R) = read-only, (W) = write, (RW) = read-write
- **TRIPWIRE markers**: `! TRIPWIRE` = non-obvious behavior that will break if you assume the obvious
- **Bang lines**: `!` prefix = critical warning, read before touching
- **Status markers**: COMPLETE, PARTIAL, DEFERRED = refactoring status

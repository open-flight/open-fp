## What does this PR do?

<!--
This PR must be scoped to a SINGLE feature or fix. If you find yourself
writing "and also...", split it into separate PRs.

Tell the story:
- What is the change?
- Why was it required? What problem does it solve or what need does it meet?
- Reference related issues with "Fixes #123".
-->

## Why was this required?

<!-- The motivation / story. What prompted this work and what is the impact of not doing it? -->

## Automated tests

<!--
Every PR must include tests. Describe the tests you added or updated and
what behavior they cover. If you believe tests are genuinely not applicable,
explain why here.
-->

## Manual (human) testing

<!--
Every PR must describe the manual testing a human performed. Be specific:
- What did you actually run? (simulator, real plates, which UI flows, a printed part)
- What did you observe? Include numbers/screenshots/photos where relevant.
- What edge cases did you exercise by hand?

"Tests pass" is not manual testing — describe what YOU verified by hand.
-->

## Checklist

- [ ] **Single feature/fix** — this PR is scoped to one thing with a clear story above
- [ ] **Automated tests included** — new or updated tests cover this change
- [ ] **Manual testing described** — I documented what I verified by hand above
- [ ] Python tests pass (`pytest`)
- [ ] Ruff passes (`ruff check app/python tools tests docs/img`)
- [ ] Pylint passes (`PYTHONPATH=app/python:tools/sim:tools/bench pylint app/python/open_fp tools/sim tools/bench --fail-under=9`)
- [ ] Hardware changes recorded in `docs/VERIFIED.md` (measurements, fit checks, pin changes)
- [ ] Generated files regenerated and committed (e.g. `docs/img/corner-assembly.svg`, CAD STL/STEP)
- [ ] Updated docs if needed
- [ ] No unrelated changes mixed in

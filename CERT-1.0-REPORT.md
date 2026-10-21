# hstsheader 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to hstsheader. PyPI has 0.2.0 (uploaded
2026-10-19), which is byte for byte the `main` branch at d7e5426 (the wheel's modules
compared with the tree), so every change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (d7e5426, same code as PyPI 0.2.0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Ground truth: fetched sources, the hstspreload checker run live, real headers (item 7)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [ ] Gates (item 15)
- [ ] PR and trace guard CLEAN
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] Merge and publish (item 17)

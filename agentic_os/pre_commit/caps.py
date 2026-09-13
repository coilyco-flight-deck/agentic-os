"""The sentence every cap violation carries.

One constant, so the wording cannot drift across the four validators that
enforce a cap. A cap is back-pressure, and an agent that reads one as a
defect opens a record asking for a raise instead of fitting the change.
See AGENTS.md, "A cap is the budget, not the obstacle".
"""
from __future__ import annotations

CAP_IS_DELIBERATE = (
    "This cap is deliberate. Do not raise it and do not ask for it to be "
    "raised. Fit the change under it, or report what it would have displaced."
)

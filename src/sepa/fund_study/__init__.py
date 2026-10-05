"""Empirical fund-weight study package."""

__all__ = ["main", "run_study"]


def __getattr__(name: str):
    if name in {"main", "run_study"}:
        from sepa.fund_study.__main__ import main, run_study

        return {"main": main, "run_study": run_study}[name]
    raise AttributeError(name)

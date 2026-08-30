class ProcedureCIError(Exception):
    """Base error for a user-facing Procedure CI failure."""


class InputError(ProcedureCIError):
    """Input cannot be safely loaded or is outside the MVP contract."""


class AnalysisError(ProcedureCIError):
    """Analysis could not produce a trustworthy report."""

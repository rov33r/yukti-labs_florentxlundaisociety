import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from pydantic import BaseModel


class RawResult(BaseModel):
    """Result of executing code in sandbox."""
    stdout: str
    stderr: str
    success: bool


async def execute_in_sandbox(code: str) -> RawResult:
    """Execute Python code locally and capture output."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, {"__name__": "__main__"})
        return RawResult(
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
            success=True
        )
    except Exception as e:
        return RawResult(
            stdout=stdout_capture.getvalue(),
            stderr=str(e),
            success=False
        )

import os
from pydantic import BaseModel
from e2b import Sandbox


class RawResult(BaseModel):
    """Result of executing code in E2B sandbox."""
    stdout: str
    stderr: str
    success: bool


async def execute_in_sandbox(code: str) -> RawResult:
    """Execute Python code in E2B sandbox and capture output."""
    api_key = os.getenv("E2B_API_KEY")
    if not api_key:
        raise ValueError("E2B_API_KEY environment variable not set")

    sandbox = Sandbox(api_key=api_key)
    try:
        execution = await sandbox.run_python(code)
        return RawResult(
            stdout=execution.stdout or "",
            stderr=execution.stderr or "",
            success=execution.exit_code == 0
        )
    finally:
        await sandbox.close()

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} '{identifier}' not found",
        )


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class SLABreachError(Exception):
    """Raised internally when an SLA threshold is breached."""

    def __init__(self, case_id: int, breach_type: str, policy_name: str):
        self.case_id = case_id
        self.breach_type = breach_type
        self.policy_name = policy_name
        super().__init__(f"SLA breach ({breach_type}) on case {case_id} — policy: {policy_name}")

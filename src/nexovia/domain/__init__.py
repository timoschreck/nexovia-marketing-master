"""Domain policies that do not depend on infrastructure."""

from .approvals import Approval, ApprovalDecision, ApprovalStatus

__all__ = ["Approval", "ApprovalDecision", "ApprovalStatus"]


"""Exact-scope approval policy for high-impact operations.

An approval never grants a broader permission than its recorded action,
resource, immutable content version, expiry, and optional cost ceiling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum


class ApprovalStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    CONSUMED = "consumed"


class ApprovalDecision(StrEnum):
    ALLOW = "allow"
    DENY_INACTIVE = "deny_inactive"
    DENY_EXPIRED = "deny_expired"
    DENY_ACTION = "deny_action"
    DENY_RESOURCE = "deny_resource"
    DENY_VERSION = "deny_version"
    DENY_COST = "deny_cost"


@dataclass(frozen=True, slots=True)
class Approval:
    approval_id: str
    approved_by: str
    action: str
    resource_id: str
    content_version: str
    expires_at: datetime
    max_cost_eur: Decimal | None = None
    status: ApprovalStatus = ApprovalStatus.ACTIVE

    def __post_init__(self) -> None:
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.max_cost_eur is not None and self.max_cost_eur < 0:
            raise ValueError("max_cost_eur cannot be negative")
        for field_name in (
            "approval_id",
            "approved_by",
            "action",
            "resource_id",
            "content_version",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be blank")

    def evaluate(
        self,
        *,
        action: str,
        resource_id: str,
        content_version: str,
        estimated_cost_eur: Decimal = Decimal("0"),
        now: datetime | None = None,
    ) -> ApprovalDecision:
        """Return one explicit decision; fail closed on every mismatch."""

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if estimated_cost_eur < 0:
            raise ValueError("estimated_cost_eur cannot be negative")

        if self.status is not ApprovalStatus.ACTIVE:
            return ApprovalDecision.DENY_INACTIVE
        if current_time >= self.expires_at:
            return ApprovalDecision.DENY_EXPIRED
        if action != self.action:
            return ApprovalDecision.DENY_ACTION
        if resource_id != self.resource_id:
            return ApprovalDecision.DENY_RESOURCE
        if content_version != self.content_version:
            return ApprovalDecision.DENY_VERSION
        if self.max_cost_eur is not None and estimated_cost_eur > self.max_cost_eur:
            return ApprovalDecision.DENY_COST
        return ApprovalDecision.ALLOW


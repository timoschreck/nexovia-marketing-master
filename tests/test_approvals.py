from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from nexovia.domain.approvals import Approval, ApprovalDecision, ApprovalStatus


class ApprovalPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
        self.approval = Approval(
            approval_id="approval-001",
            approved_by="owner-001",
            action="publish_product",
            resource_id="product-001",
            content_version="v1.0",
            expires_at=self.now + timedelta(hours=1),
            max_cost_eur=Decimal("10.00"),
        )

    def evaluate(self, **overrides: object) -> ApprovalDecision:
        values = {
            "action": "publish_product",
            "resource_id": "product-001",
            "content_version": "v1.0",
            "estimated_cost_eur": Decimal("10.00"),
            "now": self.now,
        }
        values.update(overrides)
        return self.approval.evaluate(**values)  # type: ignore[arg-type]

    def test_exact_scope_is_allowed(self) -> None:
        self.assertEqual(self.evaluate(), ApprovalDecision.ALLOW)

    def test_expired_approval_is_denied(self) -> None:
        self.assertEqual(
            self.evaluate(now=self.approval.expires_at),
            ApprovalDecision.DENY_EXPIRED,
        )

    def test_action_mismatch_is_denied(self) -> None:
        self.assertEqual(
            self.evaluate(action="increase_budget"),
            ApprovalDecision.DENY_ACTION,
        )

    def test_resource_mismatch_is_denied(self) -> None:
        self.assertEqual(
            self.evaluate(resource_id="product-002"),
            ApprovalDecision.DENY_RESOURCE,
        )

    def test_version_mismatch_is_denied(self) -> None:
        self.assertEqual(
            self.evaluate(content_version="v1.1"),
            ApprovalDecision.DENY_VERSION,
        )

    def test_cost_above_limit_is_denied(self) -> None:
        self.assertEqual(
            self.evaluate(estimated_cost_eur=Decimal("10.01")),
            ApprovalDecision.DENY_COST,
        )

    def test_revoked_approval_is_denied(self) -> None:
        revoked = Approval(
            approval_id="approval-002",
            approved_by="owner-001",
            action="publish_product",
            resource_id="product-001",
            content_version="v1.0",
            expires_at=self.now + timedelta(hours=1),
            status=ApprovalStatus.REVOKED,
        )
        self.assertEqual(
            revoked.evaluate(
                action="publish_product",
                resource_id="product-001",
                content_version="v1.0",
                now=self.now,
            ),
            ApprovalDecision.DENY_INACTIVE,
        )

    def test_naive_expiry_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            Approval(
                approval_id="approval-003",
                approved_by="owner-001",
                action="publish_product",
                resource_id="product-001",
                content_version="v1.0",
                expires_at=datetime(2026, 8, 16, 12, 0),
            )


if __name__ == "__main__":
    unittest.main()

from decimal import Decimal
import unittest

from nexovia.domain.product_agents import (
    EvidenceRef,
    HUMAN_ONLY_ACTIONS,
    ProductAgent,
    ProductAgentError,
    ProductAgentRegistry,
    ProductStrategyState,
    StrategyStatement,
    VerificationStatus,
)


PRODUCT_ID = "NEX-PILOT-001"
AGENT_ID = "product_agent_NEX-PILOT-001"


def statement(
    statement_id: str = "statement-001",
    *,
    status: VerificationStatus = VerificationStatus.VERIFIED,
    evidence: tuple[EvidenceRef, ...] | None = None,
) -> StrategyStatement:
    return StrategyStatement(
        statement_id=statement_id,
        text="Synthetic product strategy statement",
        verification_status=status,
        evidence=evidence
        if evidence is not None
        else (EvidenceRef("source-001", product_id=PRODUCT_ID),),
    )


def state(**overrides: object) -> ProductStrategyState:
    values = {
        "product_id": PRODUCT_ID,
        "product_agent_id": AGENT_ID,
        "version": 1,
        "characteristics": (statement("characteristic-001"),),
        "target_groups": (statement("target-group-001"),),
        "marketing_strategies": (statement("strategy-001"),),
    }
    values.update(overrides)
    return ProductStrategyState(**values)  # type: ignore[arg-type]


class ProductAgentPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = ProductAgent(agent_id=AGENT_ID, product_id=PRODUCT_ID)

    def test_one_registered_agent_allows_valid_product_state(self) -> None:
        registry = ProductAgentRegistry()
        registry.register(self.agent)
        registered = registry.require(PRODUCT_ID)
        registered.validate_state(state(), brief_approved=True)

    def test_missing_or_duplicate_assignment_is_blocked(self) -> None:
        registry = ProductAgentRegistry()
        with self.assertRaisesRegex(ProductAgentError, "missing"):
            registry.require(PRODUCT_ID)
        registry.register(self.agent)
        with self.assertRaisesRegex(ProductAgentError, "duplicate"):
            registry.register(ProductAgent("another-agent", PRODUCT_ID))
        with self.assertRaisesRegex(ProductAgentError, "already assigned"):
            registry.register(ProductAgent(AGENT_ID, "NEX-OTHER-001"))

    def test_product_or_agent_id_mismatch_is_blocked(self) -> None:
        with self.assertRaisesRegex(ProductAgentError, "product_id mismatch"):
            self.agent.validate_state(
                state(product_id="NEX-OTHER-001"), brief_approved=True
            )
        with self.assertRaisesRegex(ProductAgentError, "product_agent_id mismatch"):
            self.agent.validate_state(
                state(product_agent_id="wrong-agent"), brief_approved=True
            )

    def test_unapproved_cross_product_evidence_is_blocked(self) -> None:
        with self.assertRaisesRegex(ProductAgentError, "boolean"):
            EvidenceRef(
                "invalid-approval",
                approved_cross_product_standard="yes",  # type: ignore[arg-type]
            )
        foreign = EvidenceRef("foreign-source", product_id="NEX-OTHER-001")
        with self.assertRaisesRegex(ProductAgentError, "cross-product"):
            self.agent.validate_state(
                state(target_groups=(statement(evidence=(foreign,)),)),
                brief_approved=True,
            )
        unscoped = EvidenceRef("unscoped-source")
        with self.assertRaisesRegex(ProductAgentError, "cross-product"):
            self.agent.validate_state(
                state(target_groups=(statement(evidence=(unscoped,)),)),
                brief_approved=True,
            )
        approved_standard = EvidenceRef(
            "approved-standard",
            product_id="NEX-OTHER-001",
            approved_cross_product_standard=True,
        )
        self.agent.validate_state(
            state(target_groups=(statement(evidence=(approved_standard,)),)),
            brief_approved=True,
        )

    def test_unsubstantiated_statement_must_be_not_verified(self) -> None:
        with self.assertRaisesRegex(ProductAgentError, "require evidence"):
            statement(evidence=())
        with self.assertRaisesRegex(ProductAgentError, "verification status"):
            StrategyStatement(
                statement_id="invalid-status",
                text="Synthetic invalid status",
                verification_status="verified",  # type: ignore[arg-type]
                evidence=(),
            )
        unverified = statement(
            status=VerificationStatus.NOT_VERIFIED,
            evidence=(),
        )
        self.agent.validate_state(
            state(marketing_strategies=(unverified,)), brief_approved=True
        )

    def test_invalid_schema_is_blocked(self) -> None:
        with self.assertRaisesRegex(ProductAgentError, "version"):
            state(version=1.5)
        with self.assertRaisesRegex(ProductAgentError, "tuple"):
            state(target_groups=[statement()])
        with self.assertRaisesRegex(ProductAgentError, "schema"):
            self.agent.validate_state(
                state(schema="unknown_schema"), brief_approved=True
            )

    def test_agent_cannot_authorize_human_only_actions(self) -> None:
        self.assertTrue(HUMAN_ONLY_ACTIONS)
        for action in HUMAN_ONLY_ACTIONS:
            with self.subTest(action=action):
                self.assertFalse(self.agent.authorize(action))
        self.assertTrue(self.agent.authorize("propose_product_state"))

    def test_brief_cost_and_time_limits_fail_closed(self) -> None:
        with self.assertRaisesRegex(ProductAgentError, "brief"):
            self.agent.validate_state(state(), brief_approved=False)
        with self.assertRaisesRegex(ProductAgentError, "cost"):
            self.agent.validate_state(
                state(),
                brief_approved=True,
                estimated_cost_eur=Decimal("2.01"),
            )
        with self.assertRaisesRegex(ProductAgentError, "Decimal"):
            self.agent.validate_state(
                state(), brief_approved=True, estimated_cost_eur=2.0  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(ProductAgentError, "time"):
            self.agent.validate_state(
                state(), brief_approved=True, elapsed_seconds=601
            )


if __name__ == "__main__":
    unittest.main()

"""Fail-closed product-agent policy and product strategy state.

Each product has exactly one agent identity. The agent may validate and retain
proposals for its own product, but it cannot approve high-impact actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


PRODUCT_STRATEGY_SCHEMA = "product_strategy_state_v1"
HUMAN_ONLY_ACTIONS = frozenset(
    {
        "approve_product",
        "approve_claims",
        "publish",
        "launch_campaign",
        "mass_outreach",
        "change_permissions",
        "change_budget",
    }
)


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    NOT_VERIFIED = "Nicht verifiziert"


class ProductAgentError(ValueError):
    """Raised when a product-agent invariant fails closed."""


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    source_id: str
    product_id: str | None = None
    approved_cross_product_standard: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ProductAgentError("source_id cannot be blank")
        if self.product_id is not None and (
            not isinstance(self.product_id, str) or not self.product_id.strip()
        ):
            raise ProductAgentError("product_id must be a non-blank string")
        if type(self.approved_cross_product_standard) is not bool:
            raise ProductAgentError("cross-product approval must be boolean")

    def is_allowed_for(self, product_id: str) -> bool:
        return self.product_id == product_id or self.approved_cross_product_standard


@dataclass(frozen=True, slots=True)
class StrategyStatement:
    statement_id: str
    text: str
    verification_status: VerificationStatus
    evidence: tuple[EvidenceRef, ...] = ()
    counterevidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.statement_id, str)
            or not self.statement_id.strip()
            or not isinstance(self.text, str)
            or not self.text.strip()
        ):
            raise ProductAgentError("strategy statements require id and text")
        if not isinstance(self.verification_status, VerificationStatus):
            raise ProductAgentError("invalid verification status")
        if not isinstance(self.evidence, tuple) or not all(
            isinstance(item, EvidenceRef) for item in self.evidence
        ):
            raise ProductAgentError("evidence must be a tuple of EvidenceRef")
        if not isinstance(self.counterevidence, tuple) or not all(
            isinstance(item, EvidenceRef) for item in self.counterevidence
        ):
            raise ProductAgentError("counterevidence must be a tuple of EvidenceRef")
        if (
            self.verification_status is VerificationStatus.VERIFIED
            and not self.evidence
        ):
            raise ProductAgentError("verified statements require evidence")


@dataclass(frozen=True, slots=True)
class ProductStrategyState:
    product_id: str
    product_agent_id: str
    version: int
    characteristics: tuple[StrategyStatement, ...]
    target_groups: tuple[StrategyStatement, ...]
    marketing_strategies: tuple[StrategyStatement, ...]
    schema: str = PRODUCT_STRATEGY_SCHEMA

    def __post_init__(self) -> None:
        if (
            not isinstance(self.product_id, str)
            or not self.product_id.strip()
            or not isinstance(self.product_agent_id, str)
            or not self.product_agent_id.strip()
        ):
            raise ProductAgentError("product and agent ids cannot be blank")
        if type(self.version) is not int or self.version < 1:
            raise ProductAgentError("version must be positive")
        if not isinstance(self.schema, str):
            raise ProductAgentError("schema must be a string")
        for name, values in (
            ("characteristics", self.characteristics),
            ("target_groups", self.target_groups),
            ("marketing_strategies", self.marketing_strategies),
        ):
            if not isinstance(values, tuple) or not all(
                isinstance(item, StrategyStatement) for item in values
            ):
                raise ProductAgentError(
                    f"{name} must be a tuple of StrategyStatement"
                )

    def statements(self) -> tuple[StrategyStatement, ...]:
        return self.characteristics + self.target_groups + self.marketing_strategies


@dataclass(frozen=True, slots=True)
class ProductAgent:
    agent_id: str
    product_id: str
    max_cost_eur: Decimal = Decimal("2.00")
    timeout_seconds: int = 600

    def __post_init__(self) -> None:
        if (
            not isinstance(self.agent_id, str)
            or not self.agent_id.strip()
            or not isinstance(self.product_id, str)
            or not self.product_id.strip()
        ):
            raise ProductAgentError("agent and product ids cannot be blank")
        if not isinstance(self.max_cost_eur, Decimal):
            raise ProductAgentError("max_cost_eur must be Decimal")
        if type(self.timeout_seconds) is not int:
            raise ProductAgentError("timeout_seconds must be int")
        if self.max_cost_eur < 0 or self.timeout_seconds < 1:
            raise ProductAgentError("limits must be non-negative and non-zero")

    def validate_state(
        self,
        state: ProductStrategyState,
        *,
        brief_approved: bool,
        estimated_cost_eur: Decimal = Decimal("0"),
        elapsed_seconds: int = 0,
    ) -> None:
        if not brief_approved:
            raise ProductAgentError("brief is not approved")
        if state.schema != PRODUCT_STRATEGY_SCHEMA:
            raise ProductAgentError("unsupported output schema")
        if state.product_id != self.product_id:
            raise ProductAgentError("product_id mismatch")
        if state.product_agent_id != self.agent_id:
            raise ProductAgentError("product_agent_id mismatch")
        if not isinstance(estimated_cost_eur, Decimal):
            raise ProductAgentError("estimated cost must be Decimal")
        if type(elapsed_seconds) is not int:
            raise ProductAgentError("elapsed seconds must be int")
        if estimated_cost_eur < 0 or estimated_cost_eur > self.max_cost_eur:
            raise ProductAgentError("cost limit reached")
        if elapsed_seconds < 0 or elapsed_seconds > self.timeout_seconds:
            raise ProductAgentError("time limit reached")
        for statement in state.statements():
            for evidence in statement.evidence + statement.counterevidence:
                if not evidence.is_allowed_for(self.product_id):
                    raise ProductAgentError("unapproved cross-product evidence")

    def authorize(self, action: str) -> bool:
        if not isinstance(action, str):
            return False
        if action in HUMAN_ONLY_ACTIONS:
            return False
        return action in {"read_product_state", "propose_product_state"}


@dataclass(slots=True)
class ProductAgentRegistry:
    _by_product: dict[str, ProductAgent] = field(default_factory=dict)
    _by_agent: dict[str, ProductAgent] = field(default_factory=dict)

    def register(self, agent: ProductAgent) -> None:
        if agent.product_id in self._by_product:
            raise ProductAgentError("duplicate product agent")
        if agent.agent_id in self._by_agent:
            raise ProductAgentError("agent already assigned to a product")
        self._by_product[agent.product_id] = agent
        self._by_agent[agent.agent_id] = agent

    def require(self, product_id: str) -> ProductAgent:
        if not isinstance(product_id, str) or not product_id.strip():
            raise ProductAgentError("product_id must be a non-blank string")
        try:
            return self._by_product[product_id]
        except KeyError as exc:
            raise ProductAgentError("missing product agent") from exc

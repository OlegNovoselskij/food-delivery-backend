import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ChargeResult:
    success: bool
    transaction_id: str | None = None
    failure_reason: str | None = None


class PaymentGateway(ABC):
    @abstractmethod
    def charge(self, *, amount: Decimal, method: str, token: str) -> ChargeResult: ...

    @abstractmethod
    def refund(self, transaction_id: str) -> bool: ...


class MockPaymentGateway(PaymentGateway):
    DECLINED_TOKENS = {
        "tok_declined": "card_declined",
        "tok_insufficient_funds": "insufficient_funds",
    }

    def charge(self, *, amount: Decimal, method: str, token: str) -> ChargeResult:
        if token in self.DECLINED_TOKENS:
            return ChargeResult(success=False, failure_reason=self.DECLINED_TOKENS[token])
        if not token.startswith("tok_"):
            return ChargeResult(success=False, failure_reason="invalid_token")
        return ChargeResult(success=True, transaction_id=f"mock_txn_{uuid.uuid4().hex[:16]}")

    def refund(self, transaction_id: str) -> bool:
        return transaction_id.startswith("mock_txn_")

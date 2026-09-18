"""
Antigravity QuantEngine - Order Lifecycle State Machine
Enforces strict, deterministic transitions between order states.
Rejects any illegal or out-of-order transitions.
"""

from typing import Dict, Set
from core.domain.models import OrderStatus, OrderRecord
from core.logging import get_logger

logger = get_logger("execution.state_machine")


class IllegalOrderStateTransitionError(Exception):
    """Raised when an illegal transition is attempted on an order."""
    pass


# Legal state transition directed graph
LEGAL_TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.CREATED: {
        OrderStatus.VALIDATING,
        OrderStatus.REJECTED,
        OrderStatus.ERROR
    },
    OrderStatus.VALIDATING: {
        OrderStatus.SAFETY_CHECK,
        OrderStatus.REJECTED,
        OrderStatus.ERROR
    },
    OrderStatus.SAFETY_CHECK: {
        OrderStatus.SUBMITTING,
        OrderStatus.REJECTED,
        OrderStatus.ERROR
    },
    OrderStatus.SUBMITTING: {
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.SUBMISSION_UNCONFIRMED,
        OrderStatus.REJECTED,
        OrderStatus.ERROR
    },
    OrderStatus.SUBMISSION_UNCONFIRMED: {
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.ERROR
    },
    OrderStatus.ACKNOWLEDGED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_PENDING,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.ERROR
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.PARTIALLY_FILLED, # successive partial fills
        OrderStatus.FILLED,
        OrderStatus.CANCEL_PENDING,
        OrderStatus.CANCELLED,
        OrderStatus.ERROR
    },
    OrderStatus.CANCEL_PENDING: {
        OrderStatus.CANCELLED,
        OrderStatus.FILLED, # race condition where fill happens before cancel ack
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.ERROR
    },
    # Terminal states:
    OrderStatus.FILLED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REJECTED: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.ERROR: set()
}


class OrderStateMachine:
    """Manages order state progression and guarantees transition integrity."""

    @staticmethod
    def transition(order: OrderRecord, target_status: OrderStatus, reason: str = "") -> OrderRecord:
        current_status = order.status
        allowed = LEGAL_TRANSITIONS.get(current_status, set())

        if target_status not in allowed:
            err = (
                f"ILLEGAL ORDER TRANSITION: Order {order.order_id} cannot transition "
                f"from {current_status.value} to {target_status.value}. "
                f"Allowed targets: {[s.value for s in allowed]}."
            )
            logger.error(err)
            raise IllegalOrderStateTransitionError(err)

        order.status = target_status
        logger.info(
            f"Order {order.order_id} [{order.symbol} {order.side.value}]: "
            f"{current_status.value} -> {target_status.value} ({reason})"
        )
        return order

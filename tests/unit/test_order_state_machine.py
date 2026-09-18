import pytest
from core.domain.models import OrderRecord, OrderStatus, OrderSide, OrderType, TimeInForce
from core.execution.order_state_machine import OrderStateMachine, IllegalOrderStateTransitionError


def create_sample_order() -> OrderRecord:
    return OrderRecord(
        order_id="test_ord_1",
        client_order_id="client_1",
        venue="coinbase",
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.5,
        price=65000.0,
        status=OrderStatus.CREATED
    )


def test_valid_order_lifecycle_progression():
    order = create_sample_order()
    assert order.status == OrderStatus.CREATED

    # CREATED -> VALIDATING
    OrderStateMachine.transition(order, OrderStatus.VALIDATING, "Validating")
    assert order.status == OrderStatus.VALIDATING

    # VALIDATING -> SAFETY_CHECK
    OrderStateMachine.transition(order, OrderStatus.SAFETY_CHECK, "Safety gate")
    assert order.status == OrderStatus.SAFETY_CHECK

    # SAFETY_CHECK -> SUBMITTING
    OrderStateMachine.transition(order, OrderStatus.SUBMITTING, "Submitting to sandbox")
    assert order.status == OrderStatus.SUBMITTING

    # SUBMITTING -> ACKNOWLEDGED
    OrderStateMachine.transition(order, OrderStatus.ACKNOWLEDGED, "Sandbox ack")
    assert order.status == OrderStatus.ACKNOWLEDGED

    # ACKNOWLEDGED -> PARTIALLY_FILLED
    OrderStateMachine.transition(order, OrderStatus.PARTIALLY_FILLED, "Partial fill")
    assert order.status == OrderStatus.PARTIALLY_FILLED

    # PARTIALLY_FILLED -> FILLED
    OrderStateMachine.transition(order, OrderStatus.FILLED, "Final fill")
    assert order.status == OrderStatus.FILLED


def test_illegal_order_transition_raises_error():
    order = create_sample_order()
    # Cannot jump directly from CREATED to FILLED
    with pytest.raises(IllegalOrderStateTransitionError):
        OrderStateMachine.transition(order, OrderStatus.FILLED, "Illegal leap")

    # Cannot transition out of terminal FILLED state
    OrderStateMachine.transition(order, OrderStatus.VALIDATING)
    OrderStateMachine.transition(order, OrderStatus.SAFETY_CHECK)
    OrderStateMachine.transition(order, OrderStatus.SUBMITTING)
    OrderStateMachine.transition(order, OrderStatus.ACKNOWLEDGED)
    OrderStateMachine.transition(order, OrderStatus.FILLED)

    with pytest.raises(IllegalOrderStateTransitionError):
        OrderStateMachine.transition(order, OrderStatus.CANCELLED, "Cannot cancel filled")


def test_cancellation_lifecycle():
    order = create_sample_order()
    OrderStateMachine.transition(order, OrderStatus.VALIDATING)
    OrderStateMachine.transition(order, OrderStatus.SAFETY_CHECK)
    OrderStateMachine.transition(order, OrderStatus.SUBMITTING)
    OrderStateMachine.transition(order, OrderStatus.ACKNOWLEDGED)

    # ACKNOWLEDGED -> CANCEL_PENDING -> CANCELLED
    OrderStateMachine.transition(order, OrderStatus.CANCEL_PENDING, "User cancel")
    assert order.status == OrderStatus.CANCEL_PENDING

    OrderStateMachine.transition(order, OrderStatus.CANCELLED, "Confirmed cancel")
    assert order.status == OrderStatus.CANCELLED

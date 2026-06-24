import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation(self, order_id: int):
    """
    Async task: send order confirmation after a CONFIRMED order is created.
    In production this would send an email/SMS/webhook; here we log it.
    """
    try:
        from .models import Order
        order = Order.objects.select_related('store').prefetch_related('items__product').get(id=order_id)

        item_lines = "\n".join(
            f"  - {item.product.title} x {item.quantity_requested}"
            for item in order.items.all()
        )
        logger.info(
            "Order Confirmation\n"
            "==================\n"
            f"Order ID : {order.id}\n"
            f"Store    : {order.store.name}\n"
            f"Status   : {order.status}\n"
            f"Created  : {order.created_at}\n"
            f"Items    :\n{item_lines}"
        )
        return {'order_id': order_id, 'status': 'confirmation_sent'}

    except Exception as exc:
        logger.error(f"send_order_confirmation failed for order {order_id}: {exc}")
        raise self.retry(exc=exc)

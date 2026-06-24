import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample

from apps.stores.models import Store, Inventory
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderSerializer, OrderListSerializer
from .tasks import send_order_confirmation

logger = logging.getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        summary="Create an order",
        description=(
            "Validates stock availability for ALL items before deducting. "
            "Uses transaction.atomic + select_for_update to ensure consistency. "
            "If any product has insufficient stock the entire order is REJECTED and no stock is deducted."
        ),
        tags=["orders"],
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
        examples=[
            OpenApiExample(
                name="Successful order request",
                value={
                    "store_id": 1,
                    "items": [
                        {"product_id": 42, "quantity_requested": 5},
                        {"product_id": 87, "quantity_requested": 2},
                    ],
                },
                request_only=True,
            ),
        ],
    )
)
class OrderCreateView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        items_data = serializer.validated_data['items']

        store = get_object_or_404(Store, pk=store_id)
        product_ids = [item['product_id'] for item in items_data]

        with transaction.atomic():
          
            inventory_qs = (
                Inventory.objects
                .select_for_update()
                .filter(store=store, product_id__in=product_ids)
                .select_related('product')
            )
            inventory_map = {inv.product_id: inv for inv in inventory_qs}

          
            insufficient = []
            missing = []
            for item in items_data:
                pid = item['product_id']
                qty = item['quantity_requested']
                if pid not in inventory_map:
                    missing.append(pid)
                elif inventory_map[pid].quantity < qty:
                    insufficient.append({
                        'product_id': pid,
                        'available': inventory_map[pid].quantity,
                        'requested': qty,
                    })

           
            order = Order.objects.create(store=store, status=Order.Status.PENDING)

          
            order_items = [
                OrderItem(
                    order=order,
                    product_id=item['product_id'],
                    quantity_requested=item['quantity_requested'],
                )
                for item in items_data
                if item['product_id'] not in missing 
            ]
            OrderItem.objects.bulk_create(order_items)

            if missing or insufficient:
               
                order.status = Order.Status.REJECTED
                order.save(update_fields=['status'])
                response_data = {
                    'order_id': order.id,
                    'status': order.status,
                    'created_at': order.created_at,
                    'rejection_reasons': {
                        'missing_products': missing,
                        'insufficient_stock': insufficient,
                    },
                    'items': OrderSerializer(order).data['items'],
                }
                return Response(response_data, status=status.HTTP_201_CREATED)

        
            for item in items_data:
                inv = inventory_map[item['product_id']]
                inv.quantity -= item['quantity_requested']
                inv.save(update_fields=['quantity'])

            order.status = Order.Status.CONFIRMED
            order.save(update_fields=['status'])

         
            from django.core.cache import cache
            cache.delete(f'inventory_store_{store_id}')

           
            send_order_confirmation.delay(order.id)

        serializer_out = OrderSerializer(order)
        return Response(serializer_out.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="List orders for a store",
        description="Returns all orders for the given store, sorted newest first. Includes total item count per order.",
        tags=["orders"],
        responses={200: OrderListSerializer(many=True)},
    )
)
class StoreOrderListView(APIView):
    def get(self, request, store_id):
        get_object_or_404(Store, pk=store_id)

        orders = (
            Order.objects
            .filter(store_id=store_id)
            .annotate(total_items=Count('items'))
            .order_by('-created_at')
        )

        serializer = OrderListSerializer(orders, many=True)
        return Response({'results': serializer.data, 'count': orders.count()})
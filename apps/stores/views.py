import logging
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Store, Inventory
from .serializers import InventorySerializer

logger = logging.getLogger(__name__)

INVENTORY_CACHE_PREFIX = 'inventory_store_'


class StoreInventoryView(APIView):
    """
    GET /stores/<store_id>/inventory/
    Returns inventory for a store with product title, price, category, quantity.
    Results are sorted alphabetically by product title.
    Response is cached in Redis; cache is invalidated on order confirmation.
    """

    def get(self, request, store_id):
        get_object_or_404(Store, pk=store_id)

        cache_key = f'{INVENTORY_CACHE_PREFIX}{store_id}'
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache HIT for inventory store {store_id}")
            return Response(cached)

        logger.debug(f"Cache MISS for inventory store {store_id}")

       
        inventory_qs = (
            Inventory.objects
            .filter(store_id=store_id)
            .select_related('product__category')
            .order_by('product__title')
        )

        serializer = InventorySerializer(inventory_qs, many=True)
        data = serializer.data

        cache.set(cache_key, data, timeout=getattr(settings, 'CACHE_TTL', 300))

        return Response(data)

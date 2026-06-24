from rest_framework import serializers
from .models import Inventory


class InventorySerializer(serializers.ModelSerializer):
    inventory_id = serializers.IntegerField(source='id', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price', max_digits=10, decimal_places=2, read_only=True
    )
    category_name = serializers.CharField(source='product.category.name', read_only=True)

    class Meta:
        model = Inventory
        fields = [
            'inventory_id',
            'product_id',
            'product_title',
            'product_price',
            'category_name',
            'quantity',
        ]
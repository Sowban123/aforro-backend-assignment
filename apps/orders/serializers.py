from rest_framework import serializers
from .models import Order, OrderItem



class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity_requested = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    items = OrderItemInputSerializer(many=True, min_length=1)

    def validate_items(self, items):
      
        product_ids = [item['product_id'] for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Duplicate product_id found in items.")
        return items


class OrderItemOutputSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_title', 'quantity_requested']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemOutputSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    total_items = serializers.SerializerMethodField()

    def get_total_items(self, obj):
        return sum(item.quantity_requested for item in obj.items.all())

    class Meta:
        model = Order
        fields = ['id', 'store_id', 'store_name', 'status', 'created_at', 'items', 'total_items']


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order listing (no items detail, uses annotation)."""
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'created_at', 'total_items']
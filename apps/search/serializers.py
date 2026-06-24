from rest_framework import serializers
from apps.products.models import Product


class ProductSearchSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    # Optionally included when store_id filter is provided
    store_quantity = serializers.IntegerField(read_only=True, default=None, allow_null=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'category_name', 'created_at', 'store_quantity']

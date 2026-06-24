from django.urls import path
from .views import StoreInventoryView

urlpatterns = [
    path('stores/<int:store_id>/inventory/', StoreInventoryView.as_view(), name='store-inventory'),
]

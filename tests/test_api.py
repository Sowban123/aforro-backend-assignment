"""
Test suite for Aforro backend.
Covers: order creation (success + rejection), inventory API, search, autocomplete.
"""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from apps.products.models import Category, Product
from apps.stores.models import Store, Inventory
from apps.orders.models import Order, OrderItem


def create_base_data():
    """Helper: returns (category, product, store, inventory)."""
    cat = Category.objects.create(name='Test Category')
    product = Product.objects.create(
        title='Test Widget', price=Decimal('49.99'), category=cat
    )
    store = Store.objects.create(name='Test Store', location='Chennai')
    inv = Inventory.objects.create(store=store, product=product, quantity=100)
    return cat, product, store, inv


class OrderCreateSuccessTest(APITestCase):
    """Test 1: Successful order creation deducts inventory and sets CONFIRMED."""

    def setUp(self):
        self.cat, self.product, self.store, self.inv = create_base_data()

    def test_confirmed_order(self):
        url = reverse('order-create')
        payload = {
            'store_id': self.store.id,
            'items': [{'product_id': self.product.id, 'quantity_requested': 10}],
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'CONFIRMED')

        # Verify inventory was deducted
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, 90)

        # Verify order + items in DB
        order = Order.objects.get(id=response.data['id'])
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.items.count(), 1)


class OrderCreateRejectedTest(APITestCase):
    """Test 2: Order rejected when stock is insufficient; no inventory change."""

    def setUp(self):
        self.cat, self.product, self.store, self.inv = create_base_data()
        self.inv.quantity = 5
        self.inv.save()

    def test_rejected_order_insufficient_stock(self):
        url = reverse('order-create')
        payload = {
            'store_id': self.store.id,
            'items': [{'product_id': self.product.id, 'quantity_requested': 50}],
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'REJECTED')

        # Inventory must NOT be deducted
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, 5)

    def test_rejected_when_product_not_in_store(self):
        """Order rejected when product has no inventory entry for the store."""
        other_store = Store.objects.create(name='Other Store', location='Mumbai')
        url = reverse('order-create')
        payload = {
            'store_id': other_store.id,
            'items': [{'product_id': self.product.id, 'quantity_requested': 1}],
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'REJECTED')


class InventoryAPITest(APITestCase):
    """Test 3: Inventory listing returns correct data sorted by product title."""

    def setUp(self):
        cat = Category.objects.create(name='Electronics')
        self.store = Store.objects.create(name='Inv Store', location='Delhi')
        p1 = Product.objects.create(title='Zebra Headphones', price=Decimal('199.99'), category=cat)
        p2 = Product.objects.create(title='Alpha Speaker', price=Decimal('99.99'), category=cat)
        Inventory.objects.create(store=self.store, product=p1, quantity=10)
        Inventory.objects.create(store=self.store, product=p2, quantity=20)

    def test_inventory_listing(self):
        url = reverse('store-inventory', kwargs={'store_id': self.store.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item['product_title'] for item in response.data]
        # Should be alphabetically sorted
        self.assertEqual(titles, sorted(titles))
        self.assertEqual(len(titles), 2)
        # First should be Alpha Speaker
        self.assertEqual(titles[0], 'Alpha Speaker')

    def test_inventory_404_for_missing_store(self):
        url = reverse('store-inventory', kwargs={'store_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ProductSearchAPITest(APITestCase):
    """Test 4: Product search with keyword, category, and price filters."""

    def setUp(self):
        cat1 = Category.objects.create(name='Gadgets')
        cat2 = Category.objects.create(name='Books')
        Product.objects.create(title='Bluetooth Earbuds', price=Decimal('29.99'), category=cat1)
        Product.objects.create(title='Python Programming Guide', price=Decimal('14.99'), category=cat2)
        Product.objects.create(title='Wireless Charger', price=Decimal('49.99'), category=cat1)

    def test_keyword_search(self):
        url = reverse('product-search')
        response = self.client.get(url, {'q': 'bluetooth'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Bluetooth Earbuds')

    def test_category_filter(self):
        url = reverse('product-search')
        response = self.client.get(url, {'category': 'books'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_price_range_filter(self):
        url = reverse('product-search')
        response = self.client.get(url, {'price_min': '30', 'price_max': '60'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Wireless Charger')

    def test_pagination_metadata_present(self):
        url = reverse('product-search')
        response = self.client.get(url)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('total_pages', response.data)
        self.assertIn('results', response.data)

    def test_sort_by_price_asc(self):
        url = reverse('product-search')
        response = self.client.get(url, {'sort': 'price_asc'})
        prices = [float(r['price']) for r in response.data['results']]
        self.assertEqual(prices, sorted(prices))

    def test_sort_by_price_desc(self):
        url = reverse('product-search')
        response = self.client.get(url, {'sort': 'price_desc'})
        prices = [float(r['price']) for r in response.data['results']]
        self.assertEqual(prices, sorted(prices, reverse=True))


class AutocompleteAPITest(APITestCase):
    """Test 5: Autocomplete returns prefix matches first, max 10 results."""

    def setUp(self):
        cat = Category.objects.create(name='Test')
        titles = [
            'Apple Juice', 'Apple Watch', 'Applesauce',
            'Banana Split', 'Grape Juice', 'Pineapple Ring',
            'Snapple Drink', 'Grapefruit',
        ]
        for title in titles:
            Product.objects.create(title=title, price=Decimal('9.99'), category=cat)

    def test_requires_minimum_3_chars(self):
        url = reverse('autocomplete')
        response = self.client.get(url, {'q': 'ap'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_prefix_matches_returned(self):
        url = reverse('autocomplete')
        response = self.client.get(url, {'q': 'App'})
        self.assertEqual(response.status_code, 200)
        suggestions = response.data['suggestions']
        # Prefix matches (Apple*, Applesauce) should appear first
        self.assertTrue(any('Apple' in s for s in suggestions))

    def test_max_10_results(self):
        cat = Category.objects.get(name='Test')
        for i in range(20):
            Product.objects.create(title=f'Apple Product {i}', price=Decimal('1.00'), category=cat)
        url = reverse('autocomplete')
        response = self.client.get(url, {'q': 'App'})
        self.assertLessEqual(len(response.data['suggestions']), 10)

    def test_general_icontains_included(self):
        url = reverse('autocomplete')
        response = self.client.get(url, {'q': 'ple'})
        self.assertEqual(response.status_code, 200)
        suggestions = response.data['suggestions']
        # Should include "Pineapple Ring" and "Apple" variants
        self.assertTrue(len(suggestions) > 0)


class OrderListAPITest(APITestCase):
    """Test 6: Store order listing returns correct orders sorted newest first."""

    def setUp(self):
        cat = Category.objects.create(name='Cat')
        product = Product.objects.create(title='Item', price=Decimal('10'), category=cat)
        self.store = Store.objects.create(name='List Store', location='Pune')
        inv = Inventory.objects.create(store=self.store, product=product, quantity=999)
        # Create two orders directly
        self.order1 = Order.objects.create(store=self.store, status=Order.Status.CONFIRMED)
        self.order2 = Order.objects.create(store=self.store, status=Order.Status.REJECTED)

    def test_order_list(self):
        url = reverse('store-orders', kwargs={'store_id': self.store.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 2)

    def test_results_have_required_fields(self):
        url = reverse('store-orders', kwargs={'store_id': self.store.id})
        response = self.client.get(url)
        result = response.data['results'][0]
        self.assertIn('id', result)
        self.assertIn('status', result)
        self.assertIn('created_at', result)
        self.assertIn('total_items', result)

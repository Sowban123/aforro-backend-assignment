import logging
from django.db.models import Q, Value, IntegerField, Case, When, Subquery, OuterRef
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from apps.products.models import Product
from apps.stores.models import Inventory
from .serializers import ProductSearchSerializer

logger = logging.getLogger(__name__)


class SearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'results': data,
        })


class ProductSearchView(APIView):
    """
    GET /api/search/products/
    Keyword search + optional filters (category, price_min, price_max, store_id, in_stock).
    Sorting: price_asc, price_desc, newest, relevance (default).
    Includes pagination metadata.
    If store_id provided, includes inventory quantity for that store.
    """

    @extend_schema(
        summary="Search products",
        description=(
            "Full-text keyword search across product titles, descriptions, and category names. "
            "Supports filtering by category, price range, store, and stock availability. "
            "Results are paginated and can be sorted by price, date, or relevance. "
            "When `store_id` is provided, each result includes the inventory quantity for that store."
        ),
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Keyword to search across product title, description, and category name.",
                examples=[
                    OpenApiExample("Book search", value="21 lessons"),
                    OpenApiExample("Category search", value="electronics"),
                ],
            ),
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter results by category name (case-insensitive, partial match).",
                examples=[
                    OpenApiExample("Books category", value="Books"),
                ],
            ),
            OpenApiParameter(
                name='price_min',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Minimum product price (inclusive).",
                examples=[
                    OpenApiExample("Min price", value=100.00),
                ],
            ),
            OpenApiParameter(
                name='price_max',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum product price (inclusive).",
                examples=[
                    OpenApiExample("Max price", value=1500.00),
                ],
            ),
            OpenApiParameter(
                name='store_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filter products available in a specific store. "
                    "When provided, each result includes `store_quantity` for that store."
                ),
                examples=[
                    OpenApiExample("Store ID", value=3),
                ],
            ),
            OpenApiParameter(
                name='in_stock',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filter to only products with stock greater than 0. "
                    "Only effective when `store_id` is also provided. "
                    "Pass `true` to enable."
                ),
                enum=['true', 'false'],
                examples=[
                    OpenApiExample("In stock only", value="true"),
                ],
            ),
            OpenApiParameter(
                name='sort',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Sort order for results. "
                    "`relevance` (default) ranks title matches above description/category matches. "
                    "`price_asc` and `price_desc` sort by price. "
                    "`newest` sorts by creation date descending."
                ),
                enum=['relevance', 'price_asc', 'price_desc', 'newest'],
                default='relevance',
                examples=[
                    OpenApiExample("Sort by price ascending", value="price_asc"),
                    OpenApiExample("Sort by newest", value="newest"),
                ],
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page number for paginated results (default: 1).",
                examples=[
                    OpenApiExample("Page 2", value=2),
                ],
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Number of results per page (default: 20, max: 100).",
                examples=[
                    OpenApiExample("50 per page", value=50),
                ],
            ),
        ],
        responses={200: ProductSearchSerializer(many=True)},
        tags=["Search"],
    )
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        category = request.query_params.get('category', '')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')
        store_id = request.query_params.get('store_id')
        in_stock = request.query_params.get('in_stock', '').lower()
        sort = request.query_params.get('sort', 'relevance')

        qs = Product.objects.select_related('category')

        # Keyword search across title, description, category name
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(category__name__icontains=q)
            )

        # Category filter
        if category:
            qs = qs.filter(category__name__icontains=category)

        # Price range filter
        if price_min:
            try:
                qs = qs.filter(price__gte=float(price_min))
            except ValueError:
                pass
        if price_max:
            try:
                qs = qs.filter(price__lte=float(price_max))
            except ValueError:
                pass

        # Store filter + annotate inventory quantity for that store
        if store_id:
            try:
                store_id_int = int(store_id)
                # Subquery to get quantity for this store
                inventory_subquery = Inventory.objects.filter(
                    store_id=store_id_int, product=OuterRef('pk')
                ).values('quantity')[:1]
                qs = qs.annotate(
                    store_quantity=Coalesce(Subquery(inventory_subquery), Value(0))
                )
                # in_stock filter (requires store_id)
                if in_stock == 'true':
                    qs = qs.filter(store_quantity__gt=0)
            except ValueError:
                pass
        else:
            # Annotate with None so serializer field exists
            qs = qs.annotate(store_quantity=Value(None, output_field=IntegerField()))

        # Sorting
        if sort == 'price_asc':
            qs = qs.order_by('price')
        elif sort == 'price_desc':
            qs = qs.order_by('-price')
        elif sort == 'newest':
            qs = qs.order_by('-created_at')
        else:
            # Relevance: title match ranks higher than description/category match
            if q:
                qs = qs.annotate(
                    relevance_rank=Case(
                        When(title__icontains=q, then=Value(2)),
                        default=Value(1),
                        output_field=IntegerField(),
                    )
                ).order_by('-relevance_rank', 'title')
            else:
                qs = qs.order_by('title')

        paginator = SearchPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductSearchSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AutocompleteView(APIView):
    """
    GET /api/search/suggest/?q=xxx
    Returns up to 10 product title suggestions.
    Minimum 3 characters. Prefix matches appear before general matches.
    """

    @extend_schema(
        summary="Autocomplete product titles",
        description=(
            "Returns up to 10 product title suggestions for the given query string. "
            "Requires a minimum of 3 characters. "
            "Prefix matches (titles starting with the query) are ranked before general substring matches. "
            "Useful for powering search-as-you-type UI components."
        ),
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Search prefix or keyword (minimum 3 characters).",
                examples=[
                    OpenApiExample("Short prefix", value="car"),
                    OpenApiExample("Longer prefix", value="harry pot"),
                ],
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Carbon Steel Pan", "Cardamom Seeds", "Card Game Set"],
                    }
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Minimum 3 characters required.",
                    },
                    "suggestions": {
                        "type": "array",
                        "items": {},
                        "example": [],
                    },
                },
            },
        },
        tags=["Search"],
    )
    def get(self, request):
        q = request.query_params.get('q', '').strip()

        if len(q) < 3:
            return Response(
                {'error': 'Minimum 3 characters required.', 'suggestions': []},
                status=400
            )

        # Prefix matches ranked first, then general icontains
        prefix_matches = (
            Product.objects
            .filter(title__istartswith=q)
            .values_list('title', flat=True)
            .order_by('title')[:10]
        )
        prefix_list = list(prefix_matches)

        if len(prefix_list) < 10:
            # Fill remaining slots with non-prefix icontains matches
            general_matches = (
                Product.objects
                .filter(title__icontains=q)
                .exclude(title__istartswith=q)
                .values_list('title', flat=True)
                .order_by('title')[:10 - len(prefix_list)]
            )
            suggestions = prefix_list + list(general_matches)
        else:
            suggestions = prefix_list

        return Response({'suggestions': suggestions[:10]})
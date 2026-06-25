# Aforro Backend — Round 2 Assignment

A production-quality Django REST Framework backend demonstrating clean architecture,
query optimization, Redis caching, Celery async tasks, and Docker containerization.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | Django 4.2 + Django REST Framework 3.15 |
| Database | PostgreSQL 15 |
| Cache | Redis 7 via django-redis |
| Async Queue | Celery 5.3 with Redis as broker |
| Task Scheduling | Celery Beat + django-celery-beat |
| Containerization | Docker + Docker Compose |
| API Documentation | drf-spectacular (Swagger UI) |
| Seed Data | Faker + curated realistic product catalog |

---

## Project Structure

```
aforro/
├── apps/
│   ├── products/                   # Category, Product models + admin
│   ├── stores/                     # Store, Inventory models + inventory API (Redis cached)
│   ├── orders/                     # Order, OrderItem models + creation/listing APIs + Celery task
│   ├── search/                     # Product search API + autocomplete API
│   └── common/
│       └── management/
│           └── commands/
│               └── seed_data.py    # Realistic e-commerce seed command
├── config/
│   ├── __init__.py                 # Celery app auto-discovery
│   ├── settings.py                 # Main settings (env-driven)
│   ├── test_settings.py            # SQLite + locmem cache for tests (no Docker needed)
│   ├── celery.py                   # Celery application config
│   ├── urls.py                     # Root URL configuration
│   └── wsgi.py
├── tests/
│   └── test_api.py                 # 17 tests covering all major flows
├── .env.example                    # Environment variable template
├── Dockerfile
├── docker-compose.yml              # Django + PostgreSQL + Redis + Celery Worker + Beat
├── requirements.txt
└── README.md
```

---

## Environment Variables

Copy `.env.example` to `.env` before running anything.

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (insecure dev key) | Django secret key — change in production |
| `DEBUG` | `True` | Debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Comma-separated allowed hosts |
| `DB_NAME` | `aforro_db` | PostgreSQL database name |
| `DB_USER` | `aforro_user` | PostgreSQL user |
| `DB_PASSWORD` | `aforro_pass` | PostgreSQL password |
| `DB_HOST` | `db` | PostgreSQL host (`db` in Docker, `localhost` for local dev) |
| `DB_PORT` | `5432` | PostgreSQL port |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL for caching (DB 0) |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Redis URL for Celery broker (DB 1) |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Redis URL for Celery results (DB 2) |
| `CACHE_TTL` | `300` | Inventory cache TTL in seconds |

---

## Docker Setup (Recommended)

### Step 1 — Clone and configure

```bash
git clone <your-repo-url>
cd aforro
cp .env.example .env
```

### Step 2 — Build and start all services

```bash
docker compose up --build -d
```

This starts five services:

| Service | Description |
|---|---|
| `db` | PostgreSQL 15 |
| `redis` | Redis 7 |
| `api` | Django on port 8000 — runs `migrate` + `collectstatic` automatically on startup |
| `celery_worker` | Celery worker — processes async tasks with concurrency 4 |
| `celery_beat` | Celery beat — periodic task scheduler using DatabaseScheduler |

### Step 3 — Create a superuser (for Django admin)

```bash
docker compose exec api python manage.py createsuperuser
```

### Step 4 — Seed the database

```bash
docker compose exec api python manage.py seed_data
```

Generates:
- **10 categories:** Electronics, Fashion, Grocery, Home & Kitchen, Sports, Books, Beauty, Automotive, Office Supplies, Toys
- **1000+ products:** iPhone 15, Samsung Galaxy S24, Nike Air Max 270, Levi's 511 Slim Jeans, Tata Tea Gold 1kg, etc.
- **22 stores:** Chennai Central Store, Bangalore Tech Store, Mumbai Retail Hub, Hyderabad Electronics Center, Delhi Shopping Point, etc.
- **8000+ inventory records across all stores**

### Step 5 — Access the application

| URL | Description |
|---|---|
| `http://localhost:8000/api/docs/` | Swagger UI — interactive API documentation |
| `http://localhost:8000/api/schema/` | Raw OpenAPI schema (YAML) |
| `http://localhost:8000/admin/` | Django admin panel |

---

### Useful Docker Commands

```bash
# View logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f celery_worker

# Stop all services
docker compose down

# Stop and remove volumes (wipes the database)
docker compose down -v

# Open Django shell
docker compose exec api python manage.py shell

# Run tests inside the container
docker compose exec api python manage.py test tests --settings=config.test_settings -v 2

# Monitor registered Celery tasks
docker compose exec celery_worker celery -A config inspect registered

# Monitor active Celery tasks
docker compose exec celery_worker celery -A config inspect active

# Inspect Redis cache keys
docker compose exec redis redis-cli keys "*"
```

---

## Local Development (without Docker)

Requires PostgreSQL and Redis running locally.

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DB_HOST=localhost
#            set REDIS_URL=redis://localhost:6379/0
#            set CELERY_BROKER_URL=redis://localhost:6379/1
#            set CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Run migrations
python manage.py migrate

# Seed the database
python manage.py seed_data

# Start the development server
python manage.py runserver
```

### Run tests (SQLite — no Docker or PostgreSQL required)

```bash
python manage.py test tests --settings=config.test_settings -v 2
```

Expected output:

```
Ran 17 tests in ~0.2s

OK
```

---

## API Endpoints

### 1. Create Order

```
POST /orders/
Content-Type: application/json
```

**Request body:**

```json
{
  "store_id": 1,
  "items": [
    {
      "product_id": 179,
      "quantity_requested": 1
    }
  ]
}
```

**Processing rules:**
- The entire operation runs inside `transaction.atomic()` with `select_for_update()` locking inventory rows
- If **all** items have sufficient stock → order is `CONFIRMED`, inventory quantities are deducted
- If **any** item is missing from the store's inventory or has insufficient stock → order is `REJECTED`, no stock is deducted

**Response — CONFIRMED (HTTP 201):**

```json
{
  "id": 1,
  "store_id": 1,
  "store_name": "Chennai Central Store",
  "status": "CONFIRMED",
  "created_at": "2024-06-01T10:30:00Z",
  "items": [
    {
      "id": 1,
      "product_id": 179,
      "product_title": "21 Lessons for the 21st Century",
      "quantity_requested": 1
    }
  ],
  "total_items": 1
}
```

> **Note on `total_items`:** This is the count of distinct order item rows, annotated via
> `Count('items')`. On the create response it reflects the number of line items in this order.

**Response — REJECTED (HTTP 201):**

```json
{
  "order_id": 2,
  "status": "REJECTED",
  "created_at": "2024-06-01T10:31:00Z",
  "rejection_reasons": {
    "missing_products": [],
    "insufficient_stock": [
      {
        "product_id": 87,
        "available": 1,
        "requested": 2
      }
    ]
  },
  "items": []
}
```

---

### 2. List Orders for a Store

```
GET /stores/<store_id>/orders/
```

Returns all orders for the given store, sorted newest first.
`total_items` is the **count of distinct order item rows** annotated via `Count('items')`.

**Sample response:**

```json
{
  "count": 2,
  "results": [
    {
      "id": 2,
      "status": "REJECTED",
      "created_at": "2024-06-01T10:31:00Z",
      "total_items": 0
    },
    {
      "id": 1,
      "status": "CONFIRMED",
      "created_at": "2024-06-01T10:30:00Z",
      "total_items": 1
    }
  ]
}
```

---

### 3. Inventory Listing

```
GET /stores/<store_id>/inventory/
```

Returns all inventory items for the store sorted **alphabetically by product title**.
Response is **cached in Redis** on first fetch; subsequent requests are served from cache.

**Response fields:**

| Field         | Description            |
| ------------- | ---------------------- |
| inventory_id  | Inventory record ID    |
| product_id    | Product ID             |
| product_title | Product title          |
| product_price | Product price          |
| category_name | Product category       |
| quantity      | Current stock quantity |


**Sample response:**

```json
[
  {
    "inventory_id": 2283,
    "product_id": 179,
    "product_title": "21 Lessons for the 21st Century",
    "product_price": "1093.40",
    "category_name": "Books",
    "quantity": 399
  },
  {
    "inventory_id": 2379,
    "product_id": 244,
    "product_title": "3M Car Interior Cleaner",
    "product_price": "4698.23",
    "category_name": "Automotive",
    "quantity": 294
  }
]
```

Returns `404` if the store does not exist.

---

### 4. Product Search

```
GET /api/search/products/
```

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Keyword — searches `title`, `description`, and `category name` (icontains) |
| `category` | string | Filter by category name (partial, case-insensitive) |
| `price_min` | number | Minimum price (inclusive) |
| `price_max` | number | Maximum price (inclusive) |
| `store_id` | integer | Annotates each result with `store_quantity` for that store |
| `in_stock` | `true` | Only return products with `store_quantity > 0` (requires `store_id`) |
| `sort` | string | `price_asc`, `price_desc`, `newest`, `relevance` (default) |
| `page` | integer | Page number (default `1`) |
| `page_size` | integer | Results per page (default `20`, max `100`) |

**Sample request:**

```
GET /api/search/products/?q=samsung&category=electronics&price_min=20000&sort=price_asc&page=1
```

**Sample response:**

```json
{
  "count": 4,
  "next": "http://localhost:8000/api/search/products/?page=2",
  "previous": null,
  "page": 1,
  "total_pages": 1,
  "results": [
    {
      "id": 4,
      "title": "Samsung Galaxy S23 Ultra",
      "description": "Experience the best of Electronics with Samsung Galaxy S23 Ultra.",
      "price": "89999.00",
      "category_name": "Electronics",
      "created_at": "2024-06-01T00:00:00Z",
      "store_quantity": null
    }
  ]
}
```

> `store_quantity` is `null` when no `store_id` is provided. It becomes an integer when `store_id` is given.

---

### 5. Autocomplete

```
GET /api/search/suggest/?q=<query>
```

**Rules:**
- Returns `400` if `q` is fewer than 3 characters
- Returns up to **10** product title suggestions
- **Prefix matches** (`istartswith`) returned first; remaining slots filled with general `icontains` matches

**Sample request:**

```
GET /api/search/suggest/?q=sam
```

**Sample response:**

```json
{
  "suggestions": [
    "Samsung Galaxy S24",
    "Samsung Galaxy S23 Ultra",
    "Samsung Galaxy Watch 6",
    "Samsung Galaxy Tab S9",
    "Samsung 970 EVO SSD"
  ]
}
```

**Error — fewer than 3 characters (HTTP 400):**

```json
{
  "error": "Minimum 3 characters required.",
  "suggestions": []
}
```

---

## Data Models

```
Category                  Product
────────                  ──────────────────────────
id (PK)                   id (PK)
name (unique)             title (indexed)
                          description (nullable)
                          price (indexed)
                          category_id ──► Category
                          created_at (indexed)

Store                     Inventory
──────────────            ──────────────────────────────
id (PK)                   id (PK)
name                      store_id  ──► Store
location                  product_id ──► Product
                          quantity
                          UNIQUE(store_id, product_id)

Order                     OrderItem
──────────────────────    ────────────────────────
id (PK)                   id (PK)
store_id ──► Store        order_id ──► Order
status                    product_id ──► Product
  PENDING                 quantity_requested
  CONFIRMED
  REJECTED
created_at
INDEX(store_id, -created_at)
INDEX(status)
```

---

## Redis Caching

**Strategy:** Cache-aside pattern on inventory listing.

- **Cache key:** `inventory_store_{store_id}`
- **TTL:** 300 seconds (configurable via `CACHE_TTL` env var)
- **Cache MISS:** Hits PostgreSQL, serializes, stores in Redis
- **Cache HIT:** Returns directly from Redis, zero DB queries
- **Invalidation:** Explicitly deleted after every `CONFIRMED` order so stock is never served stale

```python
# apps/stores/views.py
cache_key = f'inventory_store_{store_id}'
cached = cache.get(cache_key)
if cached is not None:
    return Response(cached)          # HIT — no DB query

# ... query DB and serialize ...
cache.set(cache_key, data, timeout=settings.CACHE_TTL)
```

```python
# apps/orders/views.py — after stock deduction on CONFIRMED order
cache.delete(f'inventory_store_{store_id}')
```

**Verify caching:**

```bash
# First request — MISS, queries database
curl http://localhost:8000/stores/1/inventory/

# Second request — HIT, served from Redis
curl http://localhost:8000/stores/1/inventory/

# Inspect Redis keys
docker compose exec redis redis-cli keys "*inventory*"

# Check TTL
docker compose exec redis redis-cli ttl "inventory_store_1"
```

---

## Celery Async Tasks

### `send_order_confirmation(order_id)`

Defined in `apps/orders/tasks.py`. Triggered automatically after every `CONFIRMED` order.

```python
# apps/orders/views.py — called after stock is deducted
send_order_confirmation.delay(order.id)
```

**What the task does:**
1. Fetches the order with `select_related('store')` and `prefetch_related('items__product')`
2. Logs a formatted confirmation (store, status, all items with quantities)
3. Returns `{'order_id': order_id, 'status': 'confirmation_sent'}`

In production this would send email / SMS / webhook notifications.

**Task config:**

| Setting | Value |
|---|---|
| `max_retries` | 3 |
| `default_retry_delay` | 60 seconds |
| Broker | Redis DB 1 |
| Result backend | Redis DB 2 |
| Runs on | `celery_worker` container |

**Monitor:**

```bash
docker compose exec celery_worker celery -A config inspect registered
docker compose exec celery_worker celery -A config inspect active
docker compose exec celery_worker celery -A config inspect stats
```

---

## Query Optimization

| Technique | Where Used | Why |
|---|---|---|
| `select_related('product__category')` | Inventory listing | Joins product + category in one SQL query |
| `select_related('store')` | Order confirmation task | Avoids extra query for store name |
| `prefetch_related('items__product')` | Order confirmation task | Batch-fetches all items and their products |
| `annotate(total_items=Count('items'))` | Order listing | Counts items per order in SQL — no N+1 |
| `annotate(store_quantity=Subquery(...))` | Product search | Inlines per-store inventory quantity |
| `select_for_update()` | Order creation | Locks inventory rows during atomic transaction |
| `bulk_create(..., batch_size=500)` | Seed command | Batch-inserts thousands of rows efficiently |
| DB indexes on FK columns | All models | Speeds up joins and filter queries |
| Compound index `(store_id, -created_at)` | Order model | Optimises the store order listing sort |

---

## Scalability Considerations

### Database
- All foreign keys indexed; `unique_together` on `(store, product)` enforced at DB level
- `select_for_update()` prevents inventory race conditions under concurrent requests
- `transaction.atomic()` guarantees all-or-nothing order processing with full rollback on failure

### Caching
- Per-store cache keys allow surgical invalidation without affecting other stores
- `CACHE_TTL` is environment-configurable per deployment stage
- Extendable to product search with query-parameter composite cache keys

### Search
- `icontains` is correct for MVP / moderate data volumes
- For millions of products: migrate to **PostgreSQL full-text search** (`SearchVector` + `SearchRank`) or **Elasticsearch**
- Autocomplete runs two separate indexed queries (prefix-first via `istartswith`, then `icontains` minus prefix) to enforce correct ranking

### Celery
- `celery_worker` and `celery_beat` are separate containers — independently scalable
- Tasks retry up to 3 times with 60-second delays
- Horizontal scaling: `docker compose up --scale celery_worker=4`

### Future Improvements
1. JWT authentication on all endpoints
2. Redis rate limiting on `GET /api/search/suggest/` (20 req/min/IP)
3. PostgreSQL full-text indexes for production-scale search
4. Cursor-based pagination for high-volume listing endpoints
5. Structured JSON logging with per-request correlation IDs (structlog)
6. `/health/` endpoint for load balancer and container orchestration probes
7. API versioning (`/api/v1/`)

---

## Tests

17 tests across 6 test classes. Run with:

```bash
python manage.py test tests --settings=config.test_settings -v 2
```

| Class | Test | What it verifies |
|---|---|---|
| `OrderCreateSuccessTest` | `test_confirmed_order` | Order CONFIRMED, inventory deducted by exact quantity |
| `OrderCreateRejectedTest` | `test_rejected_order_insufficient_stock` | Order REJECTED when qty > stock; inventory unchanged |
| `OrderCreateRejectedTest` | `test_rejected_when_product_not_in_store` | Order REJECTED when product has no inventory row for store |
| `InventoryAPITest` | `test_inventory_listing` | Alphabetical sort by `product_title`; correct field names returned |
| `InventoryAPITest` | `test_inventory_404_for_missing_store` | Returns 404 for non-existent store |
| `ProductSearchAPITest` | `test_keyword_search` | `?q=bluetooth` returns only matching product |
| `ProductSearchAPITest` | `test_category_filter` | `?category=books` filters correctly |
| `ProductSearchAPITest` | `test_price_range_filter` | `?price_min=30&price_max=60` filters correctly |
| `ProductSearchAPITest` | `test_pagination_metadata_present` | Response has `count`, `next`, `previous`, `total_pages`, `results` |
| `ProductSearchAPITest` | `test_sort_by_price_asc` | `?sort=price_asc` returns prices in ascending order |
| `ProductSearchAPITest` | `test_sort_by_price_desc` | `?sort=price_desc` returns prices in descending order |
| `AutocompleteAPITest` | `test_requires_minimum_3_chars` | Returns HTTP 400 with `error` key when `q` < 3 chars |
| `AutocompleteAPITest` | `test_prefix_matches_returned` | Prefix matches present in suggestions |
| `AutocompleteAPITest` | `test_max_10_results` | Never returns more than 10 suggestions |
| `AutocompleteAPITest` | `test_general_icontains_included` | Non-prefix contains matches returned when prefix slots spare |
| `OrderListAPITest` | `test_order_list` | Returns `results` list and correct `count` |
| `OrderListAPITest` | `test_results_have_required_fields` | Each result has `id`, `status`, `created_at`, `total_items` |

---

## Author

**Mohammed Sowban**
Backend Developer
GitHub: [github.com/Sowban123](https://github.com/Sowban123)
LinkedIn: [linkedin.com/in/mohammed-sowban-928415239](https://linkedin.com/in/mohammed-sowban-928415239)
Email: mohammedsowban008@gmail.com
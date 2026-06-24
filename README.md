# Aforro Backend — Round 2 Assignment

A production-quality Django REST Framework backend demonstrating clean architecture, query optimization, Redis caching, Celery async tasks, and full Docker containerization.

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
│   ├── products/               # Category, Product models + admin
│   ├── stores/                 # Store, Inventory models + inventory API (Redis cached)
│   ├── orders/                 # Order, OrderItem models + creation/listing APIs + Celery task
│   ├── search/                 # Product search API + autocomplete API
│   └── common/
│       └── management/
│           └── commands/
│               └── seed_data.py  # Realistic seed command
├── config/
│   ├── __init__.py             # Celery app auto-discovery
│   ├── settings.py             # Main settings (env-driven)
│   ├── test_settings.py        # SQLite + locmem cache for tests
│   ├── celery.py               # Celery application config
│   ├── urls.py                 # Root URL conf
│   └── wsgi.py
├── tests/
│   └── test_api.py             # 17 tests covering all major flows
├── .env.example                # Environment variable template
├── Dockerfile
├── docker-compose.yml          # Django + PostgreSQL + Redis + Celery Worker + Beat
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
| `SECRET_KEY` | (insecure dev key) | Django secret key |
| `DEBUG` | `True` | Debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Allowed hosts |
| `DB_NAME` | `aforro_db` | PostgreSQL database name |
| `DB_USER` | `aforro_user` | PostgreSQL user |
| `DB_PASSWORD` | `aforro_pass` | PostgreSQL password |
| `DB_HOST` | `db` | PostgreSQL host (use `localhost` for local dev) |
| `DB_PORT` | `5432` | PostgreSQL port |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL for caching |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Redis URL for Celery results |
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
docker compose up --build
```

This starts five services:

| Service | Description |
|---|---|
| `db` | PostgreSQL 15 |
| `redis` | Redis 7 |
| `api` | Django API server on port 8000 (auto-runs migrations) |
| `celery_worker` | Celery worker — processes async tasks |
| `celery_beat` | Celery beat scheduler |

### Step 3 — Seed the database

```bash
docker compose exec api python manage.py seed_data
```

Generates:
- 12 realistic categories (Electronics, Fashion, Grocery, Home & Kitchen, Sports, Books, Beauty, Automotive, Office Supplies, Toys, and more)
- 1000 realistic products (iPhone 15, Samsung Galaxy S24, Nike Air Max 270, Levi's 511 Slim Jeans, etc.)
- 22 stores (Chennai Central Store, Bangalore Tech Store, Mumbai Retail Hub, etc.)
- 8000+ inventory records across all stores

### Step 4 — Access

| URL | Description |
|---|---|
| `http://localhost:8000/api/docs/` | Swagger UI (interactive API docs) |
| `http://localhost:8000/api/schema/` | Raw OpenAPI schema (YAML) |
| `http://localhost:8000/admin/` | Django admin |

### Admin Access

Create a superuser to access the Django admin panel:

```bash
docker compose exec api python manage.py createsuperuser
```

Then log in at `http://localhost:8000/admin/`.

### Useful Docker commands

```bash
# View logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f celery_worker

# Stop all services
docker compose down

# Stop and remove volumes (wipes database)
docker compose down -v

# Run Django shell
docker compose exec api python manage.py shell

# Create a Django superuser
docker compose exec api python manage.py createsuperuser

# Monitor active Celery tasks
docker compose exec celery_worker celery -A config inspect active
```

---

## Local Development (without Docker)

Requires PostgreSQL and Redis running locally.

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DB_HOST=localhost, REDIS_URL=redis://localhost:6379/0, etc.

# Run migrations
python manage.py migrate

# Seed data
python manage.py seed_data

# Start development server
python manage.py runserver
```

### Run tests (no Docker required — uses SQLite + in-memory cache)

```bash
python manage.py test tests --settings=config.test_settings -v 2
```

Expected output:
```
Ran 17 tests in 0.2s

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
    { "product_id": 42, "quantity_requested": 5 },
    { "product_id": 87, "quantity_requested": 2 }
  ]
}
```

**Rules:**
- If ALL items have sufficient stock → order is `CONFIRMED`, inventory is deducted
- If ANY item has insufficient stock or is missing → order is `REJECTED`, no stock deducted
- Entire operation wrapped in `transaction.atomic()` with `select_for_update()` on inventory rows

**Response — CONFIRMED (201):**
```json
{
  "id": 1,
  "store_id": 1,
  "store_name": "Chennai Central Store",
  "status": "CONFIRMED",
  "created_at": "2024-06-01T10:30:00Z",
  "items": [
    { "id": 1, "product_id": 42, "product_title": "iPhone 15", "quantity_requested": 5 },
    { "id": 2, "product_id": 87, "product_title": "Logitech MX Master 3", "quantity_requested": 2 }
  ],
  "total_items": 7
}
```

**Response — REJECTED (201):**
```json
{
  "order_id": 2,
  "status": "REJECTED",
  "created_at": "2024-06-01T10:31:00Z",
  "rejection_reasons": {
    "missing_products": [],
    "insufficient_stock": [
      { "product_id": 87, "available": 1, "requested": 2 }
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

Returns all orders for the store sorted by newest first. Includes `total_items` count per order (annotated — no N+1).

**Sample response:**
```json
{
  "count": 2,
  "results": [
    { "id": 2, "status": "REJECTED", "created_at": "2024-06-01T10:31:00Z", "total_items": 0 },
    { "id": 1, "status": "CONFIRMED", "created_at": "2024-06-01T10:30:00Z", "total_items": 7 }
  ]
}
```

---

### 3. Inventory Listing

```
GET /stores/<store_id>/inventory/
```

Returns inventory for the store sorted alphabetically by product title. Each record includes `inventory_id` (the inventory row's own ID), `product_id` (the related product's ID), product price, and category name. **Response is cached in Redis.**

**Sample response:**
```json
[
  {
    "inventory_id": 2281,
    "product_id": 38,
    "product_title": "Adidas Ultraboost 23",
    "product_price": "8999.00",
    "category_name": "Fashion",
    "quantity": 45
  },
  {
    "inventory_id": 2283,
    "product_id": 43,
    "product_title": "Apple Watch Series 9",
    "product_price": "41900.00",
    "category_name": "Electronics",
    "quantity": 12
  }
]
```

---

### 4. Product Search

```
GET /api/search/products/
```

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Keyword search across title, description, category name |
| `category` | string | Filter by category name (partial match) |
| `price_min` | number | Minimum price filter |
| `price_max` | number | Maximum price filter |
| `store_id` | integer | Filter by store; also adds `store_quantity` to each result |
| `in_stock` | `true` | Only return in-stock products (requires `store_id`) |
| `sort` | string | `price_asc`, `price_desc`, `newest`, `relevance` (default) |
| `page` | integer | Page number |
| `page_size` | integer | Results per page (default 20, max 100) |

**Sample request:**
```
GET /api/search/products/?q=samsung&category=electronics&price_min=20000&sort=price_asc&page=1
```

**Sample response:**
```json
{
  "count": 8,
  "next": "http://localhost:8000/api/search/products/?page=2",
  "previous": null,
  "page": 1,
  "total_pages": 1,
  "results": [
    {
      "id": 4,
      "title": "Samsung Galaxy S23 Ultra",
      "description": "Experience the best of Electronics with Samsung Galaxy S23 Ultra.",
      "price": "124999.00",
      "category_name": "Electronics",
      "created_at": "2024-06-01T00:00:00Z",
      "store_quantity": null
    }
  ]
}
```

---

### 5. Autocomplete

```
GET /api/search/suggest/?q=<query>
```

**Rules:**
- Minimum 3 characters required
- Returns up to 10 product title suggestions
- Prefix matches appear before general (contains) matches

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

**Error (< 3 characters):**
```json
{
  "error": "Minimum 3 characters required.",
  "suggestions": []
}
```

---

## Redis Caching

**Pattern:** Cache-aside on inventory listing.

- **Cache key:** `inventory_store_{store_id}`
- **TTL:** 300 seconds (configurable via `CACHE_TTL` env var)
- **Invalidation:** Explicitly deleted after every `CONFIRMED` order so stock levels are never stale

```python
# apps/orders/views.py — triggered after stock deduction
cache.delete(f'inventory_store_{store_id}')
```

To verify caching is working:
```bash
# First request — MISS, hits database
curl http://localhost:8000/stores/1/inventory/

# Second request — HIT, served from Redis
curl http://localhost:8000/stores/1/inventory/

# Inspect Redis keys directly
docker compose exec redis redis-cli keys "*inventory*"
```

---

## Celery Async Tasks

### `send_order_confirmation(order_id)`

Defined in `apps/orders/tasks.py`. Triggered automatically after every `CONFIRMED` order.

```python
# Called at the end of a successful order in apps/orders/views.py
send_order_confirmation.delay(order.id)
```

**Behaviour:**
- Fetches the full order with store + items in one optimized query
- Logs a formatted order confirmation (in production: send email/SMS/webhook)
- **Max retries:** 3 with 60-second delay between attempts
- **Runs on:** `celery_worker` Docker container

**Monitor tasks:**
```bash
# Check registered tasks
docker compose exec celery_worker celery -A config inspect registered

# Check active tasks
docker compose exec celery_worker celery -A config inspect active

# Check task history (via result backend)
docker compose exec celery_worker celery -A config inspect stats
```

---

## Data Models

```
Category          Product              Store
─────────         ────────────         ─────────
id                id                   id
name              title                name
                  description          location
                  price
                  category_id ──► Category

Inventory                    Order
─────────────                ─────────────────────
id                           id
store_id ──► Store           store_id ──► Store
product_id ──► Product       status (PENDING/CONFIRMED/REJECTED)
quantity                     created_at
UNIQUE(store, product)
                             OrderItem
                             ────────────────────
                             id
                             order_id ──► Order
                             product_id ──► Product
                             quantity_requested
```

---

## Query Optimization

| Technique | Where Used |
|---|---|
| `select_related('product__category')` | Inventory listing — joins product + category in one SQL query |
| `select_related('store')` | Order confirmation task |
| `prefetch_related('items__product')` | Order detail serialization |
| `annotate(total_items=Count('items'))` | Order listing — avoids N+1 for item counts |
| `annotate(store_quantity=Subquery(...))` | Search — pulls inventory quantity per store without extra loop |
| `select_for_update()` | Order creation — locks inventory rows during atomic transaction |
| `bulk_create(..., batch_size=500)` | Seed data — inserts thousands of rows efficiently |
| DB indexes | All FK columns + `(store, -created_at)` compound index on Order |

---

## Scalability Considerations

### Database
- All foreign keys are indexed; compound index on `(store, -created_at)` for order listing
- `select_for_update()` prevents inventory race conditions under concurrent requests
- `transaction.atomic()` guarantees all-or-nothing order processing

### Caching
- Per-store cache keys allow surgical invalidation without flushing unrelated stores
- TTL is env-configurable per deployment environment

### Search
- Current implementation uses `icontains` — correct for MVP scale
- For millions of rows: migrate to **PostgreSQL full-text search** (`SearchVector` + `SearchRank`) or **Elasticsearch**
- Autocomplete uses two separate indexed queries (prefix-first, then general) to ensure correct ranking without OR-query penalties

### Celery
- Worker and Beat run as separate containers — independently scalable
- Tasks retry with configurable delay; dead-letter handling can be added via Redis Streams
- Workers can be horizontally scaled: `docker compose up --scale celery_worker=4`

### Future Improvements
1. JWT authentication on all endpoints
2. Redis rate limiting on `/api/search/suggest/` (20 req/min/IP)
3. PostgreSQL full-text indexes for production-scale search
4. Cursor-based pagination for high-volume listing endpoints
5. Structured JSON logging with request IDs (e.g. structlog)
6. Health-check endpoint (`/health/`) for load balancer probes
7. API versioning (`/api/v1/`)

---

## Tests

17 tests covering all critical paths:

| Test | Coverage |
|---|---|
| `test_confirmed_order` | Successful order creation + inventory deduction |
| `test_rejected_order_insufficient_stock` | Rejection when stock is too low |
| `test_rejected_when_product_not_in_store` | Rejection when product not in store inventory |
| `test_inventory_listing` | Alphabetical sort, correct fields |
| `test_inventory_404_for_missing_store` | 404 on unknown store |
| `test_keyword_search` | icontains search on product title |
| `test_category_filter` | Category filter on search |
| `test_price_range_filter` | price_min / price_max filters |
| `test_pagination_metadata_present` | count, next, previous, total_pages |
| `test_sort_by_price_asc` | Ascending price sort |
| `test_sort_by_price_desc` | Descending price sort |
| `test_requires_minimum_3_chars` | Autocomplete 400 on short query |
| `test_prefix_matches_returned` | Prefix matches in autocomplete |
| `test_max_10_results` | Autocomplete cap at 10 |
| `test_general_icontains_included` | General matches in autocomplete |
| `test_order_list` | Store order listing count + results |
| `test_results_have_required_fields` | id, status, created_at, total_items |

Run all tests:
```bash
python manage.py test tests --settings=config.test_settings -v 2
```

---

## Author

**Mohammed Sowban**
Backend Developer Intern Candidate
GitHub: [github.com/Sowban123](https://github.com/Sowban123)
LinkedIn: [linkedin.com/in/mohammed-sowban-928415239](https://linkedin.com/in/mohammed-sowban-928415239)
Email: mohammedsowban008@gmail.com
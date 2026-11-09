# Reliable Commerce API

A Django REST Framework backend for an e-commerce application. The API includes product and category management, token authentication, customer carts, transactional checkout, inventory updates, and order lifecycle management.

## Features
- Token authentication and customer registration
- Public product/category browsing with manager-only writes
- Product validation, positive-price/non-negative-stock database constraints, and soft deletion
- Product pagination and GET rate limits
- Per-user shopping carts with quantity validation
- Transactional checkout with row locking, stock verification, immutable order-item price/name snapshots, and cart clearing
- Customer-owned order history/details and pending-order cancellation with inventory restoration
- Staff/order-manager order status transitions
- Django admin for catalog, carts, and orders
- SQLite for local development; PostgreSQL configuration for deployment

## Requirements
- Python 3.11+
- Dependencies in requirements.txt
- PostgreSQL for production deployments (SQLite is supported for local development)

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_product_permissions
python manage.py createsuperuser
python manage.py runserver
```

The API is available under /api/; Django admin is at /admin/.

## Environment variables
| Variable | Default | Purpose |
|---|---|---|
| DJANGO_DEBUG | true | Debug mode; set false in production |
| DJANGO_SECRET_KEY | local-only fallback when debug is true | Required when debug is false |
| DJANGO_ALLOWED_HOSTS | localhost,127.0.0.1 | Comma-separated hostnames |
| DB_ENGINE | sqlite | Set to postgresql for PostgreSQL |
| DB_NAME | reliable_commerce | PostgreSQL database |
| DB_USER | postgres | PostgreSQL user |
| DB_PASSWORD | empty | PostgreSQL password |
| DB_HOST | localhost | PostgreSQL host |
| DB_PORT | 5432 | PostgreSQL port |
| DJANGO_SECURE_SSL_REDIRECT | true in production | Set false only behind a trusted TLS-terminating proxy configured appropriately |
| DJANGO_HSTS_SECONDS | 31536000 | HSTS duration in production |

For production, provide a strong secret, explicit allowed hosts, PostgreSQL credentials, HTTPS termination, and persistent static-file hosting. Do not deploy with debug enabled.

## Authentication
Register a customer:
```http
POST /api/auth/register/
Content-Type: application/json

{"username":"customer1","email":"customer@example.com","password":"change-this-password"}
```
Obtain a token:
```http
POST /api/auth/token/
Content-Type: application/json

{"username":"customer1","password":"change-this-password"}
```
Send Authorization: Token <token> on authenticated requests.

## API endpoints
| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | /api/auth/register/ | Public | Register |
| POST | /api/auth/token/ | Public | Obtain auth token |
| GET | /api/categories/ | Public | List active categories |
| POST | /api/categories/ | Product manager | Create category |
| GET | /api/categories/{id}/ | Public | Category detail |
| PUT/PATCH/DELETE | /api/categories/{id}/ | Product manager | Manage category |
| GET | /api/products/ | Public | Paginated active products |
| POST | /api/products/ | Product manager | Create product |
| GET | /api/products/{id}/ | Public | Product detail |
| PUT/PATCH/DELETE | /api/products/{id}/ | Product manager | Update/soft-delete product |
| GET | /api/cart/ | Authenticated | Retrieve cart |
| GET/POST | /api/cart/items/ | Authenticated | List/add cart items |
| PATCH/DELETE | /api/cart/items/{id}/ | Cart owner | Update/remove own item |
| GET/POST | /api/orders/ | Authenticated | List own orders / checkout cart |
| GET | /api/orders/{id}/ | Order owner | Retrieve own order |
| POST | /api/orders/{id}/cancel/ | Order owner | Cancel pending order and restock |
| PATCH | /api/management/orders/{id}/status/ | Staff/order manager | Advance order status |

Product manager permissions are provided by Django's Product Managers group. Run python manage.py setup_product_permissions after migrations, then add trusted staff to that group. Order status management requires staff access or products.change_order.

## Checkout and inventory behavior
Checkout runs in a database transaction, locks the cart and relevant product rows, verifies active products and available stock, snapshots product names/prices into order items, decrements inventory, and empties the cart. If validation fails, the transaction rolls back. Pending-order cancellation restores the reserved quantities. Use PostgreSQL in production for effective row-level locking; SQLite is for development/testing.

## Tests and checks
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
```

## Deployment checklist
- Set DJANGO_DEBUG=false, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, and PostgreSQL variables.
- Configure HTTPS and verify proxy/SSL settings before enabling HSTS.
- Run migrations and collectstatic.
- Create a superuser and assign manager permissions.
- Configure a shared cache (for example Redis) if running multiple application instances; the built-in throttles use Django's configured cache.
- Configure backups, monitoring, and a production WSGI/ASGI server.

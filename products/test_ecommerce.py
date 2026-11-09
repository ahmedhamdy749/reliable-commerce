from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Cart, CartItem, Category, Order, OrderItem, Product


class ECommerceFlowTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="buyer",
            password="strong-test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-buyer",
            password="strong-test-password",
        )
        self.product = Product.objects.create(
            name="Mechanical Keyboard",
            price="125.00",
            stock=5,
        )
        self.client.force_authenticate(user=self.user)

    def test_register_and_obtain_token(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "new-customer",
                "email": "new@example.com",
                "password": "safe-password-123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        token_response = self.client.post(
            "/api/auth/token/",
            {
                "username": "new-customer",
                "password": "safe-password-123",
            },
            format="json",
        )
        self.assertEqual(token_response.status_code, 200)
        self.assertIn("token", token_response.data)

    def test_category_and_product_relationship(self):
        category = Category.objects.create(name="Keyboards", slug="keyboards")
        self.product.category = category
        self.product.save()
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["category_name"], "Keyboards")

    def test_cart_is_private_to_authenticated_user(self):
        Cart.objects.create(user=self.user)
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/cart/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["items"], [])

    def test_add_cart_item_and_checkout_decrements_stock(self):
        add_response = self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.pk, "quantity": 2},
            format="json",
        )
        self.assertEqual(add_response.status_code, 200)
        checkout_response = self.client.post("/api/orders/")
        self.product.refresh_from_db()
        self.assertEqual(checkout_response.status_code, 201)
        self.assertEqual(checkout_response.data["total_amount"], "250.00")
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(CartItem.objects.filter(cart__user=self.user).exists())
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().product_name, "Mechanical Keyboard")

    def test_checkout_rejects_insufficient_stock_without_partial_changes(self):
        self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.pk, "quantity": 6},
            format="json",
        )
        response = self.client.post("/api/orders/")
        self.product.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.product.stock, 5)
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_customer_cannot_read_another_customers_order(self):
        order = Order.objects.create(user=self.other_user, total_amount="10.00")
        response = self.client.get(f"/api/orders/{order.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_cancelling_pending_order_restores_stock(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        checkout = self.client.post("/api/orders/")
        self.assertEqual(checkout.status_code, 201)
        order_id = checkout.data["id"]
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

        cancel = self.client.post(f"/api/orders/{order_id}/cancel/")
        self.product.refresh_from_db()
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.data["status"], Order.Status.CANCELLED)
        self.assertEqual(self.product.stock, 5)

    def test_order_item_snapshot_survives_product_rename(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post("/api/orders/")
        self.product.name = "Renamed Keyboard"
        self.product.save()
        order_item = OrderItem.objects.get(order_id=response.data["id"])
        self.assertEqual(order_item.product_name, "Mechanical Keyboard")

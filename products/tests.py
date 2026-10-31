from rest_framework.test import APITestCase

from .models import Product


class ProductListAPITest(APITestCase):

    def test_returns_active_products(self):
        Product.objects.create(
            name="Active Keyboard",
            price="2500.00",
            stock=15,
            is_active=True,
        )

        Product.objects.create(
            name="Inactive Mouse",
            price="500.00",
            stock=0,
            is_active=False,
        )

        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Active Keyboard")

    def test_returns_empty_list_when_no_active_products(self):
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_product_creation_is_disabled(self):
        response = self.client.post(
            "/api/products/",
            {
                "name": "Gaming Mouse",
                "price": "750.00",
                "stock": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.count(), 0)
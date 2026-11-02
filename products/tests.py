from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from django.core.management import call_command
from .models import Product
from django.db import IntegrityError, transaction


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


    def test_database_rejects_zero_price(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    name="Invalid Product",
                    price="0.00",
                    stock=10,
                )

        self.assertEqual(Product.objects.count(), 0)   

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

    def test_authenticated_user_without_permission_cannot_create_product(self):
        User = get_user_model()

        user = User.objects.create_user(
            username="customer",
            password="test-password",
        )

        self.client.force_authenticate(user=user)

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

    def test_user_with_add_permission_passes_permission_check(self):
        User = get_user_model()

        user = User.objects.create_user(
            username="manager",
            password="test-password",
        )

        permission = Permission.objects.get(
            content_type__app_label="products",
            codename="add_product",
        )

        user.user_permissions.add(permission)

        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/products/",
            {
                "name": "Gaming Mouse",
                "price": "750.00",
                "stock": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.count(), 1)
    def test_product_manager_group_grants_add_permission(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="group_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/products/",
            {
                "name": "Gaming Mouse",
                "price": "750.00",
                "stock": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.count(), 1)  
    def test_product_creation_rejects_zero_price(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="price_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/products/",
            {
                "name": "Invalid Product",
                "price": "0.00",
                "stock": 10,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("price", response.data)
        self.assertEqual(Product.objects.count(), 0)   
    def test_patch_updates_only_the_provided_field(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="patch_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        product = Product.objects.create(
            name="Keyboard",
            price="1000.00",
            stock=20,
        )

        self.client.force_authenticate(user=user)

        response = self.client.patch(
            f"/api/products/{product.id}/",
            {
                "price": "1200.00",
            },
            format="json",
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(product.price, 1200)
        self.assertEqual(product.name, "Keyboard")
        self.assertEqual(product.stock, 20)      
    def test_patch_returns_404_for_nonexistent_product(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="missing_product_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        self.client.force_authenticate(user=user)

        response = self.client.patch(
            "/api/products/9999/",
            {"price": "1200.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)     




    def test_patch_returns_404_for_inactive_product(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="inactive_product_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        product = Product.objects.create(
            name="Old Keyboard",
            price="1000.00",
            stock=10,
            is_active=False,
        )

        self.client.force_authenticate(user=user)

        response = self.client.patch(
            f"/api/products/{product.id}/",
            {"price": "1200.00"},
            format="json",
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(product.price, 1000)
    def test_put_requires_all_required_fields(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="put_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        product = Product.objects.create(
            name="Keyboard",
            price="1000.00",
            stock=20,
        )

        self.client.force_authenticate(user=user)

        response = self.client.put(
            f"/api/products/{product.id}/",
            {
                "name": "Gaming Keyboard",
                "price": "1500.00",
            },
            format="json",
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertIn("stock", response.data)
        self.assertEqual(product.name, "Keyboard")
        self.assertEqual(product.price, 1000)
        self.assertEqual(product.stock, 20)    
    def test_put_replaces_all_product_fields(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="put_success_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        product = Product.objects.create(
            name="Keyboard",
            price="1000.00",
            stock=20,
        )

        self.client.force_authenticate(user=user)

        response = self.client.put(
            f"/api/products/{product.id}/",
            {
                "name": "Gaming Keyboard",
                "price": "1500.00",
                "stock": 35,
            },
            format="json",
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(product.name, "Gaming Keyboard")
        self.assertEqual(product.price, 1500)
        self.assertEqual(product.stock, 35)    
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
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"],"Active Keyboard",)

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
        self.assertEqual(response.data["results"], [])

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

    def test_delete_soft_deletes_product(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="delete_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        product = Product.objects.create(
            name="Old Keyboard",
            price="1000.00",
            stock=10,
        )

        self.client.force_authenticate(user=user)

        response = self.client.delete(
            f"/api/products/{product.id}/"
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 204)
        self.assertFalse(product.is_active)
        self.assertTrue(Product.objects.filter(id=product.id).exists())    



    def test_deleted_product_does_not_appear_in_product_list(self):
        product = Product.objects.create(
            name="Deleted Keyboard",
            price="1000.00",
            stock=10,
            is_active=False,
        )

        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        self.assertTrue(
            Product.objects.filter(id=product.id).exists()
        )   

    def test_deleted_product_cannot_be_updated(self):
        call_command("setup_product_permissions")

        user = get_user_model().objects.create_user(
            username="deleted_product_manager",
            password="test-password",
        )

        group = Group.objects.get(name="Product Managers")
        user.groups.add(group)

        product = Product.objects.create(
            name="Deleted Keyboard",
            price="1000.00",
            stock=10,
            is_active=False,
        )

        self.client.force_authenticate(user=user)

        response = self.client.patch(
            f"/api/products/{product.id}/",
            {"price": "1500.00"},
            format="json",
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(product.price, 1000)
        self.assertFalse(product.is_active)   

    def test_customer_without_permission_cannot_update_product(self):
        user = get_user_model().objects.create_user(
            username="customer_patch",
            password="test-password",
        )

        product = Product.objects.create(
            name="Keyboard",
            price="1000.00",
            stock=20,
        )

        self.client.force_authenticate(user=user)

        response = self.client.patch(
            f"/api/products/{product.id}/",
            {"price": "1500.00"},
            format="json",
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(product.price, 1000)
        self.assertEqual(product.name, "Keyboard")  

    def test_customer_without_permission_cannot_replace_product(self):
        user = get_user_model().objects.create_user(
            username="customer_put",
            password="test-password",
        )

        product = Product.objects.create(
            name="Keyboard",
            price="1000.00",
            stock=20,
        )

        self.client.force_authenticate(user=user)

        response = self.client.put(
            f"/api/products/{product.id}/",
            {
                "name": "New Keyboard",
                "price": "1500.00",
                "stock": 30,
            },
            format="json",
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(product.name, "Keyboard")
        self.assertEqual(product.price, 1000)
        self.assertEqual(product.stock, 20) 

    def test_customer_without_permission_cannot_delete_product(self):
        user = get_user_model().objects.create_user(
            username="customer_delete",
            password="test-password",
        )

        product = Product.objects.create(
            name="Keyboard",
            price="1000.00",
            stock=20,
        )

        self.client.force_authenticate(user=user)

        response = self.client.delete(
            f"/api/products/{product.id}/"
        )

        product.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertTrue(product.is_active)
        self.assertTrue(
            Product.objects.filter(id=product.id).exists()
        )       

    def test_change_permission_does_not_grant_delete_permission(self):
        user = get_user_model().objects.create_user(
            username="editor_only",
            password="test-password",
        )

        permission = Permission.objects.get(
            content_type__app_label="products",
            codename="change_product",
        )
        user.user_permissions.add(permission)

        product = Product.objects.create(
            name="Keyboard",
            price="1000.00",
            stock=20,
        )

        self.client.force_authenticate(user=user)

        patch_response = self.client.patch(
            f"/api/products/{product.id}/",
            {"price": "1200.00"},
            format="json",
        )

        delete_response = self.client.delete(
            f"/api/products/{product.id}/"
        )

        product.refresh_from_db()

        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(product.price, 1200)
        self.assertTrue(product.is_active)       
    def test_first_page_returns_20_products(self):
        Product.objects.bulk_create([
            Product(
                name=f"Product {i}",
                price=100 + i,
                stock=10,
            )
            for i in range(27)
        ])

        response = self.client.get("/api/products/?page=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 27)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_second_page_returns_remaining_7_products(self):
        Product.objects.bulk_create([
            Product(
                name=f"Product {i}",
                price=100 + i,
                stock=10,
            )
            for i in range(27)
        ])

        response = self.client.get("/api/products/?page=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 27)
        self.assertEqual(len(response.data["results"]), 7)
        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

    def test_nonexistent_page_returns_404(self):
        Product.objects.bulk_create([
            Product(
                name=f"Product {i}",
                price=100 + i,
                stock=10,
            )
            for i in range(27)
        ])

        response = self.client.get("/api/products/?page=3")

        self.assertEqual(response.status_code, 404)

    def test_inactive_products_are_excluded_from_pagination(self):
        Product.objects.bulk_create([
            Product(
                name=f"Active Product {i}",
                price=100 + i,
                stock=10,
                is_active=True,
            )
            for i in range(25)
        ])

        Product.objects.bulk_create([
            Product(
                name=f"Inactive Product {i}",
                price=200 + i,
                stock=10,
                is_active=False,
            )
            for i in range(5)
        ])

        response = self.client.get("/api/products/?page=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 5)

        for product in response.data["results"]:
            self.assertNotIn("Inactive", product["name"])
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from products.models import Order, Product


class Command(BaseCommand):
    help = "Create product and order manager groups and assign permissions"

    def handle(self, *args, **options):
        product_group, product_created = Group.objects.get_or_create(
            name="Product Managers"
        )
        product_type = ContentType.objects.get_for_model(Product)
        product_permissions = Permission.objects.filter(
            content_type=product_type,
            codename__in=(
                "add_product",
                "change_product",
                "delete_product",
                "view_product",
            ),
        )
        product_group.permissions.set(product_permissions)

        order_group, order_created = Group.objects.get_or_create(
            name="Order Managers"
        )
        order_type = ContentType.objects.get_for_model(Order)
        order_permissions = Permission.objects.filter(
            content_type=order_type,
            codename__in=("change_order", "view_order"),
        )
        order_group.permissions.set(order_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                "Permissions configured: "
                f"Product Managers ({product_permissions.count()} permissions, "
                f"{'created' if product_created else 'updated'}); "
                f"Order Managers ({order_permissions.count()} permissions, "
                f"{'created' if order_created else 'updated'})."
            )
        )

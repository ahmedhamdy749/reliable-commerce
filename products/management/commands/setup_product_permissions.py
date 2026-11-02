from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from products.models import Product


class Command(BaseCommand):
    help = "Create Product Managers group and assign permissions"

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(
            name="Product Managers"
        )

        content_type = ContentType.objects.get_for_model(Product)

        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=[
                "add_product",
                "change_product",
                "delete_product",
                "view_product",
            ],
        )

        group.permissions.set(permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f"Product Managers group {'created' if created else 'updated'} "
                f"with {permissions.count()} permissions."
            )
        )
from django.db import models
from django.db.models import Q

# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name="product_price_must_be_positive",
            ),
        ]

    def __str__(self):
        return self.name

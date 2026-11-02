
from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    stock = serializers.IntegerField(min_value=0)
    class Meta:
        model = Product
        fields = ["id", "name", "price", "stock"]
        read_only_fields = ["id"]
        

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than zero."
            )
        return value

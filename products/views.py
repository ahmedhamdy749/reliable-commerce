
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Product
from .serializers import ProductSerializer


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def product_list(request):
    if request.method == "GET":
        products = Product.objects.filter(is_active=True)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    return Response(
        {"detail": "Product creation is not enabled yet."},
        status=status.HTTP_403_FORBIDDEN,
    )

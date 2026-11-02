from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Product
from .serializers import ProductSerializer
from .permissions import IsProductManager


@api_view(["GET", "POST"])
@permission_classes([IsProductManager])
def product_list(request):

    if request.method == "GET":
        products = Product.objects.filter(is_active=True)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
    if request.method == "POST":
        serializer = ProductSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([IsProductManager])
def product_detail(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk,
        is_active=True,
    )
    if request.method == "DELETE":
        product.is_active = False
        product.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ProductSerializer(
        product,
        data=request.data,
        partial=(request.method == "PATCH"),
        
)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )
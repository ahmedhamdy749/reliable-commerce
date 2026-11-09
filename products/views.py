from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem, Category, Order, OrderItem, Product
from .pagination import ProductPagination
from .permissions import IsOrderManager, IsProductManager
from .serializers import (
    CartItemSerializer,
    CartItemWriteSerializer,
    CartSerializer,
    CategorySerializer,
    OrderSerializer,
    ProductSerializer,
    RegisterSerializer,
)
from .throttles import GetAnonRateThrottle, GetUserRateThrottle


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsProductManager]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsProductManager]
    http_method_names = ["get", "put", "patch", "delete"]


@api_view(["GET", "POST"])
@permission_classes([IsProductManager])
@throttle_classes([GetAnonRateThrottle, GetUserRateThrottle])
def product_list(request):
    if request.method == "GET":
        products = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .order_by("id")
        )
        paginator = ProductPagination()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = ProductSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsProductManager])
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("category"),
        pk=pk,
        is_active=True,
    )
    if request.method == "GET":
        return Response(ProductSerializer(product).data)
    if request.method == "DELETE":
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ProductSerializer(
        product,
        data=request.data,
        partial=(request.method == "PATCH"),
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart = Cart.objects.prefetch_related("items__product").get(pk=cart.pk)
        return Response(CartSerializer(cart).data)


class CartItemListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related("product").order_by("id")
        return Response(CartItemSerializer(items, many=True).data)

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        if quantity > product.stock:
            raise ValidationError({"quantity": "Requested quantity exceeds available stock."})

        item, _ = CartItem.objects.update_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        return Response(
            CartItemSerializer(item).data,
            status=status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        item = get_object_or_404(
            CartItem.objects.select_related("product", "cart"),
            pk=pk,
            cart__user=request.user,
        )
        serializer = CartItemWriteSerializer(
            item,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data.get("product", item.product)
        quantity = serializer.validated_data.get("quantity", item.quantity)
        if product != item.product and CartItem.objects.filter(
            cart=item.cart, product=product
        ).exclude(pk=item.pk).exists():
            raise ValidationError({"product_id": "This product is already in your cart."})
        if quantity > product.stock:
            raise ValidationError({"quantity": "Requested quantity exceeds available stock."})
        item.product = product
        item.quantity = quantity
        item.save(update_fields=["product", "quantity", "updated_at"])
        return Response(CartItemSerializer(item).data)

    def delete(self, request, pk):
        item = get_object_or_404(
            CartItem,
            pk=pk,
            cart__user=request.user,
        )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items")
            .order_by("-created_at", "-id")
        )
        return Response(OrderSerializer(orders, many=True).data)

    @transaction.atomic
    def post(self, request):
        cart = get_object_or_404(
            Cart.objects.select_for_update(),
            user=request.user,
        )
        cart_items = list(
            cart.items.select_related("product").order_by("product_id")
        )
        if not cart_items:
            raise ValidationError({"cart": "Your cart is empty."})

        product_ids = [item.product_id for item in cart_items]
        locked_products = {
            product.pk: product
            for product in Product.objects.select_for_update()
            .filter(pk__in=product_ids, is_active=True)
            .order_by("pk")
        }

        total = Decimal("0.00")
        for item in cart_items:
            product = locked_products.get(item.product_id)
            if product is None:
                raise ValidationError(
                    {"product": f"{item.product.name} is no longer available."}
                )
            if item.quantity > product.stock:
                raise ValidationError(
                    {"stock": f"Insufficient stock for {product.name}."}
                )
            total += product.price * item.quantity

        order = Order.objects.create(user=request.user, total_amount=total)
        order_items = []
        for item in cart_items:
            product = locked_products[item.product_id]
            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=item.quantity,
                )
            )
            product.stock -= item.quantity
            product.save(update_fields=["stock", "updated_at"])

        OrderItem.objects.bulk_create(order_items)
        cart.items.all().delete()
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.prefetch_related("items"),
            pk=pk,
            user=request.user,
        )
        return Response(OrderSerializer(order).data)


class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_for_update().prefetch_related("items"),
            pk=pk,
            user=request.user,
        )
        if order.status != Order.Status.PENDING:
            raise ValidationError("Only pending orders can be cancelled.")

        for item in order.items.all():
            if item.product_id:
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.stock += item.quantity
                product.save(update_fields=["stock", "updated_at"])

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order).data)


class OrderStatusUpdateView(APIView):
    permission_classes = [IsOrderManager]

    @transaction.atomic
    def patch(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_for_update().prefetch_related("items"),
            pk=pk,
        )
        new_status = request.data.get("status")
        valid_statuses = {choice for choice, _ in Order.Status.choices}
        if new_status not in valid_statuses:
            raise ValidationError({"status": "Invalid order status."})

        allowed_transitions = {
            Order.Status.PENDING: {Order.Status.PROCESSING, Order.Status.CANCELLED},
            Order.Status.PROCESSING: {Order.Status.SHIPPED, Order.Status.CANCELLED},
            Order.Status.SHIPPED: {Order.Status.DELIVERED},
            Order.Status.DELIVERED: set(),
            Order.Status.CANCELLED: set(),
        }
        if new_status not in allowed_transitions[order.status]:
            raise ValidationError({"status": "This status transition is not allowed."})

        if new_status == Order.Status.CANCELLED:
            for item in order.items.all():
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.stock += item.quantity
                product.save(update_fields=["stock", "updated_at"])

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order).data)

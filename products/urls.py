from django.urls import path

from .views import (
    CancelOrderView,
    CartItemDetailView,
    CartItemListCreateView,
    CartView,
    CategoryDetailView,
    CategoryListCreateView,
    OrderDetailView,
    OrderListCreateView,
    OrderStatusUpdateView,
    RegisterView,
    product_detail,
    product_list,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path("products/", product_list, name="product-list"),
    path("products/<int:pk>/", product_detail, name="product-detail"),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemListCreateView.as_view(), name="cart-item-list"),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/cancel/", CancelOrderView.as_view(), name="order-cancel"),
    path(
        "management/orders/<int:pk>/status/",
        OrderStatusUpdateView.as_view(),
        name="order-status-update",
    ),
]

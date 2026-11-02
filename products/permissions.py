from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsProductManager(BasePermission):

    def has_permission(self, request, view):

        if request.method in SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        permission_map = {
            "POST": "products.add_product",
            "PUT": "products.change_product",
            "PATCH": "products.change_product",
            "DELETE": "products.delete_product",
        }

        permission = permission_map.get(request.method)

        if permission is None:
            return False

        return request.user.has_perm(permission)
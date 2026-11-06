from rest_framework.throttling import (
    AnonRateThrottle,
    UserRateThrottle,
)


class GetAnonRateThrottle(AnonRateThrottle):

    def allow_request(self, request, view):
        if request.method != "GET":
            return True

        return super().allow_request(request, view)


class GetUserRateThrottle(UserRateThrottle):

    def allow_request(self, request, view):
        if request.method != "GET":
            return True

        return super().allow_request(request, view)    
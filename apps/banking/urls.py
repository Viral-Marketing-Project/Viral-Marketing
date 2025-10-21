# apps/banking/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_accounts import AccountViewSet
from .views_transactions import TransactionViewSet

app_name = "banking"

router = DefaultRouter()
router.register(r"accounts", AccountViewSet, basename="account")
router.register(r"transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("", include(router.urls)),
]

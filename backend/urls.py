from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CartView, UserView, OrderView, ProductView, OrderItemView, WishlistView,
    RegisterView, Checkout, CustomLoginView, ForgotPasswordView, ResetPasswordView,
    create_razorpay_order, verify_razorpay_payment,
    AdminDashboardView, AdminProductsView, AdminOrderView ,BlockUnblockUserView
)


router = DefaultRouter()
router.register(r'cart', CartView, basename='cart')
router.register(r'users', UserView, basename='users')
router.register(r'order-items', OrderItemView, basename='order-items')
router.register(r'orders', OrderView, basename='orders')
router.register(r'products', ProductView, basename='products')
router.register(r'wishlist', WishlistView, basename='wishlist')

urlpatterns = [
    
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    
    path('cart/checkout/', Checkout, name='checkout'),
    path('create-razorpay-order/', create_razorpay_order, name='create-razorpay-order'),
    path('verify-razorpay-payment/', verify_razorpay_payment, name='verify-razorpay-payment'),

    
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('manage-products/', AdminProductsView.as_view(), name='manage-products-list'),
    path('manage-products/<int:pk>/', AdminProductsView.as_view(), name='manage-products-detail'),
    path('manage-orders/', AdminOrderView.as_view()),            
    path('manage-orders/<int:pk>/', AdminOrderView.as_view()),
    path('block-user/<int:user_id>/', BlockUnblockUserView.as_view(), name='block-unblock-user'),

    
    path('', include(router.urls)),
]

from decimal import Decimal
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from rest_framework import generics, status, viewsets
from django.contrib.auth.tokens import default_token_generator
from rest_framework.decorators import api_view, permission_classes
from .models import Cart, Product, Wishlist, Order, OrderItem, CustomUser
from .serializer import (CartSerializer, ProductSerializer, WishlistSerializer, OrderItemSerializer, OrderSerializer, UserSerializer, RegisterSerializer)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated 
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import BasePermission 
from rest_framework.response import Response
from rest_framework.views import APIView
from .pagination import AdminPagination
from django.conf import settings
import razorpay


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and 
            user.is_authenticated and 
            (getattr(user, 'role', '').lower() == 'admin' or user.is_staff)
        )


class CustomLoginView(APIView):
    permission_classes = [AllowAny] 
    
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "Account is inactive. Please contact support."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save(is_active=True, is_verified=True)

        try:
            send_mail(
                subject="🎉 Welcome to Olea!",
                message=(
                    f"Hi {user.username},\n\n"
                    "Your account has been created successfully!\n"
                    "We're thrilled to have you as part of our community.\n\n"
                    "You can now log in and start exploring our platform.\n\n"
                    "Best regards,\n"
                    "The Olea Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print("Email sending failed:", e)

        return user

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Account created successfully! A welcome email has been sent.",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "role": user.role,  # ✅ ADDED: Include role here too
                },
            },
            status=status.HTTP_201_CREATED,
        )


class UserView(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [AllowAny]
        elif self.action in ["retrieve", "update", "partial_update"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=user.id)


class ProductView(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]


class CartView(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data['product']
        quantity = serializer.validated_data.get('quantity', 1)

       
        cart_item, created = Cart.objects.get_or_create(
            user=user, 
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()


class WishlistView(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data['product']

        
        wishlist_item, created = Wishlist.objects.get_or_create(user=user, product=product)
        if not created:
            pass


class OrderView(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderItemView(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"detail": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User with this email does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        otp = user.generate_otp()
        send_mail(
            subject="Password Reset OTP",
            message=f"Your OTP for password reset is: {otp}\n\nThis OTP will expire in 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {"message": "OTP sent to your email for password reset", "email": user.email},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not email or not otp or not new_password:
            return Response(
                {"detail": "Email, OTP and new password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.otp != otp:
            return Response(
                {"detail": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.otp = None
        user.save()

        return Response(
            {"message": "Password reset successfully! You can now login with your new password."},
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def Checkout(request):
    user = request.user
    cart_items = Cart.objects.filter(user=user)

    if not cart_items.exists():
        return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

    subtotal = Decimal(0)
    for cart_item in cart_items:
        product = cart_item.product
        quantity = cart_item.quantity
        subtotal += product.price * quantity

    shipping = Decimal(50)
    total_amount = subtotal + shipping

    # Create order
    order = Order.objects.create(
        user=user,
        order_id=get_random_string(length=10).upper(),
        subtotal=subtotal,
        shipping=shipping,
        total_amount=total_amount,
        payment_method=request.data.get("payment_method", "cash"),
        status='pending',
        payment_status='pending'
    )

    # Create order items and link to order
    for cart_item in cart_items:
        order_item = OrderItem.objects.create(
            order=order, 
            product=cart_item.product,
            quantity=cart_item.quantity,
            price=cart_item.product.price
        )

    # Clear cart
    cart_items.delete()

    serializer = OrderSerializer(order)
    return Response({
        "message": "Order created successfully",
        "order": serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    user = request.user
    payment_method = request.data.get("payment_method", "card")

    cart_items = Cart.objects.filter(user=user)
    if not cart_items.exists():
        return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

    subtotal = Decimal(0)
    for item in cart_items:
        subtotal += item.product.price * item.quantity

    shipping = Decimal(50)
    total_amount = subtotal + shipping

   
    if payment_method == "cash":
        try:
            # Create order first
            order = Order.objects.create(
                user=user,
                order_id=get_random_string(length=10).upper(),
                subtotal=subtotal,
                shipping=shipping,
                total_amount=total_amount,
                payment_method="cash",
                status="pending",
                payment_status="pending",
            )

            # Create order items and link them to the order
            for item in cart_items:
                order_item = OrderItem.objects.create(
                    order=order,  # Fixed: Link to order
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
                

            # Clear cart
            cart_items.delete()

            serializer = OrderSerializer(order)
            return Response({
                "message": "Order placed successfully!", 
                "order_id": order.order_id,
                "order": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Failed to create order: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    
    elif payment_method in ["upi", "card"]:
        amount_paise = int(total_amount * 100) 
        
        try:
            razorpay_order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1, 
            })
            
            return Response({
                "razorpay_order_id": razorpay_order["id"],
                "amount": float(total_amount),
                "amount_paise": amount_paise,
                "currency": "INR",
                "key_id": settings.RAZORPAY_KEY_ID,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to create Razorpay order: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    else:
        return Response(
            {"error": "Invalid payment method"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_razorpay_payment(request):
    user = request.user
    razorpay_payment_id = request.data.get("razorpay_payment_id")
    razorpay_order_id = request.data.get("razorpay_order_id")
    razorpay_signature = request.data.get("razorpay_signature")

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return Response(
            {"error": "Missing payment verification data"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify signature
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        return Response(
            {"error": "Payment verification failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Payment successful → create DB order
    cart_items = Cart.objects.filter(user=user)
    if not cart_items.exists():
        return Response(
            {"error": "Cart items not found"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    subtotal = sum([item.product.price * item.quantity for item in cart_items])
    shipping = Decimal(50)
    total_amount = subtotal + shipping

    try:
        # Create order first
        order = Order.objects.create(
            user=user,
            order_id=get_random_string(length=10).upper(),
            subtotal=subtotal,
            shipping=shipping,
            total_amount=total_amount,
            payment_method="card",
            status="processing",
            payment_status="paid",
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id
        )

        # Create order items and link them to the order
        for item in cart_items:
            order_item = OrderItem.objects.create(
                order=order,  # Fixed: Link to order
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        # Clear cart
        cart_items.delete()

        serializer = OrderSerializer(order)
        return Response({
            "message": "Payment successful & order created!", 
            "order_id": order.order_id,
            "order": serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to create order: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Fetch all data
        orders = Order.objects.all().order_by('-created_at')
        products = Product.objects.all()
        users = CustomUser.objects.all()

        # Calculate total revenue
        total_revenue = sum([float(order.total_amount or 0) for order in orders])

        # Sales data grouped by date
        sales_dict = {}
        category_count = {}

        for order in orders:
            date_str = order.created_at.strftime("%Y-%m-%d")
            sales_dict[date_str] = sales_dict.get(date_str, 0) + float(order.total_amount or 0)

            for item in order.items.all():
                category = item.product.category if item.product.category else "Uncategorized"
                category_count[category] = category_count.get(category, 0) + item.quantity

        sales_data = [{"date": date, "total": total} for date, total in sales_dict.items()]
        category_data = [{"name": name, "value": value} for name, value in category_count.items()]

        # Recent activity (latest 4 orders)
        recent_activity = [
            {
                "id": idx + 1,
                "type": "order",
                "message": f"New order from {order.user.username if order.user else 'Customer'}",
                "time": order.created_at.strftime("%H:%M:%S"),
                "amount": f"₹{order.total_amount or 0}"
            }
            for idx, order in enumerate(orders[:4])
        ]

        # Serialize users and products
        users_serializer = UserSerializer(users, many=True)
        products_serializer = ProductSerializer(products, many=True)

        # Return consolidated response
        return Response({
            "totalRevenue": float(total_revenue),
            "totalOrders": orders.count(),
            "totalUsers": users.count(),
            "totalProducts": products.count(),
            "salesData": sales_data,
            "categoryData": category_data,
            "recentActivity": recent_activity,
            "orders": OrderSerializer(orders, many=True).data,
            "users": users_serializer.data,
            "products": products_serializer.data
        })
    

class AdminProductsView(APIView):
    permission_classes = [IsAdminUser, IsAdminRole]

    def get(self, request):
        products = Product.objects.all().order_by('-created_at')
        paginator = AdminPagination()
        paginated_products = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(paginated_products, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data['totalProducts'] = products.count()
        return response

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Product created successfully", "product": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Product updated successfully", "product": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Product partially updated", "product": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response({"message": "Product deleted successfully"}, status=status.HTTP_200_OK)


class AdminOrderView(APIView):
    permission_classes = [IsAdminUser, IsAdminRole]

    def get(self, request, pk=None):
        if pk:
            order = get_object_or_404(Order.objects.select_related('user').prefetch_related('items'), pk=pk)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        else:
            orders = Order.objects.all().select_related('user').prefetch_related('items').order_by('-created_at')
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)

    def patch(self, request, pk=None):
        order = get_object_or_404(Order.objects.select_related('user').prefetch_related('items'), pk=pk)
        status_value = request.data.get("status")
        if not status_value:
            return Response({"error": "Status field is required."}, status=400)

        order.status = status_value
        order.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    

class BlockUnblockUserView(APIView):
    permission_classes = [IsAdminUser, IsAdminRole]

    def patch(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({"error": "The 'is_active' field is required."}, status=400)

        if not isinstance(is_active, bool):
            return Response({"error": "'is_active' must be a boolean value."}, status=400)

        if user.is_staff:
            return Response({"error": "Admin users cannot be blocked."}, status=403)

        user.is_active = is_active
        user.save()

        if not is_active:
            try:
                send_mail(
                    subject="Account Blocked",
                    message=(
                        f"Hi {user.username},\n\n"
                        "Your account has been blocked by the admin. "
                        "Please contact support if you think this is a mistake."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email to {user.email}: {e}")

        return Response({
            "status": "success",
            "user_id": user.id,
            "is_active": user.is_active,
            "message": "User has been unblocked." if is_active else "User has been blocked."
        })

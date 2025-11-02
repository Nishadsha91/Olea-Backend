from rest_framework import serializers
from .models import Cart, Product, Wishlist, Order, OrderItem, CustomUser
from django.contrib.auth.hashers import make_password


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'phone', 'password', 'terms')
    
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            phone=validated_data.get('phone', ''),
            password=validated_data['password'],
            terms=validated_data.get('terms', False),
            is_active=True,  
            is_verified=True  
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta: 
        model = CustomUser
        fields = ['id', 'username', 'email', 'phone', 'role', 'terms', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data.get('password'))
        return super().create(validated_data)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        source='product'
    )

    class Meta:
        model = Cart
        fields = ['id', 'user', 'product', 'product_id', 'quantity', 'created_at', 'updated_at']
        extra_kwargs = {'user': {'read_only': True}}


class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        source='product'
    )
    
    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'product', 'product_id', 'created_at', 'updated_at']
        extra_kwargs = {'user': {'read_only': True}}


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), 
        source='product', 
        write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_id', 'quantity', 'price', 'created_at', 'updated_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)  
    user = UserSerializer(read_only=True)   
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source='user',
        write_only=True,
        required=False
    )

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'user', 'user_id', 'items', 'subtotal', 'shipping', 
            'total_amount', 'payment_method', 'status', 'payment_status', 
            'razorpay_payment_id', 'razorpay_order_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['order_id', 'created_at', 'updated_at']


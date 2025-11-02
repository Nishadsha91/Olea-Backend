from django.contrib import admin
from .models import Cart,Product,Wishlist,Order,OrderItem,CustomUser

# Register your models here.

admin.site.register(Cart),
admin.site.register(Product),
admin.site.register(Wishlist),
admin.site.register(OrderItem),
admin.site.register(Order),
admin.site.register(CustomUser),
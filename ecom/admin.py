# from django.contrib import admin
# from .models import Customer,Product,Orders,Feedback, Brand, Category
# Register your models here.
# class CustomerAdmin(admin.ModelAdmin):
#     pass
# admin.site.register(Customer, CustomerAdmin)

# class ProductAdmin(admin.ModelAdmin):
#     list_display = ('name', 'brand', 'category', 'price', 'availability', 'offer')
#     list_filter = ('brand', 'category', 'availability', 'offer')
# admin.site.register(Product, ProductAdmin)

# class OrderAdmin(admin.ModelAdmin):
#     pass
# admin.site.register(Orders, OrderAdmin)

# class FeedbackAdmin(admin.ModelAdmin):
#     pass
# admin.site.register(Feedback, FeedbackAdmin)

# class BrandAdmin(admin.ModelAdmin):
#     list_display = ['id', 'name']
# admin.site.register(Brand, BrandAdmin)

# class CategoryAdmin(admin.ModelAdmin):
#     list_display = ['id', 'name', 'parent']
# admin.site.register(Category, CategoryAdmin)
# Register your models here.

from django.contrib import admin
from .models import Customer, Product, Orders, Feedback, Brand, Category

class CustomerAdmin(admin.ModelAdmin):
    pass
admin.site.register(Customer, CustomerAdmin)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'availability', 'offer')
    list_filter = ('brand', 'category', 'availability', 'offer')
admin.site.register(Product, ProductAdmin)

class OrderAdmin(admin.ModelAdmin):
    pass
admin.site.register(Orders, OrderAdmin)

class FeedbackAdmin(admin.ModelAdmin):
    pass
admin.site.register(Feedback, FeedbackAdmin)

class BrandAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
admin.site.register(Brand, BrandAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'parent']
admin.site.register(Category, CategoryAdmin)


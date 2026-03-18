from django.urls import path
from . import views

urlpatterns = [
    path('shop/<slug:category_slug>/', views.category_products_view, name='category-products'),
    path('product/<int:pk>/', views.product_detail_view, name='product-detail'),

    path('manage-category/', views.manage_category_view, name='manage_category'),
    path('manage-brand/', views.manage_brand_view, name='manage_brand'),
    path('manage-product/', views.manage_product_view, name='manage_product'),
    path('admin-panel/delete-category/<int:pk>/', views.admin_delete_category_view, name='admin_delete_category'),
    path('admin-panel/delete-brand/<int:pk>/', views.admin_delete_brand_view, name='admin_delete_brand'),
    path('delete-product/<int:pk>/', views.delete_product_view, name='delete-product'),

]

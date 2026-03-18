# urls.py 
from django.urls import include
from django.contrib import admin
from django.urls import path
from ecom import views
from django.views.generic import TemplateView

from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', include('ecom.urls')),

    # Public views
    path('', views.home_view, name='homepage'),
    path('afterlogin', views.afterlogin_view, name='afterlogin'),


    path('demo', views.demo_view, name='demo'),

    path('logout', views.logout_user, name='logout'),
    path('logout-success', TemplateView.as_view(template_name='ecom/logout.html'), name='logout-success'),

    path('aboutus', views.aboutus_view, name='aboutus'),
    path('contactus', views.contactus_view, name='contactus'),
    path('search', views.search_view, name='search'),
    path('send-feedback', views.send_feedback_view, name='send-feedback'),
    path('view-feedback', views.view_feedback_view, name='view-feedback'),
    path('shop', views.shop_view, name='shop'),
    path('shop/<slug:category_slug>/', views.category_products_view, name='category-products'),

    #admin add product
    path('admin-add-products', views.admin_add_product_view, name='admin-add-products'),

    # Admin authentication and dashboard
    path('adminclick', views.adminclick_view, name='adminclick'),
    path('adminlogin', LoginView.as_view(template_name='ecom/adminlogin.html'), name='adminlogin'),
    path('admin-dashboard', views.admin_dashboard_view, name='admin-dashboard'),

    # Admin customer management
    path('view-customer', views.view_customer_view, name='view-customer'),
    path('delete-customer/<int:pk>', views.delete_customer_view, name='delete-customer'),
    path('update-customer/<int:pk>', views.update_customer_view, name='update-customer'),

    # Admin product management
    path('admin-products', views.admin_products_view, name='admin-products'),
    path('admin-add-product', views.admin_add_product_view, name='admin-add-product'),
    path('delete-product/<int:pk>', views.delete_product_view, name='delete-product'),
    path('update-product/<int:pk>', views.update_product_view, name='update-product'),

    # Admin order management
    path('admin-view-booking', views.admin_view_booking_view, name='admin-view-booking'),
    path('delete-order/<int:pk>', views.delete_order_view, name='delete-order'),
    path('update-order/<int:pk>', views.update_order_view, name='update-order'),

    # Customer authentication and profile
    path('customersignup', views.customer_signup_view),
    path('customerlogin', LoginView.as_view(template_name='ecom/customerlogin.html'), name='customerlogin'),
    path('customer-home', views.customer_home_view, name='customer-home'),
    path('my-order', views.my_order_view, name='my-order'),
    path('my-profile', views.my_profile_view, name='my-profile'),
    path('edit-profile', views.edit_profile_view, name='edit-profile'),
    path('customersignup', views.customer_signup_view, name='customersignup'),
    path('shop/', views.shop_view, name='shop'),

    path('download-invoice/<int:orderID>/<int:productID>', views.download_invoice_view, name='download-invoice'),

    # Cart functionality with quantity support
    path('add-to-cart/<int:pk>/', views.add_to_cart_view, name='add-to-cart'),
    path('cart/', views.cart_view, name='cart'),
    path('remove-from-cart/<int:pk>/', views.remove_from_cart_view, name='remove-from-cart'),
    path('increase-cart-item/<int:pk>/', views.increase_cart_item_view, name='increase-cart-item'),
    path('delete-from-cart/<int:pk>/', views.delete_from_cart_view, name='delete-from-cart'),


    # Address and checkout
        path('customer-address/', views.customer_address_view, name='customer_address'),
    path('payment-success', views.payment_success_view, name='payment-success'),


    path('track-order/', views.track_order, name='track_order'),
    path("chatbot/", views.chatbot, name="chatbot"),

    path('pay/', views.esewa_payment_view, name='esewa_payment'),
    path('esewa/success/', views.esewa_success_view, name='esewa_success'),
    path('esewa/failure/', views.esewa_failure_view, name='esewa_failure'),
    path('product/<int:pk>/', views.product_detail_view, name='product-detail'),


]
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# Standard libraries
import os
import io
import uuid
import json
import hmac
import base64
import hashlib

# Third-party libraries
import requests
import openai
import pandas as pd
from xhtml2pdf import pisa
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Django core
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.template.loader import get_template
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt

#  app imports
from . import forms, models
from .models import Product, Category


ESEWA_SECRET_KEY = settings.ESEWA_SECRET_KEY
ESEWA_PRODUCT_CODE = settings.ESEWA_PRODUCT_CODE
ESEWA_BASE_URL = 'https://uat.esewa.com.np'  



# -------------------------
# Category, Brand, Product Management Views
# -------------------------
@login_required(login_url='adminlogin')
def manage_category_view(request):
    categories = models.Category.objects.all()
    form = forms.CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('manage_category')
    return render(request, 'ecom/manage_category.html', {'form': form, 'categories': categories})

@login_required(login_url='adminlogin')
def admin_delete_category_view(request, pk):
    category = models.Category.objects.get(id=pk)
    category.delete()
    messages.success(request, "Category deleted successfully.")
    return redirect('manage_category')


@login_required(login_url='adminlogin')
def manage_brand_view(request):
    brands = models.Brand.objects.all()
    form = forms.BrandForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('manage_brand')
    return render(request, 'ecom/manage_brand.html', {'form': form, 'brands': brands})

@login_required(login_url='adminlogin')
def admin_delete_brand_view(request, pk):
    brand = models.Brand.objects.get(id=pk)
    brand.delete()
    messages.success(request, "Brand deleted successfully!")
    return redirect('manage_brand')

@login_required(login_url='adminlogin')
def manage_product_view(request):
    products = models.Product.objects.all()
    form = forms.ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('manage_product')
    return render(request, 'ecom/manage_product.html', {'form': form, 'products': products})

@login_required(login_url='adminlogin')
def delete_product_view(request, pk):
    product = models.Product.objects.get(id=pk)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect('manage_product') 

#filtering for category_product_view
def category_products_view(request, category_slug):
    # 🔄 Lookup by slug instead of ID
    category = get_object_or_404(models.Category, slug=category_slug)

    products = models.Product.objects.filter(
        category=category,
        availability=True
    )

    # Sorting logic
    sort = request.GET.get('sort')
    if sort == 'latest':
        products = products.order_by('-id')
    elif sort == 'low_to_high':
        products = products.order_by('price')
    elif sort == 'high_to_low':
        products = products.order_by('-price')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'popular':
        products = products.order_by('-views')  # update field based on model
    elif sort == 'newest':
        products = products.order_by('-created_at')    

    # Price filtering
    min_p = request.GET.get('min_price')
    max_p = request.GET.get('max_price')
    if min_p and max_p:
        products = products.filter(price__gte=min_p, price__lte=max_p)

    all_categories = models.Category.objects.all()

    return render(request, 'ecom/shop.html', {
        'category': category,
        'products': products,
        'all_categories': all_categories,
        'sort': sort,
        'min_price': min_p,
        'max_price': max_p,
    })

#filtering shop_view


# ecom/views.py
from django.shortcuts import render
from .models import Product, Category

def shop_view(request):
    category_name = request.GET.get('category')
    sort = request.GET.get('sort')
    min_p = request.GET.get('min_price')
    max_p = request.GET.get('max_price')

    # Get products
    products = Product.objects.all()
    if category_name:
        products = products.filter(category__name=category_name)

    # Sorting
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')

    # Price filter
    if min_p:
        products = products.filter(price__gte=min_p)
    if max_p:
        products = products.filter(price__lte=max_p)

    total_products_count = products.count()

    # ✅ Get cart count from cookie or session
    cookie_value = request.COOKIES.get('product_ids', '').strip()
    if cookie_value:
        product_count_in_cart = sum(
            int(qty)
            for item in cookie_value.split('|')
            if ':' in item
            for pid, qty in [item.split(':')]
        )
    else:
        cart = request.session.get('cart', {})  # session fallback
        product_count_in_cart = sum(item.get('quantity', 1) for item in cart.values())

    # Recently viewed products
    recently_viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed_products = Product.objects.filter(id__in=recently_viewed_ids)

    return render(request, 'ecom/shop.html', {
        'products': products,
        'all_categories': Category.objects.all(),
        'category': category_name,
        'sort': sort,
        'min_price': min_p,
        'max_price': max_p,
        'total_products_count': total_products_count,
        'recently_viewed_products': recently_viewed_products,
        'product_count_in_cart': product_count_in_cart,
    })


    
    


#for recently view product & content based recommendation system

from .models import Product
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from scipy.sparse import hstack
from django.shortcuts import get_object_or_404, render


# Utility: Get total quantity from cookie
def get_total_cart_quantity(cookie_value):
    return sum(
        int(qty)
        for item in cookie_value.split('|')
        if ':' in item
        for pid, qty in [item.split(':')]
    )


def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # ✅ Increment view count
    product.views_count += 1
    product.save()

    # Track recently viewed
    recently_viewed = request.session.get('recently_viewed', [])
    if pk in recently_viewed:
        recently_viewed.remove(pk)
    recently_viewed.insert(0, pk)
    request.session['recently_viewed'] = recently_viewed[:5]

    try:
        all_products = Product.objects.exclude(id=pk)

        # Step 1: Create DataFrame with text and price
        df = pd.DataFrame([
            {
                'id': p.id,
                'text': f"{p.category.name} {p.brand.name} {p.description}",
                'price': float(p.price)
            } for p in all_products
        ])

        # Add current product
        df.loc[len(df)] = {
            'id': product.id,
            'text': f"{product.category.name} {product.brand.name} {product.description}",
            'price': float(product.price)
        }

        # Step 2: TF-IDF
        tfidf = TfidfVectorizer()
        tfidf_matrix = tfidf.fit_transform(df['text'])

        # Step 3: Normalize price
        scaler = MinMaxScaler()
        price_vector = scaler.fit_transform(df[['price']])

        # Step 4: Combine features
        combined_features = hstack([tfidf_matrix, price_vector])

        # Step 5: Cosine similarity
        sim_matrix = cosine_similarity(combined_features)

        # Step 6: Identify similar products
        target_index = df[df['id'] == product.id].index[0]
        sim_scores = sorted(
            list(enumerate(sim_matrix[target_index])),
            key=lambda x: x[1],
            reverse=True
        )

        # Step 7: Top 4 similar product IDs
        recommended_ids = [
            int(df.iloc[i[0]]['id']) for i in sim_scores[1:5]
        ]

        # Step 8: Query recommended products
        recommended_products = Product.objects.filter(id__in=recommended_ids)

    except Exception as e:
        print("Error in recommendation logic:", e)
        recommended_products = []

    # ✅ Cart count logic (same as shop view)
    product_count_in_cart = 0
    if 'product_ids' in request.COOKIES:
        product_count_in_cart = get_total_cart_quantity(request.COOKIES['product_ids'])

    # Step 9: Return to template
    return render(request, 'ecom/product_detail.html', {
        'product': product,
        'recommended_products': recommended_products,
        'product_count_in_cart': product_count_in_cart,  # ✅ send to navbar
    })


# def home_view(request):
#     try:
#         session_test = request.session.items()
#     except Exception:
#         request.session.flush()

#     products = models.Product.objects.all()[:9]
#     categories = models.Category.objects.all()  
#     product_count_in_cart = 0

#     if 'product_ids' in request.COOKIES:
#         product_count_in_cart = get_total_cart_quantity(request.COOKIES['product_ids'])

#     if request.user.is_authenticated:
#         return HttpResponseRedirect('afterlogin')

#     return render(request, 'ecom/index.html', {
#         'products': products,
#         'product_count_in_cart': product_count_in_cart,
#         'categories': categories  # ✅ Include this so navbar can show dropdown
#     })


#for popular product 

from django.db.models import Count, F, ExpressionWrapper, IntegerField
from . import models
from .models import Product, OrderItem
from django.shortcuts import render
from django.http import HttpResponseRedirect

def home_view(request):
    try:
        session_test = request.session.items()
    except Exception:
        request.session.flush()

    # ✅ Latest products
    products = models.Product.objects.all().order_by('-id')[:9]

    # ✅ Popular products
    popular_products = models.Product.objects.annotate(
        order_count=Count('orderitem'),
        popularity_score=ExpressionWrapper(
            F('order_count') * 2 + F('views_count'),
            output_field=IntegerField()
        )
    ).order_by('-popularity_score')[:6]

    # ✅ Categories
    categories = models.Category.objects.all()

    # ✅ Cart quantity
    product_ids = request.COOKIES.get('product_ids', '')
    if product_ids:
        product_count_in_cart = len(set(product_ids.split('|')))
    else:
        product_count_in_cart = 0

    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')

    return render(request, 'ecom/index.html', {
        'products': products,
        'popular_products': popular_products,
        'product_count_in_cart': product_count_in_cart,
        'categories': categories
    })


def demo_view(request):
    try:
        session_test = request.session.items()
    except Exception:
        request.session.flush()

    products = models.Product.objects.all()[:9]
    categories = models.Category.objects.all() 
    product_count_in_cart = 0

    if 'product_ids' in request.COOKIES:
        product_count_in_cart = get_total_cart_quantity(request.COOKIES['product_ids'])

    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')

    return render(request, 'ecom/index.html', {
        'products': products,
        'product_count_in_cart': product_count_in_cart,
        'categories': categories  
    })



def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return HttpResponseRedirect('adminlogin')

# def shop_view(request):
    category_name = request.GET.get('category')
    products = Product.objects.all()

    if category_name:
        products = products.filter(category__name=category_name)

    # Price filtering
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Sorting
    sort = request.GET.get('sort')
    if sort == 'latest':
        products = products.order_by('-id')
    elif sort == 'popular':
        products = products.order_by('-views')
    elif sort == 'low_to_high':
        products = products.order_by('price')
    elif sort == 'high_to_low':
        products = products.order_by('-price')
    elif sort == 'name_asc':
        products = products.order_by('name')

    categories = Category.objects.all()

    return render(request, 'shop.html', {
        'products': products,
        'categories': categories,
        'sort': sort,
        'min_price': min_price,
        'max_price': max_price,
    })
def customer_signup_view(request):
    userForm = forms.CustomerUserForm()
    customerForm = forms.CustomerForm()
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST)
        customerForm = forms.CustomerForm(request.POST, request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            customer = customerForm.save(commit=False)
            customer.user = user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
        return HttpResponseRedirect('customerlogin')
    return render(request, 'ecom/customersignup.html', {'userForm': userForm, 'customerForm': customerForm})


def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()


def afterlogin_view(request):
    if is_customer(request.user):
        return redirect('customer-home')
    else:
        return redirect('admin-dashboard')


@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    customercount = models.Customer.objects.count()
    productcount = models.Product.objects.count()
    ordercount = models.Orders.objects.count()
    orders = models.Orders.objects.all()

    data = zip(
        [models.Product.objects.filter(id=o.product.id) for o in orders],
        [models.Customer.objects.filter(id=o.customer.id) for o in orders],
        orders
    )

    context = {
        'customercount': customercount,
        'productcount': productcount,
        'ordercount': ordercount,
        'data': data,
    }
    return render(request, 'ecom/admin_dashboard.html', context)

# Use the correct view function name


@login_required(login_url='adminlogin')
def view_customer_view(request):
    customers = models.Customer.objects.all()
    return render(request, 'ecom/view_customer.html', {'customers': customers})


@login_required(login_url='adminlogin')
def delete_customer_view(request, pk):
    customer = models.Customer.objects.get(id=pk)
    customer.user.delete()
    customer.delete()
    return redirect('view-customer')


@login_required(login_url='adminlogin')
def update_customer_view(request, pk):
    customer = models.Customer.objects.get(id=pk)
    userForm = forms.CustomerUserForm(instance=customer.user)
    customerForm = forms.CustomerForm(instance=customer)

    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST, instance=customer.user)
        customerForm = forms.CustomerForm(request.POST, request.FILES, instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return redirect('view-customer')

    return render(request, 'ecom/admin_update_customer.html', {'userForm': userForm, 'customerForm': customerForm})


@login_required(login_url='adminlogin')
def admin_products_view(request):
    products = models.Product.objects.all()
    return render(request, 'ecom/admin_products.html', {'products': products})


@login_required(login_url='adminlogin')
def admin_add_product_view(request):
    productForm = forms.ProductForm()
    if request.method == 'POST':
        productForm = forms.ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
        return HttpResponseRedirect('admin-products')
    return render(request, 'ecom/admin_add_product.html', {'productForm': productForm})


@login_required(login_url='adminlogin')
def delete_product_view(request, pk):
    models.Product.objects.get(id=pk).delete()
    return redirect('admin-products')


@login_required(login_url='adminlogin')
def update_product_view(request, pk):
    product = models.Product.objects.get(id=pk)
    productForm = forms.ProductForm(instance=product)
    if request.method == 'POST':
        productForm = forms.ProductForm(request.POST, request.FILES, instance=product)
        if productForm.is_valid():
            productForm.save()
            return redirect('admin-products')
    return render(request, 'ecom/admin_update_product.html', {'productForm': productForm})


@login_required(login_url='adminlogin')
def admin_view_booking_view(request):
    orders = models.Orders.objects.all()
    data = zip(
        [models.Product.objects.filter(id=o.product.id) for o in orders],
        [models.Customer.objects.filter(id=o.customer.id) for o in orders],
        orders
    )
    return render(request, 'ecom/admin_view_booking.html', {'data': data})


@login_required(login_url='adminlogin')
def delete_order_view(request, pk):
    models.Orders.objects.get(id=pk).delete()
    return redirect('admin-view-booking')


@login_required(login_url='adminlogin')
def update_order_view(request, pk):
    order = models.Orders.objects.get(id=pk)
    orderForm = forms.OrderForm(instance=order)
    if request.method == 'POST':
        orderForm = forms.OrderForm(request.POST, instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request, 'ecom/update_order.html', {'orderForm': orderForm})


@login_required(login_url='adminlogin')
def view_feedback_view(request):
    feedbacks = models.Feedback.objects.all().order_by('-id')
    return render(request, 'ecom/view_feedback.html', {'feedbacks': feedbacks})


from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_user(request):
    logout(request)
    return redirect('logout-success')


# --- CUSTOMER VIEWS ---

#     try:
#         session_test = request.session.items()
#     except Exception:
#         request.session.flush()

#     products = models.Product.objects.all()[:9]
#     categories = models.Category.objects.all()  # ✅ This line is missing in your current code
#     product_count_in_cart = 0

#     if 'product_ids' in request.COOKIES:
#         product_count_in_cart = get_total_cart_quantity(request.COOKIES['product_ids'])

#     if request.user.is_authenticated:
#         return HttpResponseRedirect('afterlogin')

#     return render(request, 'ecom/customer_home.html', {
#         'products': products,
#         'product_count_in_cart': product_count_in_cart,
#         'categories': categories  # ✅ Include this so navbar can show dropdown
#     })
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_home_view(request):
    product_count_in_cart = 0

    if 'product_ids' in request.COOKIES:
        product_count_in_cart = get_total_cart_quantity(request.COOKIES['product_ids'])

    products = models.Product.objects.all()[:9]

    return render(request, 'ecom/customer_home.html', {
        'products': products,
        'product_count_in_cart': product_count_in_cart
    })

    
    
def search_view(request):
    query = request.GET.get('query', '')
    products = models.Product.objects.filter(name__icontains=query)
    product_count_in_cart = get_total_cart_quantity(request.COOKIES.get('product_ids', ''))

    return render(request, 'ecom/shop.html', {  # ✅ changed to index.html
        'products': products,
        'word': f"Searched Result for: {query}" if query else "Search Results",
        'product_count_in_cart': product_count_in_cart
    })






def add_to_cart_view(request, pk):
    cart_items = {}
    if 'product_ids' in request.COOKIES:
        for item in request.COOKIES['product_ids'].split('|'):
            if ':' in item:
                pid, qty = item.split(':')
                cart_items[pid] = int(qty)

    cart_items[str(pk)] = cart_items.get(str(pk), 0) + 1

    updated_cookie = '|'.join(f'{pid}:{qty}' for pid, qty in cart_items.items())
    referer = request.META.get('HTTP_REFERER', 'customer-home')
    response = redirect(referer)
    response.set_cookie('product_ids', updated_cookie)
    messages.success(request, f"{models.Product.objects.get(id=pk).name} added to cart.")
    return response


def cart_view(request):
    cart_items = {}
    products = []
    total = 0

    if 'product_ids' in request.COOKIES:
        for item in request.COOKIES['product_ids'].split('|'):
            if ':' in item:
                pid, qty = item.split(':')
                cart_items[int(pid)] = int(qty)

    product_objs = models.Product.objects.filter(id__in=cart_items.keys())
    for product in product_objs:
        product.quantity = cart_items[product.id]
        product.total_price = product.quantity * product.price
        total += product.total_price
        products.append(product)

    return render(request, 'ecom/cart.html', {'products': products, 'total': total, 'product_count_in_cart': sum(cart_items.values())})


def remove_from_cart_view(request, pk):
    cart_items = {}
    if 'product_ids' in request.COOKIES:
        for item in request.COOKIES['product_ids'].split('|'):
            if ':' in item:
                pid, qty = item.split(':')
                cart_items[pid] = int(qty)

    pid = str(pk)
    if pid in cart_items:
        if cart_items[pid] > 1:
            cart_items[pid] -= 1
        else:
            del cart_items[pid]

    updated_cookie = '|'.join(f'{pid}:{qty}' for pid, qty in cart_items.items())
    response = redirect('cart')
    if cart_items:
        response.set_cookie('product_ids', updated_cookie)
    else:
        response.delete_cookie('product_ids')
    return response


def increase_cart_item_view(request, pk):
    cart_items = {}
    if 'product_ids' in request.COOKIES:
        for item in request.COOKIES['product_ids'].split('|'):
            if ':' in item:
                pid, qty = item.split(':')
                cart_items[pid] = int(qty)

    pid = str(pk)
    if pid in cart_items:
        cart_items[pid] += 1

    updated_cookie = '|'.join(f'{pid}:{qty}' for pid, qty in cart_items.items())
    response = redirect('cart')
    response.set_cookie('product_ids', updated_cookie)
    return response


def delete_from_cart_view(request, pk):
    cart_items = {}
    if 'product_ids' in request.COOKIES:
        for item in request.COOKIES['product_ids'].split('|'):
            if ':' in item:
                pid, qty = item.split(':')
                cart_items[pid] = int(qty)

    cart_items.pop(str(pk), None)

    updated_cookie = '|'.join(f'{pid}:{qty}' for pid, qty in cart_items.items())
    response = redirect('cart')
    if updated_cookie:
        response.set_cookie('product_ids', updated_cookie)
    else:
        response.delete_cookie('product_ids')
    return response


def send_feedback_view(request):
    feedbackForm = forms.FeedbackForm()
    if request.method == 'POST':
        feedbackForm = forms.FeedbackForm(request.POST)
        if feedbackForm.is_valid():
            feedbackForm.save()
            return render(request, 'ecom/feedback_sent.html')
    return render(request, 'ecom/send_feedback.html', {'feedbackForm': feedbackForm})

# ------------------------ CUSTOMER RELATED VIEWS START ------------------------------
@login_required(login_url='customerlogin')
@user_passes_test(lambda u: u.groups.filter(name='CUSTOMER').exists())
def customer_home_view(request):
    products = models.Product.objects.all()[:9]
    product_count_in_cart = 0

    if 'product_ids' in request.COOKIES:
        cookie_value = request.COOKIES['product_ids']
        product_count_in_cart = get_total_cart_quantity(cookie_value)

    return render(request, 'ecom/customer_home.html', {
        'products': products,
        'product_count_in_cart': product_count_in_cart
    })

        
   
            #for showing total price on payment page.....accessing id from cookies then fetching  price of product from db


# Generate eSewa HMAC-SHA256 Signature
def generate_signature(fields, secret_key):
    message = ''.join([str(fields[field]) for field in fields['signed_field_names'].split(',')])
    digest = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(digest).decode('utf-8')


            
    if request.method == 'POST':
     addressForm = forms.AddressForm(request.POST)
    if addressForm.is_valid():
        email = addressForm.cleaned_data['Email']
        mobile = addressForm.cleaned_data['Mobile']
        address = addressForm.cleaned_data['Address']

        # Calculate total cart price
        total = 0
        if 'product_ids' in request.COOKIES:
            product_ids = request.COOKIES['product_ids']
            if product_ids:
                product_entries = product_ids.split('|')  # ['1:2', '3:1', ...]
                product_ids_only = []
                for entry in product_entries:
                    try:
                        product_id = int(entry.split(':')[0])  # Get product id only
                        product_ids_only.append(product_id)
                    except (IndexError, ValueError):
                        pass

                products = models.Product.objects.filter(id__in=product_ids_only)
                for p in products:
                    total += p.price

        # Prepare eSewa payment fields
        transaction_uuid = str(uuid.uuid4())
        signed_fields = {
            'total_amount': total,
            'transaction_uuid': transaction_uuid,
            'product_code': 'EPAYTEST',
            'signed_field_names': 'total_amount,transaction_uuid,product_code'
        }

        secret_key = '8gBm/:&EnhH.1/q'  # Your secret key here
        signature = generate_signature(signed_fields, secret_key)

        response = render(request, 'ecom/payment.html', {
            'total': total,
            'uuid': transaction_uuid,
            'signature': signature
        })

        response.set_cookie('email', email)
        response.set_cookie('mobile', mobile)
        response.set_cookie('address', address)

        return response

            # Save address data in cookies for future use (or save in DB)
        

    return render(request, 'ecom/customer_address.html', {
        'addressForm': addressForm,
        'product_in_cart': product_in_cart,
        'product_count_in_cart': product_count_in_cart
    })




# here we are just directing to this view...actually we have to check whther payment is successful or not
#then only this view should be accessed
@login_required(login_url='customerlogin')
def payment_success_view(request):
    # Here we will place order | after successful payment
    # we will fetch customer  mobile, address, Email
    # we will fetch product id from cookies then respective details from db
    # then we will create order objects and store in db
    # after that we will delete cookies because after order placed...cart should be empty
    customer=models.Customer.objects.get(user_id=request.user.id)
    products=None
    email=None
    mobile=None
    address=None
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            products=models.Product.objects.all().filter(id__in = product_id_in_cart)
            # Here we get products list that will be ordered by one customer at a time

    # these things can be change so accessing at the time of order...
    if 'email' in request.COOKIES:
        email=request.COOKIES['email']
    if 'mobile' in request.COOKIES:
        mobile=request.COOKIES['mobile']
    if 'address' in request.COOKIES:
        address=request.COOKIES['address']

    # here we are placing number of orders as much there is a products
    # suppose if we have 5 items in cart and we place order....so 5 rows will be created in orders table
    # there will be lot of redundant data in orders table...but its become more complicated if we normalize it
    for product in products:
        models.Orders.objects.get_or_create(customer=customer,product=product,status='Pending',email=email,mobile=mobile,address=address)

    # after order placed cookies should be deleted
    response = render(request,'ecom/payment_success.html')
    response.delete_cookie('product_ids')
    response.delete_cookie('email')
    response.delete_cookie('mobile')
    response.delete_cookie('address')
    return response




@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_order_view(request):
    
    customer=models.Customer.objects.get(user_id=request.user.id)
    
    orders=models.Orders.objects.all().filter(customer_id = customer)
    ordered_products=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_products.append(ordered_product)

    return render(request,'ecom/my_order.html',{'data':zip(ordered_products,orders)})
 



# @login_required(login_url='customerlogin')
# @user_passes_test(is_customer)
# def my_order_view2(request):

#     products=models.Product.objects.all()
#     if 'product_ids' in request.COOKIES:
#         product_ids = request.COOKIES['product_ids']
#         counter=product_ids.split('|')
#         product_count_in_cart=len(set(counter))
#     else:
#         product_count_in_cart=0
#     return render(request,'ecom/my_order.html',{'products':products,'product_count_in_cart':product_count_in_cart})    



#--------------for discharge patient bill (pdf) download and printin

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def download_invoice_view(request,orderID,productID):
    order=models.Orders.objects.get(id=orderID)
    product=models.Product.objects.get(id=productID)
    mydict={
        'orderDate':order.order_date,
        'customerName':request.user,
        'customerEmail':order.email,
        'customerMobile':order.mobile,
        'shipmentAddress':order.address,
        'orderStatus':order.status,

        'productName':product.name,
        'productImage':product.product_image,
        'productPrice':product.price,
        'productDescription':product.description,


    }
    return render_to_pdf('ecom/download_invoice.html',mydict)






@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    return render(request,'ecom/my_profile.html',{'customer':customer})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_profile_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    user = models.User.objects.get(id=customer.user_id)
    userForm = forms.CustomerUserForm(instance=user)
    customerForm = forms.CustomerForm(instance=customer)
    mydict = {'userForm': userForm, 'customerForm': customerForm}

    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST, instance=user)
        customerForm = forms.CustomerForm(request.POST, request.FILES, instance=customer)  # ✅ fixed
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return HttpResponseRedirect('my-profile')

    return render(request, 'ecom/edit_profile.html', context=mydict)




#---------------------------------------------------------------------------------
#------------------------ ABOUT US AND CONTACT US VIEWS START --------------------
#---------------------------------------------------------------------------------
def aboutus_view(request):
    return render(request,'ecom/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email),message, settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = False)
            return render(request, 'ecom/contactussuccess.html')
    return render(request, 'ecom/contactus.html', {'form':sub})






# Replace these with actual values in production
ESEWA_SECRET_KEY = '8gBm/:&EnhH.1/q'
ESEWA_PRODUCT_CODE = 'EPAYTEST'
ESEWA_BASE_URL = 'https://rc-epay.esewa.com.np'


def generate_signature(fields, secret_key):
    signed_field_names = fields['signed_field_names'].split(',')
    message = ','.join(f"{field}={fields[field]}" for field in signed_field_names)
    digest = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(digest).decode('utf-8')


# @login_required(login_url='customerlogin')
# def customer_address_view(request):
#     product_in_cart = False
#     product_count_in_cart = 0

#     product_ids = request.COOKIES.get('product_ids', '')
#     if product_ids:
#         product_in_cart = True
#         product_count_in_cart = len(set(product_ids.split('|')))

#     addressForm = forms.AddressForm()

#     if request.method == 'POST':
#         addressForm = forms.AddressForm(request.POST)
#         if addressForm.is_valid():
#             email = addressForm.cleaned_data['Email']
#             mobile = addressForm.cleaned_data['Mobile']
#             address = addressForm.cleaned_data['Address']

#             # Total price calculation
#             total = 0
#             entries = []
#             for entry in product_ids.split('|'):
#                 if ':' not in entry: continue
#                 try:
#                     pid, qty = map(int, entry.split(':'))
#                     entries.append((pid, qty))
#                 except ValueError:
#                     continue

#             product_map = {p.id: p for p in models.Product.objects.filter(id__in=[e[0] for e in entries])}
#             for pid, qty in entries:
#                 product = product_map.get(pid)
#                 if product:
#                     total += product.price * qty

#             transaction_uuid = str(uuid.uuid4())
#             signed_fields = {
#                 'total_amount': total,
#                 'transaction_uuid': transaction_uuid,
#                 'product_code': ESEWA_PRODUCT_CODE,
#                 'signed_field_names': 'total_amount,transaction_uuid,product_code'
#             }

#             signature = generate_signature(signed_fields, ESEWA_SECRET_KEY)
#             # success_url = request.build_absolute_uri('/esewa/success/')
#             success_url = request.build_absolute_uri(
#     f"/esewa/success/?transaction_uuid={transaction_uuid}&total_amount={total_amount}&product_code={ESEWA_PRODUCT_CODE}"
# )

#             failure_url = request.build_absolute_uri('/esewa/failure/')

#             response = render(request, 'ecom/payment.html', {
#                 'total': total,
#                 'uuid': transaction_uuid,
#                 'signature': signature,
#                 'success_url': success_url,
#                 'failure_url': failure_url,
#                 'product_code': ESEWA_PRODUCT_CODE
#             })

#             response.set_cookie('email', email)
#             response.set_cookie('mobile', mobile)
#             response.set_cookie('address', address)
#             return response

#     return render(request, 'ecom/customer_address.html', {
#         'addressForm': addressForm,
#         'product_in_cart': product_in_cart,
#         'product_count_in_cart': product_count_in_cart
#     })

@login_required(login_url='customerlogin')
def customer_address_view(request):
    product_in_cart = False
    product_count_in_cart = 0

    product_ids = request.COOKIES.get('product_ids', '')
    if product_ids:
        product_in_cart = True
        product_count_in_cart = len(set(product_ids.split('|')))

    addressForm = forms.AddressForm()

    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        if addressForm.is_valid():
            email = addressForm.cleaned_data['Email']
            mobile = addressForm.cleaned_data['Mobile']
            address = addressForm.cleaned_data['Address']

            # Total price calculation
            total = 0
            entries = []
            for entry in product_ids.split('|'):
                if ':' not in entry:
                    continue
                try:
                    pid, qty = map(int, entry.split(':'))
                    entries.append((pid, qty))
                except ValueError:
                    continue

            product_map = {p.id: p for p in models.Product.objects.filter(id__in=[e[0] for e in entries])}
            for pid, qty in entries:
                product = product_map.get(pid)
                if product:
                    total += product.price * qty

            transaction_uuid = str(uuid.uuid4())
            signed_fields = {
                'total_amount': total,
                'transaction_uuid': transaction_uuid,
                'product_code': ESEWA_PRODUCT_CODE,
                'signed_field_names': 'total_amount,transaction_uuid,product_code'
            }

            signature = generate_signature(signed_fields, ESEWA_SECRET_KEY)

            success_url = request.build_absolute_uri(
                f"/esewa/success/?transaction_uuid={transaction_uuid}&total_amount={total}&product_code={ESEWA_PRODUCT_CODE}"
            )

            failure_url = request.build_absolute_uri('/esewa/failure/')

            response = render(request, 'ecom/payment.html', {
                'total': total,
                'uuid': transaction_uuid,
                'signature': signature,
                'success_url': success_url,
                'failure_url': failure_url,
                'product_code': ESEWA_PRODUCT_CODE
            })

            response.set_cookie('email', email)
            response.set_cookie('mobile', mobile)
            response.set_cookie('address', address)
            return response

    return render(request, 'ecom/customer_address.html', {
        'addressForm': addressForm,
        'product_in_cart': product_in_cart,
        'product_count_in_cart': product_count_in_cart
    })



@login_required(login_url='customerlogin')
def esewa_success_view(request):
    transaction_uuid = request.GET.get('transaction_uuid')
    total_amount = request.GET.get('total_amount')

    if not transaction_uuid or not total_amount:
        return HttpResponse("❌ Missing transaction data.")

    verify_url = f"{ESEWA_BASE_URL}/api/epay/transaction/status/"
    params = {
        "product_code": ESEWA_PRODUCT_CODE,
        "total_amount": total_amount,
        "transaction_uuid": transaction_uuid
    }

    response = requests.get(verify_url, params=params)
    if response.status_code != 200:
        return HttpResponse("⚠️ Could not verify transaction with eSewa.")

    data = response.json()
    if data.get("status") != "COMPLETE":
        return HttpResponse("❌ Payment was not completed.")

    try:
        email = request.COOKIES.get('email')
        mobile = request.COOKIES.get('mobile')
        address = request.COOKIES.get('address')
        product_ids = request.COOKIES.get('product_ids', '')

        customer = models.Customer.objects.get(user=request.user)

        for entry in product_ids.split('|'):
            if ':' not in entry:
                continue
            pid, qty = map(int, entry.split(':'))
            product = models.Product.objects.get(id=pid)
            for _ in range(qty):
                models.Orders.objects.create(
                    customer=customer,
                    product=product,
                    email=email,
                    mobile=mobile,
                    address=address,
                    status='Order Confirmed'
                )

        # response = HttpResponse("✅ Payment successful! Order has been placed.")
        return render(request, 'ecom/payment_success.html')
        response.delete_cookie('product_ids')
        response.delete_cookie('email')
        response.delete_cookie('mobile')
        response.delete_cookie('address')
        return response

    except Exception as e:
        return HttpResponse(f"❌ Error placing order: {str(e)}")


def esewa_failure_view(request):
    return HttpResponse("❌ Payment failed or was cancelled.")

def esewa_payment_view(request):
    transaction_uuid = str(uuid.uuid4())
    total_amount = 110  # test amount
    fields = {
        'total_amount': total_amount,
        'transaction_uuid': transaction_uuid,
        'product_code': ESEWA_PRODUCT_CODE,
        'signed_field_names': 'total_amount,transaction_uuid,product_code'
    }

    signature = generate_signature(fields, ESEWA_SECRET_KEY)
    success_url = request.build_absolute_uri('/esewa/success/')
    failure_url = request.build_absolute_uri('/esewa/failure/')

    return render(request, 'ecom/payment.html', {
        'total': total_amount,
        'uuid': transaction_uuid,
        'signature': signature,
        'product_code': ESEWA_PRODUCT_CODE,
        'success_url': success_url,
        'failure_url': failure_url
    })





import environ

env = environ.Env()
# This pulls the key from your .env file automatically
api_key = env('OPENAI_API_KEY')
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json

@csrf_exempt
def chatbot(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "").lower().strip()

        # Order Tracking Response
        if "track" in user_message or "order" in user_message:
            return JsonResponse({
                "reply": "Sure! You can view your order status here: <a href='/my-order' target='_blank'>Track My Order</a>. Let me know if you need help with anything else."
            })

        # FAQ Responses (More conversational tone)
        faq_answers = {
            "do you offer cash on delivery?": "Absolutely! We offer Cash on Delivery service all across Nepal for your convenience.",
            "what is the return policy?": "You can return any item within 7 days as long as it's in original condition and packaging.",
            "how long does delivery take?": "For Kathmandu, delivery takes about 2–4 business days. For locations outside the valley, it can take up to 7 days.",
            "do you sell original products?": "Yes, we only deal in verified and 100% original products. Your satisfaction is our priority.",
            "is there a delivery charge?": "We offer free delivery within Kathmandu. For other areas, delivery charges may apply depending on your location.",
        }

        reply = faq_answers.get(
            user_message,
            "I'm not sure I understood that. Could you please rephrase or choose from our FAQs above?"
        )

        return JsonResponse({"reply": reply})

def track_order(request):
    return render(request, 'ecom/my_order.html')

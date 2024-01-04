from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from user.models import Userprofile
from django.core.checks import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate,login,logout
from django.db.models import Q
from django.contrib import messages
import re
from .models import Category, Product, ProductImage, Variant, Brand, Coupons, UserCoupons, Reviews
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from cart.models import Order, OrderItem, OrderAddress
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.views.decorators.cache import never_cache
from datetime import datetime, timedelta, time
from django.db.models import F, Sum, Count
from django.contrib.auth.decorators import login_required


@never_cache
def admin_home(request):

    if not request.user.is_superuser:
        return redirect('admin_login')

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    total_ordered_orders = Order.objects.filter(is_ordered=True).count()
    total_available_products = Product.objects.all().count()
    total_available_customer = User.objects.filter(is_superuser=False).count()    
    total_available_category = Category.objects.all().count()
    print(total_available_category)
    total_pending = Order.objects.filter(is_ordered=True, status='Confirmed').count()
    total_delivered = Order.objects.filter(is_ordered=True, status='Delivered').count()
    total_cancelled = Order.objects.filter(is_ordered=True, status='cancelled').count()
    total_returned = Order.objects.filter(is_ordered=True, status='Returned').count()

    total_earned_amount = \
        Order.objects.filter(is_ordered=True).exclude(status__in=['Cancelled', 'Returned']).aggregate(
            Sum('total_amount'))[
            'total_amount__sum'] or 0
    users = User.objects.filter(is_superuser=False)[:5]

    daily_order_counts = (
        Order.objects
        .filter(created_at__range=(start_date, end_date), is_ordered=True)
        .values('created_at__date')
        .annotate(order_count=Count('id'))
        .order_by('created_at__date')
    )

    dates = [entry['created_at__date'].strftime('%Y-%m-%d') for entry in daily_order_counts]
    counts = [entry['order_count'] for entry in daily_order_counts]

    orders = Order.objects.filter(is_ordered=True).order_by('-created_at')[:10]
    context = {
        'username': request.session.get('admin'),
        'total_ordered_orders': total_ordered_orders,
        'total_available_products': total_available_products,
        'total_earned_amount': total_earned_amount,
        'total_available_customer': total_available_customer,
        'total_available_category': total_available_category,
        'total_pending': total_pending,
        'total_returned': total_returned,
        'total_cancelled': total_cancelled,
        'total_delivered': total_delivered,

        'users': users,
        'orders': orders,
        'dates': dates,
        'counts': counts,
        # 'monthly_dates': monthly_dates,
        # 'monthly_counts': monthly_counts,

    }
    return render(request, 'admin_home.html', context)

@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_home')
    if request.method == 'POST':
        uname = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=uname, password=password)

        if user is not None and user.is_superuser and user.is_active:
            request.session['super_user']=uname
            login(request, user)
            return redirect('admin_home')
        else:
            messages.error(request, "Invalid credentials. Please Try again.")
            return redirect('admin_login')
    return render(request, 'admin_login.html')




@never_cache
def user_list(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    if request.user.is_authenticated and request.user.is_superuser:
        users = User.objects.filter(is_superuser=False)  # Exclude superuser
        user_data = []

        for user in users:
            try:
                userprofile = Userprofile.objects.get(user=user)
                blocked_status = userprofile.blocked
                phone_number = userprofile.phone_number
            except Userprofile.DoesNotExist:
                # Handle the case where Userprofile does not exist for the user
                messages.warning(request, f'Userprofile not found for user {user.username}')
                blocked_status = None
                phone_number = None

            user_info = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': phone_number,
                'status': 'Blocked' if blocked_status else 'Unblocked'
            }
            user_data.append(user_info)

        return render(request, 'user_management.html', {'users': user_data})
    else:
        messages.info(request, "Please log in as admin")
        return redirect('admin_login')
    


@never_cache
def block_user(request, user_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')

    if request.user.is_authenticated and request.user.is_superuser:
        try:
            user = User.objects.get(id=user_id)
            userprofile = Userprofile.objects.get(user=user)
            userprofile.blocked = not userprofile.blocked
            userprofile.save()
            messages.success(request, f"User {user.username} has been {'blocked' if userprofile.blocked else 'unblocked'} successfully.")
        except User.DoesNotExist:
            messages.warning(request, f"User with ID {user_id} not found.")
        except Userprofile.DoesNotExist:
            messages.warning(request, f"Userprofile not found for user with ID {user_id}.")

        return redirect('user_list')

    else:
        messages.info(request, "Please log in as admin")
        return redirect('admin_login')



@never_cache
def create_category(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    if request.method == 'POST':
        name = request.POST.get('category_name')  
        description = request.POST.get('category_description')  
        
        categories = Category.objects.all()

        
        if not name:
            return render(request, 'page-categories.html', {'error': 'Name is required.', 'description': description})

        
        if not re.match(r'^[a-zA-Z]+(?: [a-zA-Z]+)*$', name):
            return render(request, 'page-categories.html', {'error': 'Invalid name. Use only letters and single spaces between words.', 'description': description})

        
        if Category.objects.filter(name=name).exists():
            return render(request, 'page-categories.html', {'error': 'Category with this name already exists.', 'description': description})

        
        category = Category.objects.create(name=name, description=description)

        
        return redirect('category_list')  
    return render(request, 'page-categories.html')


@never_cache
def category_list(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    categories = Category.objects.all() 
    return render(request, 'page-categories.html', {'categories': categories})


@never_cache
def edit_category(request, category_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('category_name')
        description = request.POST.get('category_description')

        
        if not name:
            return render(request, 'edit_category.html', {'category': category, 'error': 'Name is required.', 'description': description})

        
        if not re.match(r'^[a-zA-Z]+(?: [a-zA-Z]+)*$', name):
            return render(request, 'edit_category.html', {'category': category, 'error': 'Invalid name. Use only letters and single spaces between words.', 'description': description})

   
        category.name = name
        category.description = description
        category.save()

        
        return redirect('category_list')  

    return render(request, 'edit_category.html', {'category': category})


@never_cache
def delete_category(request, category_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    return HttpResponseRedirect(reverse('category_list'))



@never_cache
def create_product(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    categories = Category.objects.all()
    brands = Brand.objects.all()
    context = {'categories': categories, 'brands': brands}

    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description')
        brand_id = request.POST.get('brand')  
        stocks = request.POST.getlist('stock')
        sizes = request.POST.getlist('size')
        colors = request.POST.getlist('color')
        is_blocked = request.POST.get('is_blocked') == 'on'
        category_ids = request.POST.getlist('categories')

        if not category_ids:
            return render(request, 'create_product.html', {**context, 'error': 'Please select at least one category.'})

        
        if not re.match(r'^[^\s].*[^\s]$', name) or re.search(r'\s\s', name):
            return render(request, 'create_product.html', {**context, 'error': 'Invalid name.'})

        
        try:
            price_decimal = Decimal(price.replace('₹', '').replace(',', '').strip())
            if price_decimal < 1 or int(price_decimal) != price_decimal:
                raise ValueError
        except (InvalidOperation, ValueError):
            return render(request, 'create_product.html', {**context, 'error': 'Invalid price.'})

       
        if not description or description.isspace():
            return render(request, 'create_product.html', {**context, 'error': 'Description is required and cannot be empty.'})

       
        if not re.match(r'^[^\s].*', description):
            return render(request, 'create_product.html', {**context, 'error': 'Description cannot start with spaces.'})

       
        for stock, size, color in zip(stocks, sizes, colors):
            try:
                stock_int = int(stock)
                if stock_int < 0:
                    raise ValueError
            except ValueError:
                return render(request, 'create_product.html', {**context, 'error': 'Invalid stock.'})

           
            if not size or not re.match(r'^[a-zA-Z]+(?: [a-zA-Z]+)*$', color):
                return render(request, 'create_product.html', {**context, 'error': 'Invalid size or color.'})

        
        with transaction.atomic():
            product = Product.objects.create(
                name=name,
                price=price_decimal,
                description=description,
                brand_id=brand_id,
                is_blocked=is_blocked,
            )

            for stock, size, color in zip(stocks, sizes, colors):
                Variant.objects.create(
                    product=product,
                    size=size,
                    color=color,
                    stock=int(stock)
                )

            for i in range(1, 6):
                image_key = f'image{i}'
                image = request.FILES.get(image_key)
                if image:
                    ProductImage.objects.create(product=product, image=image)

            product.categories.add(*category_ids)

        return redirect('product_list')

    return render(request, 'create_product.html', context)



@never_cache
def edit_product(request, product_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    brands = Brand.objects.all()
    variants = Variant.objects.filter(product=product)
    images = ProductImage.objects.filter(product=product)

    context = {
        'categories': categories,
        'brands': brands,
        'product': product,
        'variants': variants,
        'images': images,
    }

    if request.method == 'POST':
       
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description')
        brand_id = request.POST.get('brand') 
        category_ids = request.POST.getlist('categories')

        # Validate inputs
        if not name or not name.strip():
            context['error'] = 'Name is required.'
            return render(request, 'edit_product.html', context)

        try:
            price_decimal = Decimal(price.replace('₹', '').replace(',', '').strip())
        except InvalidOperation:
            context['error'] = 'Invalid price.'
            return render(request, 'edit_product.html', context)

        if not isinstance(price_decimal, Decimal) or price_decimal < 1:
            context['error'] = 'Invalid price.'
            return render(request, 'edit_product.html', context)

        
        if not description or description.isspace():
            context['error'] = 'Description is required and cannot be empty.'
            return render(request, 'edit_product.html', context)

        
        if not re.match(r'^[^\s].*', description):
            context['error'] = 'Description cannot start with spaces.'
            return render(request, 'edit_product.html', context)

       
        product.name = name
        product.price = price_decimal
        product.description = description
        product.brand_id = brand_id

       
        with transaction.atomic():
            try:
                product.save()
            except IntegrityError as e:
                context['error'] = f'Error saving product: {e}'
                return render(request, 'edit_product.html', context)

           
            variants_data = []
            for i in range(len(request.POST.getlist('stock'))):
                stock = request.POST.getlist('stock')[i]
                size = request.POST.getlist('size')[i]
                color = request.POST.getlist('color')[i]

                try:
                    stock_int = int(stock)
                    if stock_int < 0:
                        raise ValueError
                except ValueError:
                    context['error'] = 'Invalid stock.'
                    return render(request, 'edit_product.html', context)

              
                if not size or not re.match(r'^[a-zA-Z]+(?: [a-zA-Z]+)*$', color):
                    context['error'] = 'Invalid size or color.'
                    return render(request, 'edit_product.html', context)

                variants_data.append({
                    'size': size,
                    'color': color,
                    'stock': stock_int,
                })

           
            variants.delete()

            
            for variant_data in variants_data:
                Variant.objects.create(product=product, **variant_data)

            
            # Handle existing images
            existing_images = ProductImage.objects.filter(product=product)
            for i, image in enumerate(existing_images):
                image_key = f'image{i + 1}'
                image_file = request.FILES.get(image_key)
                if image_file:
                    image.image = image_file
                    try:
                        image.save()
                    except ValidationError as e:
                        context['error'] = f'Error saving product image: {e}'
                        return render(request, 'edit_product.html', context)

           
            product.categories.set(category_ids)

        return redirect('product_list')

    return render(request, 'edit_product.html', context)



@never_cache
def block_product(request, product_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    try:
        product = Product.objects.get(id=product_id)
        product.is_blocked = not product.is_blocked 
        product.save()
        return redirect('product_list')
    except Product.DoesNotExist:
        messages.error(request, "Product not found.")
        return redirect('product_list')




@never_cache
def product_list(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    products = Product.objects.all()
    product_data = []

    for product in products:
        images = ProductImage.objects.filter(product=product)
        categories = product.categories.all()
        first_image = images.first() if images else None

        product_data.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'brand': product.brand.name if product.brand else None,  
            'categories': [category.name for category in categories],
            'image_url': first_image.image.url if first_image else None,
            'is_blocked': product.is_blocked,
        })

    context = {'products': product_data}
    return render(request, 'product_list.html', context)




@never_cache
def create_brand(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    if request.method == 'POST':
        name = request.POST.get('brand_name')
        logo = request.FILES.get('brand_logo')

        print("Name:", name)  
        print("Logo:", logo)  

      
        if not name:
            return render(request, 'create_brand.html', {'error': 'Brand name is required.'})

        
        if not re.match(r'^[^\s].*[^\s]$', name) or re.search(r'\s\s', name):
            return render(request, 'create_brand.html', {'error': 'Invalid brand name.'})

        
        if Brand.objects.filter(name=name).exists():
            return render(request, 'create_brand.html', {'error': 'Brand with this name already exists.'})

        brand = Brand.objects.create(name=name, logo=logo)

        return redirect('brand_list') 

    return render(request, 'create_brand.html')



@never_cache
def brand_list(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    brands = Brand.objects.all()
    context = {'brands': brands}
    return render(request, 'create_brand.html', context)

@never_cache
def brand_delete(request, brand_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
       
        brand.delete()
        return redirect('brand_list')

    return render(request, 'brand_delete.html', {'brand': brand})


from django.views.decorators.cache import cache_control



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def admin_logout(request):
    if request.user.is_authenticated and request.user.is_superuser:
        request.session.flush()
        logout(request)
        return redirect('admin_login')
    else:
        messages.info(request, "Please log in as admin")
        return render(request,'admin_login.html')
    

@never_cache
def list_orders(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    orders = Order.objects.all().order_by('-created_at')
    context = {
        'orders': orders,
    }

    return render(request, 'list_orders.html', context)

@never_cache
def order_detail(request, order_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    order = get_object_or_404(Order, id=order_id)
    orderaddress = get_object_or_404(OrderAddress, order=order)
    userprofile = Userprofile.objects.get(user=order.user)
    order.phone_number = userprofile.phone_number
    order_items = OrderItem.objects.filter(order=order)
    print(order.status)
    for order_item in order_items:
        order_item.subtotal = order_item.product.price * order_item.quantity
        print(order_item.subtotal)    
    context = {
        'order': order,
        'order_items': order_items,
        'orderaddress':orderaddress
    }

    return render(request, 'order_detail.html', context)

@never_cache
def update_status(request, order_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        status = request.POST.get('status')

        if status == 'Cancelled':
            # Update product and variant quantities
            for order_item in order.order_items.exclude(status='cancelled', is_cancelled=True):
                order_item.is_cancelled = True
                order_item.status = 'cancelled'
                order_item.variant.stock += order_item.quantity
                print(order_item.variant.stock)
                order_item.variant.save()
                order_item.save()

        if status == 'Delivered':
            # Update delivered_at field to the current time when changing status to 'delivered'
            order.delivered_at = timezone.now()
            for order_item in order.order_items.exclude(status='cancelled', is_cancelled=True):
                order_item.status = 'Delivered'
                order.is_paid = True
                order_item.save()        

        if status != 'cancelled':
            for order_item in order.order_items.exclude(status='cancelled', is_cancelled=True):
                order_item.status = status
                order_item.save()

        order.status = status
        order.save()

    return redirect('order_detail', order_id=order_id)

@never_cache
def coupon_list(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    search_query = request.GET.get('search')
    coupons = Coupons.objects.all().order_by('-valid_to')
    if search_query:
        coupons = coupons.filter(Q(coupon_code__icontains=search_query))
    context = {'coupons': coupons}
    return render(request, 'coupon.html', context)

@never_cache
def add_coupons(request):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        description = request.POST.get('description')
        minimum_amount = request.POST.get('minimum_amount')
        discount = request.POST.get('discount')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')

        # Check for empty fields
        if not (coupon_code and description and minimum_amount and discount and valid_from and valid_to):
            messages.error(request, "All fields are required.")
            return redirect('add_coupons')

        try:
            minimum_amount = int(minimum_amount)
            discount = int(discount)
        except ValueError:
            messages.error(request, "Minimum Amount and Discount must be integers.")
            return redirect('add_coupons')

        # Check if discount is greater than minimum amount
        if discount > minimum_amount:
            messages.error(request, "Discount cannot be greater than Minimum Amount.")
            return redirect('add_coupons')

        if valid_from > valid_to:
            messages.error(request, "Valid From date should not be greater than Valid To date.")
            return redirect('add_coupons')

        coupon = Coupons(
            coupon_code=coupon_code,
            description=description,
            minimum_amount=minimum_amount,
            discount=discount,
            valid_from=valid_from,
            valid_to=valid_to
        )
        coupon.save()
        messages.success(request, "Coupon added successfully.")
        return redirect('coupon_list')

    return render(request, 'add_coupon.html')

@never_cache
def edit_coupons(request, coupon_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    try:
        coupon = Coupons.objects.get(pk=coupon_id)
    except Coupons.DoesNotExist:
        return redirect('admin_coupons')

    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        description = request.POST.get('description')
        minimum_amount = request.POST.get('minimum_amount')
        discount = request.POST.get('discount')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')

        # Check for empty fields
        if not (coupon_code and description and minimum_amount and discount and valid_from and valid_to):
            messages.error(request, "All fields are required.")
            return redirect('edit_coupons', coupon_id=coupon_id)

        try:
            minimum_amount = int(minimum_amount)
            discount = int(discount)
        except ValueError:
            messages.error(request, "Minimum Amount and Discount must be integers.")
            return redirect('edit_coupons', coupon_id=coupon_id)

        # Check if discount is greater than minimum amount
        if discount > minimum_amount:
            messages.error(request, "Discount cannot be greater than Minimum Amount.")
            return redirect('edit_coupons', coupon_id=coupon_id)

        if valid_from > valid_to:
            messages.error(request, "Valid From date should not be greater than Valid To date.")
            return redirect('edit_coupons', coupon_id=coupon_id)

        coupon.coupon_code = coupon_code
        coupon.description = description
        coupon.minimum_amount = minimum_amount
        coupon.discount = discount
        coupon.valid_from = valid_from
        coupon.valid_to = valid_to

        coupon.save()

        return redirect('coupon_list')

    context = {'coupon': coupon}
    return render(request, 'edit_coupon.html', context)

@never_cache
def list_coupon(request, c_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    coupon = Coupons.objects.get(id=c_id)
    coupon.un_list = False
    coupon.save()
    return redirect('coupon_list')

@never_cache
def unlist_coupon(request, c_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    coupon = Coupons.objects.get(id=c_id)
    coupon.un_list = True
    coupon.save()
    return redirect('coupon_list')


@never_cache
def coupon_details(request, coupon_id):
    if request.user.is_anonymous and not request.user.is_superuser:
        return redirect('admin_login')
    coupon = get_object_or_404(Coupons, id=coupon_id)
    used_users = UserCoupons.objects.filter(coupon=coupon)
    is_expired = coupon.valid_to < timezone.now()
    context = {
        'coupon': coupon,
        'used_users': used_users,
        'is_expired': is_expired,
    }

    return render(request, 'coupon_details.html', context)

@never_cache
def week_sales(request):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    total_sales = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).aggregate(
        total_sales=Sum('total_amount'))['total_sales'] or 0

    total_orders = Order.objects.filter(created_at__range=(start_date, end_date)).count()
    success_orders = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).count()
    average_order_value = total_sales / success_orders if success_orders != 0 else 0
    delivered_products = OrderItem.objects.filter(order__status='Delivered', order__created_at__range=(start_date, end_date), order__is_ordered=True).values('product__name').annotate(total_quantity_sold=Sum('quantity'), total_revenue=Sum(F('quantity') * F('product__price'))
                                                                         # Calculate total revenue here using F expressions
                                                                         ).order_by('-total_quantity_sold')

    order_products = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).order_by(
        '-created_at')
    Month = end_date.month
    print(Month)

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'average_order_value': average_order_value,
        'delivered_products': delivered_products,
        'end_date': end_date,
        'order_products': order_products,
        'success_orders': success_orders,
        'month': Month
    }

    return render(request, 'weekly_sales.html', context)


def today_sales(request):
    current_datetime = datetime.now()
    current_day = current_datetime.strftime('%d')

    start_date = datetime.combine(current_datetime.date(), time.min)
    end_date = current_datetime

    total_sales = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).aggregate(
        total_sales=Sum('total_amount'))['total_sales'] or 0
    total_orders = Order.objects.filter(created_at__range=(start_date, end_date)).count()
    success_orders = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).count()
    average_order_value = total_sales / success_orders if success_orders != 0 else 0

    delivered_products = OrderItem.objects.filter(order__status='Delivered'
                                                  ,order__created_at__range=(start_date, end_date)
                                                  , order__is_ordered=True).values('product__name').annotate(total_quantity_sold=Sum('quantity')
                                                  ,total_revenue=Sum(F('quantity') * F('product__price'))).order_by('-total_quantity_sold')

    order_products = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).order_by(
        '-created_at')

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'success_orders': success_orders,
        'average_order_value': average_order_value,
        'delivered_products': delivered_products,
        'current_datetime': current_datetime,
        'current_day': current_day,
        'order_products': order_products,
    }
    return render(request, 'today_sales.html', context)

@never_cache
def current_year_sales(request):
    current_year = datetime.now().year
    start_date = datetime(current_year, 1, 1)
    end_date = datetime.now()

    total_sales = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0

    total_orders = Order.objects.filter(created_at__range=(start_date, end_date)).count()
    success_orders = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).count()
    average_order_value = total_sales / success_orders if success_orders != 0 else 0

    delivered_products = OrderItem.objects.filter(order__status='Delivered',
                                                     order__created_at__range=(start_date, end_date),
                                                     ).values('product__name'
                                                              ).annotate(total_quantity_sold=Sum('quantity'),
                                                                         total_revenue=Sum(
                                                                             F('quantity') * F('product__price'))
                                                                         # Calculate total revenue using F expressions
                                                                         ).order_by('-total_quantity_sold')

    order_products = Order.objects.filter(status='Delivered', created_at__range=(start_date, end_date)).order_by(
        '-created_at')

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'success_orders': success_orders,
        'average_order_value': average_order_value,
        'delivered_products': delivered_products,
        'current_year': current_year,
        'order_products': order_products,
    }

    return render(request, 'current_year_sales.html', context)

@never_cache
def stock_report(request):
    # Get all products with their variants
    products_with_variants = Product.objects.prefetch_related('variants').all()

    # Calculate total stock for each product
    product_stock_report = []
    for product in products_with_variants:
        total_stock = sum(variant.stock for variant in product.variants.all())
        variant_count = product.variants.count()
        product_stock_report.append({'product': product, 'total_stock': total_stock, 'variant_count': variant_count})
    
    # Pass the stock report data to the template
    context = {'product_stock_report': product_stock_report}

    # Render the template with the stock report data
    return render(request, 'stock_report.html', context)

@never_cache
def cancelled_report(request):
    cancelled_orders = OrderItem.objects.filter(status='cancelled')
    
    # Pass the stock report data to the template
    context = {'cancelled_orders': cancelled_orders}

    # Render the template with the stock report data
    return render(request, 'cancelled_report.html', context)


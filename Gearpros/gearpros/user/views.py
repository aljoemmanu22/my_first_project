from django.db import models
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import Userprofile, PasswordReset, Wallet, Wishlist
from django.contrib import messages, auth
from django.contrib.auth import authenticate,login,logout
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_control
import re
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from datetime import datetime
from django.utils import timezone
from django.core.mail import send_mail
import random
from django.urls import reverse
from django.http import JsonResponse
from admin_part.models import Brand, Coupons, Product, ProductImage, Variant, UserCoupons, Category, Reviews
from django.contrib.auth.decorators import login_required
from cart.models import Cart
from django.contrib.auth.mixins import LoginRequiredMixin
from cart.models import Address, OrderItem, Order, Cart
from django.views import View
from social_django.models import UserSocialAuth
from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Avg


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def home(request):
    print(f"User '{request.user.username}' logged in successfully.")
    brands = Brand.objects.all() 
    core_products = Product.objects.filter(is_blocked=False)
    product_data = []   

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            cart_item_count = cart_items.count()
        except Cart.DoesNotExist:
            cart_items = []
            cart_item_count = 0
    else:
        cart_items = []
        cart_item_count = 0

    selected_category_id = request.GET.get('category_id')
    if selected_category_id:
        selected_category = get_object_or_404(Category, id=selected_category_id)
        core_products = core_products.filter(categories=selected_category)

    search_query = request.GET.get('q')
    if search_query:
        core_products = core_products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )       

    for product in core_products:
        images = ProductImage.objects.filter(product=product)
        categories = product.categories.all()

        variant = product.variants.first()

        if images and variant:
            first_image = images.first()
            product_data.append({
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'size': variant.size,
                'color': variant.color,
                'stock': variant.stock,
                'categories': [category.name for category in categories],
                'image_url': first_image.image.url if first_image else None,
            })
            
    categories = Category.objects.all()     

    context = {'products': product_data, 'username': request.session.get('username'), 'brands': brands, 'cart_item_count': cart_item_count, 'categories': categories,}
    return render(request, 'index.html', context)


# @never_cache
# def Login(request):
#     if 'username' in request.session :
#         return redirect('/')
#     if request.method == 'POST':
#         email = request.POST.get('email')  
#         password = request.POST.get('password')
     
#         user = authenticate(request, username=email, password=password)
#         if user is not None and not user.is_superuser:
#             print(f"User '{user.username}' logged in successfully.")
#             request.session['username'] = user.username
#             request.session['email'] = user.email
#             login(request, user)
#             return redirect('/')
#         else:
#             messages.error(request, 'Invalid credentials')
#             return redirect('login')
#     return render(request,"login.html")


@never_cache
def Login(request):
    if 'username' in request.session:
        return redirect('/')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)
        if user is not None and not user.is_superuser:
            user_profile = Userprofile.objects.get(user=user)

            if user_profile.blocked:
                messages.error(request, 'Your account is blocked. Contact support for assistance.')
                return redirect('login')

            print(f"User '{user.username}' logged in successfully.")
            request.session['username'] = user.username
            request.session['email'] = user.email
            login(request, user)
            return redirect('/')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect('login')

    return render(request, "login.html")



@never_cache
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone_number = request.POST.get('phone_number')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("signup")

        try:
            if User.objects.get(username=username):
                messages.error(request, "Username already exists")
                return redirect("signup")
        except:
            pass

        try:
            if User.objects.get(email=email):
                messages.error(request, "Email already exists")
                return redirect("signup")
        except:
            pass

        if not re.match(r'^[\w.@+-]+$',username):
            messages.error(request, "Invalid username")
            return redirect("/signup")

        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, "Invalid email")
            return redirect("/signup")

        phone_validator = RegexValidator(
            regex=r'^\+?91?\d{10}$',
            message="Phone number must be entered in the format: '+91xxxxxxxxxx'. Up to 12 digits allowed."
        )
        try:
            phone_validator(phone_number)
        except ValidationError as e:
            messages.error(request, e)  
            return redirect("signup")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters")
            return redirect("/signup")
        
        
        if is_valid_password(password):
            pass
        else:
            messages.error(request, "Password does not contain spaces")
            return redirect("signup")
        
        request.session["email"]=email
        request.session["username"]=username
        request.session["password"]=password
        request.session["phone_number"]=phone_number

        send_otp_signup(request, email)
        return render(request,'otp_signup.html',{"email":email})
    
    return render(request, 'signup.html')
        

def send_otp_signup(request, email=None):
    if request.method == 'POST':
        email = email or request.POST.get('email')

        
        s = "".join(str(random.randint(0, 9)) for _ in range(4))
        request.session["otp"] = s
        request.session["otp_generated_at"] = str(timezone.now().isoformat())
        
        request.session['otp_verified'] = False

        send_mail("OTP for Sign up", s, 'emmanus9822@gmail.com', [email], fail_silently=False)

        messages.info(request, 'A new OTP has been sent to your email.')
        return redirect('otp_verification_signup')
    

        
def resend_otp_signup(request):
    if request.method == 'GET':
        email = request.session.get('email')

       
        new_otp = "".join(str(random.randint(0, 9)) for _ in range(4))
        request.session["otp"] = new_otp
        request.session["otp_generated_at"] = str(timezone.now().isoformat())
  
        request.session['otp_verified'] = False

    
        send_mail("New OTP for Sign up", new_otp, 'emmanus9822@gmail.com', [email], fail_silently=False)

       
        request.session['otp_resend'] = True

     
        redirect_url = reverse('otp_verification_signup') + f'?email={email}'
        return redirect(redirect_url)
    
    return JsonResponse({'error': 'Invalid request method'})


def otp_verification_signup(request):
    email = request.GET.get("email")

    if request.method == 'POST':
        otp_entered = request.POST.get("otp")
        otp_generated_at_str = request.session.get("otp_generated_at")

        if request.session.get('otp_verified'):
            messages.info(request, 'You have already verified the OTP.')
            return redirect('login')

        if request.session.get('otp_resend'):
            request.session['otp_resend'] = False
            messages.info(request, 'A new OTP has been sent to your email.')

        otp_generated_at = datetime.strptime(otp_generated_at_str, '%Y-%m-%dT%H:%M:%S.%f%z') if otp_generated_at_str else None

        expiry_time_in_seconds = 120

        if otp_generated_at is not None:
            if otp_entered == request.session.get("otp"):
                time_elapsed_in_seconds = (timezone.now() - otp_generated_at).total_seconds()
                remaining_time = expiry_time_in_seconds - time_elapsed_in_seconds

                if remaining_time > 0:
                    try:
                        email = request.session.get('email')
                        username = request.session.get('username')
                        password = request.session.get('password')
                        phone_number = request.session.get('phone_number')

                        user = User.objects.create_user(username=username, email=email, password=password)
                        user.save()
                        
                        userprofile = Userprofile.objects.create(user=user, phone_number=phone_number)
                        userprofile.save()
                        request.session['otp_verified'] = True

                        messages.success(request, 'Account created successfully')
                        request.session.flush()
                        return redirect('login')

                    except ValueError as e:
                        messages.error(request, str(e))
                        return render(request, 'otp_signup.html', {"email": email})
                else:
                    # OTP expired
                    request.session["otp"] = None
                    request.session["otp_generated_at"] = None
                    messages.error(request, "OTP expired. Please request a new OTP.")
                    return render(request, 'otp_signup.html', {"email": email})
            else:
                # User entered incorrect OTP
                # Store remaining time
                remaining_time = expiry_time_in_seconds - (timezone.now() - otp_generated_at).total_seconds()
                request.session['remaining_time'] = remaining_time
                messages.error(request, "Invalid OTP")
                return render(request, 'otp_signup.html', {"email": email})
        else:
            request.session['remaining_time'] = None
            messages.error(request, "OTP expired. Please request a new OTP.")
            return render(request, 'otp_signup.html', {"email": email})

    # Get remaining time from session if available
    remaining_time = request.session.get('remaining_time')

    return render(request, 'otp_signup.html', {"email": email, "remaining_time": remaining_time})


@login_required
def edit_profile(request):
    if not 'username' in request.session:
        return redirect('login')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')

        try:
            if User.objects.exclude(pk=request.user.pk).get(username=username):
                messages.error(request, "Username already exists")
                return redirect("edit_profile")
        except User.DoesNotExist:
            pass

        try:
            if User.objects.exclude(pk=request.user.pk).get(email=email):
                messages.error(request, "Email already exists")
                return redirect("edit_profile")
        except User.DoesNotExist:
            pass

        # Additional validation logic (similar to the signup view)

        # Update the user profile
        request.user.username = username
        request.user.email = email
        request.user.save()

        # Update the user's profile (assuming you have a UserProfile model)
        user_profile = request.user.userprofile
        user_profile.phone_number = phone_number
        user_profile.save()

        messages.success(request, "Profile updated successfully")
        return redirect("my_account")


from django.views.decorators.cache import cache_control

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def Logout(request):
    if request.method == 'POST':
        request.session.flush()
        logout(request)
        return redirect('login') 
    return redirect('home')


def product_detail(request, product_id):
    my_review = None
    has_ordered = False
    existing_review = None
    average_rating = 0
    product = get_object_or_404(Product, id=product_id)
    variants = Variant.objects.filter(product=product)
    images = ProductImage.objects.filter(product=product)
    categories = product.categories.all()
    stocks = 0
    for variant in variants:
        stocks += variant.stock

    reviews = Reviews.objects.filter(product=product)
    count = Reviews.objects.filter(product=product).count()

    try:
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        if average_rating:
            product.rating = average_rating
            product.save()
    except ObjectDoesNotExist:
        pass

    review_with_images = []
    for review in reviews:
        user = review.user  # Use the correct field name
        user_profile = User.objects.filter(id=user.id).first()
        if user_profile:
            # profile_image_url = user_profile.profile_image.url
            review_with_images.append((review))
    
    if request.user.is_authenticated:
        has_ordered = OrderItem.objects.filter(order__user=request.user, product=product, order__is_ordered=True).exists()

        existing_review = Reviews.objects.filter(user=request.user, product=product).exists()

        # logined user review
        try:
            my_review = Reviews.objects.get(user=request.user, product=product)
            print(my_review.comment)
        except ObjectDoesNotExist:
            pass


    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            cart_item_count = cart_items.count()
        except Cart.DoesNotExist:
            cart_items = []
            cart_item_count = 0
    else:
        cart_items = []
        cart_item_count = 0

    unique_colors = set()
    for variant in variants:
        if variant.stock > 0:
            unique_colors.add(variant.color)

    # Choose a default variant (e.g., the first available variant)
    default_variant = variants.filter(stock__gt=0).first()
    selected_variant_id = None
    selected_color = None

    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        selected_variant = get_object_or_404(Variant, id=variant_id)

        # Check if the selected variant belongs to the current product
        if selected_variant.product == product:
            selected_variant_id = variant_id
            selected_color = selected_variant.color

    context = {
        'product': product,
        'variants': variants,
        'categories': [category.name for category in categories],
        'images': images,
        'cart_item_count': cart_item_count,
        'unique_colors': unique_colors,
        'selected_variant_id': selected_variant_id,
        'selected_color': selected_color,
        'stocks': stocks,
        'reviews': reviews,
        'has_ordered': has_ordered,
        'existing_review': existing_review,
        'count': count,
        'my_review': my_review,
        'average_rating': average_rating,
        'review_with_images':review_with_images 
    }

    return render(request, 'product_detail.html', context)



class MyAccountView(LoginRequiredMixin, View):
    template_name = 'myaccount.html'

    def get(self, request, *args, **kwargs):

        #Get user data
        user_data = {
            'username': request.user.username,
            'email': request.user.email,
            'phone_number': request.user.userprofile.phone_number,
        }

        # Get user addresses
        addresses = Address.objects.filter(user=request.user)

        # Get user orders
        orders = Order.objects.filter(user=request.user)
        all_order_items = OrderItem.objects.filter(order__in=orders).order_by('-id')  # Sort by id in descending order
        for item in all_order_items:
            if item.order.discount > 0:
                item.subtotal = (item.product.price * item.quantity) - item.order.discount
                item.status = item.status
                item.id = item.id
            else:    
                item.subtotal = (item.product.price * item.quantity)
                item.status = item.status
                item.id = item.id
        
        #Get Coupens
        all_coupons = Coupons.objects.filter(un_list=False)
        # Get used coupons by the logged-in user
        used_coupons = UserCoupons.objects.filter(user=request.user, is_used=True)
        used_coupon_ids = used_coupons.values_list('coupon_id', flat=True)
        # Get used coupon objects
        used_coupon_objects = all_coupons.filter(id__in=used_coupon_ids)
        # Filter out expired coupons from available coupons
        current_time = timezone.now()
        available_coupons = all_coupons.exclude(id__in=used_coupon_ids).filter(valid_to__gt=current_time)
        # Get expired coupons
        expired_coupons = all_coupons.exclude(id__in=used_coupon_ids).filter(valid_to__lt=current_time)

        # Merge expired coupons with used coupons for displaying
        used_coupon_objects = used_coupon_objects.union(expired_coupons)

        
        #wallet details
        current_user = request.user
        try:
            wallet = Wallet.objects.get(user=current_user)
        except Wallet.DoesNotExist:
            wallet = Wallet.objects.create(user=current_user, amount=0)
        wallet_amount = wallet.amount
        print(wallet_amount)


        return render(request, self.template_name, {'user_data': user_data, 'addresses': addresses, 'orders': all_order_items, 'used_coupons': used_coupon_objects, 'available_coupons': available_coupons, 'wallet_amount': wallet_amount})


@login_required
def view_wishlist(request):
    wishlist = Wishlist.objects.get_or_create(user=request.user)[0]
    return render(request, 'wishlist.html', {'wishlist': wishlist})

@login_required
def add_to_wishlist(request, product_id):
    product = Product.objects.get(pk=product_id)
    wishlist = Wishlist.objects.get_or_create(user=request.user)[0]
    wishlist.products.add(product)
    return redirect('view_wishlist')

@login_required
def remove_from_wishlist(request, product_id):
    product = Product.objects.get(pk=product_id)
    wishlist = Wishlist.objects.get_or_create(user=request.user)[0]
    wishlist.products.remove(product)
    return redirect('view_wishlist')


import re


def is_valid_comment(comment):
    # Check if the comment contains only spaces and special characters
    return not re.match(r'^[\s!@#$%^&*(),.?":{}|<>]*$', comment)


def add_review(request, p_id):
    if not 'username' in request.session:
        return redirect('login')

    product = get_object_or_404(Product, id=p_id)
    user = request.user
    existing_review = Reviews.objects.filter(user=user, product=product).exists()

    if request.method == 'POST' and not existing_review:
        comment = request.POST.get('comment')
        star = request.POST.get('rating')

        if comment and is_valid_comment(comment):
            review = Reviews(user=user, product=product, comment=comment, rating=star)
            review.save()
        else:
            messages.error(request, 'Invalid comment. Please enter a valid comment.')

    return redirect('product_detail', product_id=p_id)


def edit_review(request, review_id):
    if not 'username' in request.session:
        return redirect('login')

    review = get_object_or_404(Reviews, pk=review_id)
    user = request.user

    if user == review.user:
        if request.method == 'POST':
            comment = request.POST.get('comment')
            star = request.POST.get('rating')

            if comment and is_valid_comment(comment):
                review.comment = comment
                review.rating = star
                review.save()
            else:
                messages.error(request, 'Invalid comment. Please enter a valid comment.')

            return redirect('product_detail', product_id=review.product.id)



def delete_review(request, review_id):
    if not 'username' in request.session:
        return redirect('login')
    review = get_object_or_404(Reviews, pk=review_id)
    review.delete()
    return redirect('product_detail', product_id=review.product.id)


@never_cache
def contact(request):
    return render(request, 'contact.html')

@never_cache
def about(request):
    return render(request, 'about.html')

@never_cache
def changepass(request):
    return render(request, 'confirm_password.html')

@never_cache
def confirm_password(request):
    if request.method == "POST":
        password = request.POST.get('password1')
        confirm_password = request.POST.get('password2')

        if password == confirm_password:
            email = request.session.get('email')
            print(email)
            user = User.objects.get(email=email)
            print(user)
            user.set_password(password)  # to change the password
            user.save()
            print('set')
            messages.success(request, 'Password reset successful')
            request.session.flush()
            return redirect('login')
        else:
            messages.warning(request, 'Passwords do not match')
            print('not set')
            return redirect("confirm_password")
    return render(request, 'confirm_password.html')




































def is_valid_password(password):
    password_regex = re.compile(r'^(?=.*[a-zA-Z0-9]).{8,}$')

    return bool(password_regex.match(password))



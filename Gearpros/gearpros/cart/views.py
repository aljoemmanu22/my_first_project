
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Product, Variant, Cart, CartItem, Address, Order, OrderItem, CancellationReason, ReturnRequest
from admin_part.models import UserCoupons
from user.models import Wallet
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from datetime import datetime, time, timedelta
from django.contrib import messages
from django.db import transaction
import razorpay
from django.conf import settings
from razorpay.errors import BadRequestError
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from admin_part.models import Coupons
from django.http import JsonResponse
from decimal import Decimal
from django.views.decorators.cache import never_cache
from django.http import HttpResponseRedirect
from django.urls import reverse

@never_cache
@login_required
def cart_list(request):
    if not 'username' in request.session:
        return redirect('login')
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_item_id = request.POST.get('cart_item_id')
        quantity = request.POST.get('quantity')
        
        if cart_item_id and quantity:
            cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
            cart_item.quantity = int(quantity)
            cart_item.save()

            return JsonResponse({'success': True})
    
    cart_items = CartItem.objects.filter(cart__user=request.user) 
    for item in cart_items:
        item.subtotal = (item.product.price * item.quantity)

    total = sum(item.product.price * item.quantity for item in cart_items)

    context = {
        'cart_items': cart_items,
        'total': total,
    }

    return render(request, 'cart_list.html', context)

from django.http import JsonResponse

from django.db.models import F, ExpressionWrapper, DecimalField


@never_cache
@login_required
def cart_totals(request):
    cart_items = CartItem.objects.filter(cart__user=request.user)
    
    # Calculate subtotal for each item and update it in the queryset
    cart_items = cart_items.annotate(subtotal=ExpressionWrapper(F('product__price') * F('quantity'), output_field=DecimalField()))

    # Calculate the overall subtotal and total
    cart_subtotal = sum(item.subtotal for item in cart_items)
    cart_total = cart_subtotal  # Add shipping or any other costs here

    # Prepare data for each cart item
    cart_items_data = {item.id: item.subtotal for item in cart_items}

    context = {
        'cart_subtotal': cart_subtotal,
        'cart_total': cart_total,
        'cart_items': cart_items_data,
    }

    return JsonResponse(context)



@require_POST
@login_required
def add_to_cart(request):
    if not 'username' in request.session:
        return redirect('login')
    product_id = request.POST.get('product_id')
    variant_id = request.POST.get('variant_id')
    quantity = request.POST.get('quantity', 1)

    product = get_object_or_404(Product, id=product_id)

    if variant_id and variant_id != 'None':
        variant = get_object_or_404(Variant, id=variant_id, product=product)
    else:
        messages.error(request, 'Please select a valid variant.')
        return redirect('product_detail', product_id=product_id)
    

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)

    if not item_created:
        if cart_item.variant == variant:
            cart_item.quantity += int(quantity)
            cart_item.save()

    return redirect('cart_list')


@require_POST
@login_required
def remove_from_cart(request, cart_item_id):
    if not 'username' in request.session:
        return redirect('login')
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('cart_list')

@login_required
def checkout(request):        
    if not 'username' in request.session:
        return redirect('login')
    cart_items = CartItem.objects.filter(cart__user=request.user) 
    for item in cart_items:
        item.subtotal = (item.product.price * item.quantity)

    total = sum(item.product.price * item.quantity for item in cart_items)
    addresses = Address.objects.filter(user=request.user)
    if 'discount' in request.session:
        discount = request.session.get('discount')
        # del request.session['discount']
        total = int(float(total) - float(discount))
        context = {
        'cart_items': cart_items,
        'total': total,
        'addresses':addresses,
        'discount' :discount
        }
    else:
        context = {
            'cart_items': cart_items,
            'total': total,
            'addresses':addresses
        }

    return render(request, 'cart_checkout.html', context)

@login_required
def apply_coupon(request):
    if not 'username' in request.session:
        return redirect('login')
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        request.session['coupon_code'] = coupon_code
        total = float(request.POST.get('total'))
        total = int(total)
        cart_items = CartItem.objects.filter(cart__user=request.user) 
        for item in cart_items:
            item.subtotal = (item.product.price * item.quantity)
        addresses = Address.objects.filter(user=request.user)
        try:
            coupon = Coupons.objects.get(coupon_code=coupon_code, un_list=False)
            if coupon.valid_from <= timezone.now() <= coupon.valid_to:
                if total >= coupon.minimum_amount:
                    if coupon.is_used_by_user(request.user):
                        messages.warning(request, 'Coupon has already been Used')
                        print('Coupon has already been Used')
                    else:
                        total = int(float(total) - float(coupon.discount))
                        request.session['total'] = total
                        discount = float(coupon.discount)
                        request.session['discount'] = discount
                        request.session['coupon_discount'] = float(coupon.discount)
                        request.session['applied_coupon_code'] = coupon.coupon_code
                        messages.success(request, 'Coupon successfully added')
                        return redirect('checkout')
                else:
                    messages.warning(request, 'Coupon is not Applicable for Order Total')
            else:
                messages.warning(request, 'Coupon is not Applicable for the current date')
        except ObjectDoesNotExist:
            messages.warning(request, 'Coupon code is Invalid')
            return redirect('checkout')
    return redirect('checkout')


@login_required
def remove_coupon(request):
    if not 'username' in request.session:
        return redirect('login')

    # Check if the coupon is applied
    if 'applied_coupon_code' in request.session:
        # Remove coupon-related session variables
        del request.session['coupon_code']
        del request.session['total']
        del request.session['discount']
        del request.session['coupon_discount']
        del request.session['applied_coupon_code']

        messages.success(request, 'Coupon successfully removed')
    else:
        messages.warning(request, 'No coupon applied')

    return redirect('checkout')


class AddressView(LoginRequiredMixin, View):
    template_name = 'address_form.html' 

    def get(self, request, *args, **kwargs):
        addresses = Address.objects.filter(user=request.user)
        return render(request, self.template_name, {'addresses': addresses})

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')

        if action == 'create':
            return self.create_address(request)
        elif action == 'delete':
            return self.delete_address(request)
        elif action == 'edit':
            return self.edit_address(request)

        return redirect('checkout')

    def create_address(self, request):
        new_address = Address(
            user=request.user,
            first_name=request.POST['firstname'],
            last_name=request.POST['lastname'],
            company_name=request.POST['companyname'],
            address=request.POST['billing_address'],
            address_line2=request.POST['billing_address2'],
            country=request.POST['country'],  
            city=request.POST['city'],
            state=request.POST['state'],
            postal_code=request.POST['postal_code'],
            phone_number=request.POST['phone_number'],  
            email_address=request.POST['email_address'],  
        )
        new_address.save()
        return redirect('checkout')

    def delete_address(self, request):
        address_id = request.POST.get('address_id')
        if address_id:
            address = get_object_or_404(Address, id=address_id, user=request.user)
            address.delete()
        return redirect('my_account')

    def edit_address(self, request):
        address_id = request.session.get('address_id')
        address_id = request.session.pop('address_id', None)
        if address_id:
            address = get_object_or_404(Address, id=address_id, user=request.user)

            if request.method == 'POST':
                address.first_name = request.POST['firstname']
                address.last_name = request.POST['lastname']
                address.company_name = request.POST['companyname']
                address.address = request.POST['billing_address']
                address.address_line2 = request.POST['billing_address2']
                address.country = request.POST['country']
                address.city = request.POST['city']
                address.state = request.POST['state']
                address.postal_code = request.POST['postal_code']
                address.phone_number = request.POST['phone_number']
                address.email_address = request.POST['email_address']
                address.save()
                if address.save: 
                    print('successful')

            return redirect('my_account')

@login_required
def edit_address_page(request):
    if not 'username' in request.session:
        return redirect('login')
    address_id = request.POST.get('address_id')
    print(address_id)
    request.session['address_id'] = address_id
    if address_id:
        address = get_object_or_404(Address, id=address_id, user=request.user)

    return render(request, 'edit_address.html', {'address': address})

@login_required
def confirm_order(request):
    if not 'username' in request.session:
        return redirect('login')
    if request.method == 'POST':
        payment_option = request.POST.get('payment_option')
        total = request.POST.get('total')
        print(type(total))
        print(total)
        request.session['payment_option'] = payment_option
        selected_address_id = request.POST.get('selected_address')
        print(selected_address_id)
        try:
            selected_address = Address.objects.get(id=selected_address_id)
            request.session['selected_address_id'] = selected_address.id
        except Address.DoesNotExist:
            print("The selected address does not exist. Please choose a valid address.")
            return redirect('checkout')


        cart_items = CartItem.objects.filter(cart__user=request.user)
        expected_delivery_date = datetime.now() + timedelta(days=4)
        for item in cart_items:
            item.subtotal = (item.product.price * item.quantity)
        context = {
            'cart_items': cart_items,
            'total': total,
            'payment_option': payment_option,
            'expected_delivery_date': expected_delivery_date,
            'selected_address': selected_address,
        }

        return render(request, 'confirm_order.html', context)

    return redirect('checkout')



class OrderView(LoginRequiredMixin, View):
    template_name = 'confirm_order.html'

    def get(self, request, *args, **kwargs):
        orders = Order.objects.filter(user=request.user, is_cancelled=False)
        cart_items = CartItem.objects.filter(cart__user=request.user)
        total_amount = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, self.template_name, {'orders': orders, 'total_amount': total_amount})
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')

        if action == 'place_order':
            return self.place_order(request)
        elif action == 'cancel_order':
            return self.cancel_order(request)
    

    def place_order(self, request):
        print('Place Order method is executed.')

        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        cart_items_count = int(cart_items.count())
        discount = 0 
        if 'coupon_discount' in request.session:
            total_amount = int(request.session.get('total'))
            discounts = int(request.session.get('coupon_discount'))
            discount = discounts / cart_items_count
            print('if coupon discounted')
            request.session.pop('total', None)
        else:
            total_amount = request.POST.get('total')
        print(type(total_amount))       
        print(total_amount)
        payment_option = request.session.get('payment_option')
        payment_option = request.session.pop('payment_option', None)
        selected_address_id = request.session.get('selected_address_id')
        selected_address = Address.objects.get(id=selected_address_id)
        selected_address_id = request.session.pop('selected_address_id', None)
        created_at = datetime.now()
        
        tax_rate = Decimal('18.00') / Decimal('100.00')  # Represent 18% as a Decimal

        tax = Decimal(total_amount) * tax_rate

        new_order = Order(user=request.user, total_amount=total_amount, status='Confirmed', address=selected_address, created_at=created_at, discount=discount, tax = tax, payment_option = payment_option)
        print(new_order)
        razorpay_order = None  # Initialize razorpay_order to None

        if payment_option == 'cash_on_delivery':
            new_order.is_paid = False
        else:
            razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = razorpay_client.order.create({
                'amount': int(total_amount * 100),
                'currency': 'INR',
                'payment_capture': '1',
            })

        if razorpay_order:
            new_order.razorpay_order_id = razorpay_order['id']
            print(new_order.razorpay_order_id)
            new_order.is_paid = True
        new_order.is_ordered = True

        with transaction.atomic():
            new_order.save()

            for item in cart_items:
                order_item = OrderItem(order=new_order, product=item.product, variant=item.variant, quantity=item.quantity)
                order_item.save()

                item.variant.stock -= item.quantity
                item.variant.save()

            cart_items.delete()
        applied_coupon_code = request.session.get('coupon_code')
        if applied_coupon_code:
            try:
                coupon = Coupons.objects.get(coupon_code=applied_coupon_code)
                used_coupons = UserCoupons(user=request.user, coupon=coupon, is_used=True)
                used_coupons.save()
                new_order.coupon_info = applied_coupon_code
                new_order.save()
            except Coupons.DoesNotExist:
                pass

        if 'coupon_discount' in request.session:
            del request.session['coupon_discount']

        messages.success(request, 'Your order has been placed successfully!')
        return redirect('order_list')





    def cancel_order(self, request):
        order_id = request.POST.get('order_id')
        order_item_id = request.POST.get('order_item_id')
        
        with transaction.atomic():
            if order_id and order_item_id:
                order_item = get_object_or_404(OrderItem, id=order_item_id, order__user=request.user, is_cancelled=False)
                order_item.is_cancelled = True
                order_item.save()

                # Restore the variant stock when canceling an order item
                order_item.variant.stock += order_item.quantity
                order_item.variant.save()

            elif order_id:
                order = get_object_or_404(Order, id=order_id, user=request.user, is_cancelled=False)
                order.is_cancelled = True
                order.save()

                # Restore the variant stocks for all items in the canceled order
                for order_item in order.order_items.filter(is_cancelled=False):
                    order_item.variant.stock += order_item.quantity
                    order_item.variant.save()

        return redirect('order_list')


@login_required
def update_order_status(request):
    if not 'username' in request.session:
        return redirect('login')
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        cart_items_count = int(cart_items.count())
        discount = 0 
        discounts = 0
        if 'coupon_discount' in request.session:
            total_amount = int(request.session.get('total'))
            discounts = int(request.session.get('coupon_discount'))
            print('if coupon discounted')
            request.session.pop('total', None)
        else:
            total_amount = sum(item.product.price * item.quantity for item in cart_items)
        print(type(total_amount))       
        print(total_amount)
        payment_option = request.session.get('payment_option')
        payment_option = request.session.pop('payment_option', None)
        selected_address_id = request.session.get('selected_address_id')
        selected_address = Address.objects.get(id=selected_address_id)
        selected_address_id = request.session.pop('selected_address_id', None)
        discount = Decimal(discounts) / Decimal(cart_items_count)
        created_at = datetime.now()
        
        tax_rate = Decimal('18.00') / Decimal('100.00')  # Represent 18% as a Decimal
        

        tax = Decimal(total_amount) * tax_rate
        
        new_order = Order(user=request.user, total_amount=total_amount, status='Confirmed', address=selected_address, discount=discount, payment_option=payment_option, created_at=created_at, tax = tax)
        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = razorpay_client.order.create({
            'amount': int(total_amount * 100),
            'currency': 'INR',
            'payment_capture': '1',
        })

        new_order.razorpay_order_id = razorpay_order['id']
        print(new_order.razorpay_order_id)
        new_order.is_paid = True    
        new_order.is_ordered = True

        with transaction.atomic():
            new_order.save()

            for item in cart_items:
                order_item = OrderItem(order=new_order, product=item.product, variant=item.variant, quantity=item.quantity)
                order_item.save()

                item.variant.stock -= item.quantity
                item.variant.save()

            cart_items.delete()
        applied_coupon_code = request.session.get('coupon_code')
        if applied_coupon_code:
            try:
                coupon = Coupons.objects.get(coupon_code=applied_coupon_code)
                used_coupons = UserCoupons(user=request.user, coupon=coupon, is_used=True)
                used_coupons.save()
                new_order.coupon_info = applied_coupon_code
                new_order.save()
            except Coupons.DoesNotExist:
                pass

        if 'coupon_discount' in request.session:
            del request.session['coupon_discount']
        # Include razorpay_order_id in the response
        return JsonResponse({'status': 'success', 'razorpay_order_id': razorpay_order['id']})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


def wallet_payment(request):
    cart = Cart.objects.get(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    cart_items_count = int(cart_items.count())
    discount = 0 
    discounts = 0
    if 'coupon_discount' in request.session:
        total_amount = int(request.session.get('total'))
        discounts = int(request.session.get('coupon_discount'))
        print('if coupon discounted')
        request.session.pop('total', None)
    else:
        total_amount = sum(item.product.price * item.quantity for item in cart_items)
    print(type(total_amount))       
    print(total_amount)
    payment_option = request.session.get('payment_option')
    payment_option = request.session.pop('payment_option', None)
    selected_address_id = request.session.get('selected_address_id')
    selected_address = Address.objects.get(id=selected_address_id)
    selected_address_id = request.session.pop('selected_address_id', None)
    discount = Decimal(discounts) / Decimal(cart_items_count)
    created_at = datetime.now()
    
    tax_rate = Decimal('18.00') / Decimal('100.00')  # Represent 18% as a Decimal
    

    tax = Decimal(total_amount) * tax_rate
    current_user = request.user
    try:
        wallet = Wallet.objects.get(user=current_user)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(user=current_user, amount=0)
    wallet_amount = wallet.amount
    
    if wallet_amount > total_amount:
        new_order = Order(user=request.user, total_amount=total_amount, status='Confirmed', address=selected_address, discount=discount, payment_option=payment_option, created_at=created_at, tax = tax)
        new_order.is_paid = True    

        with transaction.atomic():
            new_order.save()

            for item in cart_items:
                order_item = OrderItem(order=new_order, product=item.product, variant=item.variant, quantity=item.quantity)
                order_item.save()

                item.variant.stock -= item.quantity
                item.variant.save()
                wallet.amount -= total_amount  # Subtract the total_amount from the wallet's amount
                wallet.save()

            cart_items.delete()
    else:
        messages.warning(request, 'Not Enough Balance in Wallet')
        return redirect('checkout')

    applied_coupon_code = request.session.get('coupon_code')
    if applied_coupon_code:
        try:
            coupon = Coupons.objects.get(coupon_code=applied_coupon_code)
            used_coupons = UserCoupons(user=request.user, coupon=coupon, is_used=True)
            used_coupons.save()
        except Coupons.DoesNotExist:
            pass
        
    messages.success(request, 'Your order has been placed successfully!')
    response = HttpResponseRedirect(reverse('order_list'))
    response['Cache-Control'] = 'no-store'

    return response




class OrderItemListView(LoginRequiredMixin, View):
    template_name = 'order_list.html'

    def get(self, request, *args, **kwargs):
        orders = Order.objects.filter(user=request.user)
        all_order_items = OrderItem.objects.filter(order__in=orders).order_by('-id')  # Sort by id in descending order
        
        for item in all_order_items:
            if item.order.discount > 0:
                item.subtotal = (item.product.price * item.quantity) - item.order.discount
            else:    
                item.subtotal = (item.product.price * item.quantity)

        return render(request, self.template_name, {'order_items': all_order_items})
    

class ProductOrderDetailView(LoginRequiredMixin, View):
    template_name = 'order_item_detail.html'

    def get(self, request, *args, **kwargs):
        order_item_id = kwargs.get('order_item_id')
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order = order_item.order
        if order.discount > 0:
            order_item.subtotal = (order_item.product.price * order_item.quantity) - order.discount
        else:
            order_item.subtotal = (order_item.product.price * order_item.quantity)
        print(order_item.subtotal)
        order_item.created_at = order.created_at
        # order_item.status = order_item.status
        order_item.is_paid = order.is_paid

        order_item.return_option_available = self.is_return_option_available(order_item)

        return render(request, self.template_name, {'order_item': order_item, 'order': order})

    def is_return_option_available(self, order_item):
        if order_item.status != 'cancelled':
            # Check if the item is delivered
            if order_item.status == 'Delivered':
                # Calculate the number of days since delivery
                days_since_delivery = (timezone.now() - order_item.order.delivered_at).days
                # Return option available until 7 days after delivery
                return days_since_delivery <= 7
            else:
                # Return option available for non-cancelled items
                return True
        return False

    def post(self, request, *args, **kwargs):
        order_item_id = kwargs.get('order_item_id')
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order = order_item.order
        if 'return_reason' in request.POST:
            return_reason = request.POST.get('return_reason', '')

            # Create a ReturnRequest object
            return_request = ReturnRequest(user=request.user, order_item=order_item, reason=return_reason)
            return_request.save()

            # Update the status of the order_item to 'return requested'
            order_item.status = 'return requested'
            order_item.save()
            if order_item.order.is_paid:
                user_wallet = Wallet.objects.get(user=request.user)
                if order_item.order.discount > 0 :
                    refunded_amount = (order_item.product.price * order_item.quantity) - order_item.order.discount
                else:    
                    refunded_amount = order_item.product.price * order_item.quantity
                with transaction.atomic():
                    user_wallet.amount += refunded_amount
                    user_wallet.save()

                    messages.success(request, f'Order item canceled. Refunded ${refunded_amount:.2f} to your wallet.')

                    # Check if the order contains only one item, then update the order status
                    if order_item.order.order_items.count() == 1:
                        order_item.order.status = "return requested"
                        order_item.order.save()
                        
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error'})
    

class CancelOrderItemView(LoginRequiredMixin, View):
    def post(self, request, order_item_id, *args, **kwargs):
        order_item = get_object_or_404(OrderItem, id=order_item_id)

        if not order_item.is_cancelled:
            with transaction.atomic():
                order_item.is_cancelled = True
                order_item.status = "cancelled"
                order_item.save()

                # Create a CancellationReason entry
                reason = request.POST.get('cancellation_reason', '')
                if reason:
                    cancellation_reason = CancellationReason(user=request.user, order_item=order_item, reason=reason)
                    cancellation_reason.save()

                # Update the variant stock
                order_item.variant.stock += order_item.quantity
                order_item.variant.save()

                # Check if the order is paid and update wallet
                if order_item.order.is_paid:
                    user_wallet = Wallet.objects.get(user=request.user)
                    if order_item.order.discount > 0 :
                        refunded_amount = (order_item.product.price * order_item.quantity) - order_item.order.discount
                    else:    
                        refunded_amount = order_item.product.price * order_item.quantity
    
                    with transaction.atomic():
                        user_wallet.amount += refunded_amount
                        user_wallet.save()

                        messages.success(request, f'Order item canceled. Refunded ${refunded_amount:.2f} to your wallet.')

                        # Check if the order contains only one item, then update the order status
                        if order_item.order.order_items.count() == 1:
                            order_item.order.status = "cancelled"
                            order_item.order.save()
                            messages.success(request, 'Order canceled as it contained only one item.')

        return redirect('my_account')
    
    
def invoice(request, order_item_id):

    order_item = get_object_or_404(OrderItem, id=order_item_id)
    order = order_item.order
    order_items = OrderItem.objects.filter(order_id=order.id)
    counts = order_items.count()
    for order_item in order_items:
        if order.discount > 0:
            order_item.subtotal = (order_item.product.price * order_item.quantity) - order.discount
        else:
            order_item.subtotal = (order_item.product.price * order_item.quantity)
            print(order_item.subtotal)
    order.coupon_dis = counts * order.discount        
    return render(request, 'invoice.html', {'order_items': order_items, 'order': order})
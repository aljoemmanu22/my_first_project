from django.db import models
from django.contrib.auth.models import User
from admin_part.models import Product, Variant
from django.urls import reverse
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    items = models.ManyToManyField('CartItem', related_name='cart_items')  # Use a different related_name

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_absolute_url(self):
        return reverse("cart:cart_detail")

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items', default=1)  # Set a default value
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.variant.size}, {self.variant.color})"

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company_name = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255)
    country = models.CharField(max_length=50)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    email_address = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.user.username}'s Address"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey('OrderAddress', on_delete=models.SET_NULL, blank=True, null=True, related_name='orders')
    items = models.ManyToManyField('OrderItem', related_name='order_items')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    status = models.TextField(max_length=50, default="Confirmed")
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    discount = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    order_number = models.CharField(max_length=200, default=1)
    is_ordered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(blank=True, null=True)
    payment_option = models.CharField(max_length=50, blank=True, null=True)
    coupon_info = models.CharField(max_length=50, blank=True, null=True)
    tax = models.DecimalField(default=0, decimal_places=2, max_digits=10)

    def __str__(self):
        return f"Order for {self.user.username} - Total Amount: {self.total_amount}"

    def get_absolute_url(self):
        return reverse("order:order_detail", kwargs={"pk": self.pk})

class OrderAddress(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_addresses')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company_name = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255)
    country = models.CharField(max_length=50)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    email_address = models.CharField(max_length=50)

    def __str__(self):
        return f"Address for Order {self.order.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    is_cancelled = models.BooleanField(default=False)  # New field for item cancellation status
    status = models.TextField(max_length=50, default="Confirmed")
    cancellation_reason = models.ForeignKey('CancellationReason', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items_cancellation_reason')


    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.variant.size}, {self.variant.color})"



class CancellationReason(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_item = models.OneToOneField('OrderItem', on_delete=models.CASCADE, related_name='cancellation_reason_entry')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation Reason for Order Item {self.order_item.id} by {self.user.username}"
    


class ReturnRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Return Request #{self.id} for Order Item #{self.order_item.id}"    
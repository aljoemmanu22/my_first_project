
from datetime import timezone
from django.contrib.auth.models import User
from django.db import models




class Brand(models.Model):
    name = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='brand_logos/', null=True, blank=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    brand = models.ForeignKey(Brand, related_name='products', on_delete=models.SET_NULL, null=True, blank=True)
    categories = models.ManyToManyField(Category, related_name='products')
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Variant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    size = models.CharField(max_length=50, null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color}"

class ProductImage(models.Model):
    DEFAULT_IMAGE_PATH = 'product_images/default/default_image.jpg'

    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    image = models.ImageField(
        upload_to='product_images/',
        default=DEFAULT_IMAGE_PATH
    )


class UserCoupons(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    coupon = models.ForeignKey('Coupons', on_delete=models.CASCADE)
    is_used = models.BooleanField(default=True)

    def __str__(self):
        return self.coupon.coupon_code


class Coupons(models.Model):
    coupon_code = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    minimum_amount = models.IntegerField(default=10000)
    discount = models.IntegerField(default=0)
    is_expired = models.BooleanField(default=False)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    un_list= models.BooleanField(default=False)

    def __str__(self):
        return self.coupon_code

    def is_valid(self):
        now = timezone.now()
        return now >= self.valid_from and now <= self.valid_to


    def is_used_by_user(self, user):
        redeemed_details = UserCoupons.objects.filter(coupon=self, user=user, is_used=True)
        return redeemed_details.exists()
    

class Reviews(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    comment=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    rating=models.IntegerField()
    def __str__(self):
        return f"comment of  {self.user.username} on {self.product.product_name}"

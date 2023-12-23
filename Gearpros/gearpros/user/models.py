from django.db import models
from django.contrib.auth.models import User
from admin_part.models import Product


class Userprofile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    blocked = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
    

class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100)
    expiry_date = models.DateTimeField()


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.user.username}"

class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='wishlist')

    def __str__(self):
        return f"Wishlist for {self.user.username}"

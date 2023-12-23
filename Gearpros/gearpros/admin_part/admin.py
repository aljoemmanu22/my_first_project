# Register your models here.
from django.contrib import admin
from . import models
# Register your models here.

admin.site.register(models.Category)
admin.site.register(models.Product)
admin.site.register(models.ProductImage)
admin.site.register(models.Brand)
admin.site.register(models.Variant)
admin.site.register(models.UserCoupons)
admin.site.register(models.Coupons)
# Generated by Django 4.2.7 on 2023-12-08 07:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0009_order_razorpay_order_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

# Generated by Django 4.2.7 on 2023-12-09 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0011_order_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_ordered',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='order_number',
            field=models.CharField(default=1, max_length=200),
        ),
    ]

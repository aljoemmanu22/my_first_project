# Generated by Django 4.2.7 on 2024-01-04 12:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0016_order_tax'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('company_name', models.CharField(max_length=50)),
                ('address', models.CharField(max_length=255)),
                ('address_line2', models.CharField(max_length=255)),
                ('country', models.CharField(max_length=50)),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=50)),
                ('postal_code', models.CharField(max_length=20)),
                ('phone_number', models.CharField(max_length=20)),
                ('email_address', models.CharField(max_length=50)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_addresses', to='cart.order')),
            ],
        ),
        migrations.AlterField(
            model_name='order',
            name='address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='cart.orderaddress'),
        ),
    ]

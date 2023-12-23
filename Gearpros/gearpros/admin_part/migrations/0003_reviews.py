# Generated by Django 4.2.7 on 2023-12-20 04:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admin_part', '0002_coupons_usercoupons'),
    ]

    operations = [
        migrations.CreateModel(
            name='Reviews',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rating', models.IntegerField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='admin_part.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

from django.urls import path
from . import views

urlpatterns=[
    path('admin_login/',views.admin_login,name='admin_login'),
    path('admin_home/',views.admin_home,name='admin_home'),
    path('admin_logout/',views.admin_logout,name='admin_logout'),

    path('user_list/',views.user_list,name='user_list'),
    path('block_user/<int:user_id>/', views.block_user, name='block_user'),

    path('create_category/', views.create_category, name='create_category'),
    path('category_list/', views.category_list, name='category_list'),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete_category/<int:category_id>/', views.delete_category, name='delete_category'),

    path('create_product/', views.create_product, name='create_product'),
    path('product_list/', views.product_list, name='product_list'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('block_product/<int:product_id>/', views.block_product, name='block_product'),

    path('brands/', views.brand_list, name='brand_list'),
    path('brands/create/', views.create_brand, name='create_brand'),
    path('brands/<int:brand_id>/delete/', views.brand_delete, name='brand_delete'),

    path('list_orders/', views.list_orders, name='list_orders'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('update_status/<int:order_id>/', views.update_status, name='update_status'),

    path('coupon_list/', views.coupon_list, name='coupon_list'),
    path('add_coupons/', views.add_coupons, name='add_coupons'),
    path('edit_coupons/<int:coupon_id>/', views.edit_coupons, name='edit_coupons'),
    path('unlist_coupon/<int:c_id>/', views.unlist_coupon, name='unlist_coupon'),
    path('list_coupon/<int:c_id>/', views.list_coupon, name='list_coupon'),
    path('coupon_details/<int:coupon_id>/', views.coupon_details, name='coupon_details'),

    path('week_sales/', views.week_sales, name='week_sales'),
    path('today_sales/',views.today_sales,name='today_sales'),
    path('current_year_sales/',views.current_year_sales,name='current_year_sales'),
    path('stock_report/', views.stock_report, name='stock_report'),
    path('cancelled_report/', views.cancelled_report, name='cancelled_report'),
]
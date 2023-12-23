from django.urls import path, include
from . import views
from .views import AddressView

urlpatterns = [ 
    path('cart/', views.cart_list, name='cart_list'),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart_totals/', views.cart_totals, name='cart_totals'),

    
    path('addresses/', AddressView.as_view(), name='address-list'),
    path('edit_address_page/', views.edit_address_page, name='edit_address_page'),

    path('checkout/', views.checkout, name='checkout'),
    path('confirm_order/', views.confirm_order, name='confirm_order'),
    path('order/', views.OrderView.as_view(), name='order'),
    path('update_order_status/', views.update_order_status, name='update_order_status'),
    path('wallet_payment/', views.wallet_payment, name='wallet_payment'),

    path('order_list/', views.OrderItemListView.as_view(), name='order_list'),
    path('product_order_detail/<int:order_item_id>/', views.ProductOrderDetailView.as_view(), name='product_order_detail'),
    path('invoice/<int:order_item_id>/', views.invoice, name='invoice'),
    path('cancel_order_item/<int:order_item_id>/', views.CancelOrderItemView.as_view(), name='cancel_order_item'),
    path('return_order_item/<int:order_item_id>/', views.ProductOrderDetailView.as_view(), name='return_order_item'),
    
    path('apply_coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove_coupon/', views.remove_coupon, name='remove_coupon'),
]    
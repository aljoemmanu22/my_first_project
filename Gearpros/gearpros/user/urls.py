from django.urls import path, include
from . import views
from cart.views import ProductOrderDetailView
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetCompleteView
from django.contrib.auth import views as auth_views
from social_django.views import complete

urlpatterns=[
    path('',views.home,name='home'),
    path('login/',views.Login,name='login'),
    path('complete/google-oauth2/', complete, name='social_complete_google_oauth2'),
    path('social/', include('social_django.urls', namespace='social')),
    path('signup/',views.signup,name='signup'),
    path('logout/',views.Logout,name='logout'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('signup/otp_verification_signup', views.otp_verification_signup, name='otp_verification_signup'),
    path('resend-otp/', views.resend_otp_signup, name='resend_otp_signup'),
    path('my_account/', views.MyAccountView.as_view(), name='my_account'),
    path('edit_profile', views.edit_profile, name='edit_profile'),
    path('product_order_detail/<int:order_item_id>/', ProductOrderDetailView.as_view(), name='product_order_detail'),
    
    path('password_reset/', PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset/complete/', PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('confirm_password/', views.confirm_password, name='confirm_password'),
    path('changepass/', views.changepass, name='changepass'),



    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<int:product_id>/',  views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/',  views.remove_from_wishlist, name='remove_from_wishlist'),

    path('add_review/<int:p_id>/', views.add_review, name='add_review'),
    path('edit_review/<int:review_id>/', views.edit_review, name='edit_review'),
    path('delete_review/<int:review_id>/', views.delete_review, name='delete_review'),

    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
]

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # URL cho trang đăng nhập/đăng xuất
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Trang chủ và các chức năng booking sẽ nằm ở root URL
    path('', include('booking.urls')),
]


from django.urls import path
from . import views

urlpatterns = [
    # Đường dẫn cho trang đăng ký chính
    path('', views.booking_page, name='booking_page'),
    
    # Đường dẫn xử lý việc tạo booking mới
    path('create/', views.create_booking, name='create_booking'),
    
    # Đường dẫn cho trang "Lịch của tôi"
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    
    # Đường dẫn xử lý việc hủy booking
    path('cancel/', views.cancel_booking, name='cancel_booking'),
]


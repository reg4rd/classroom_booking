from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Định nghĩa model cho Phòng học
class Room(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên phòng")
    capacity = models.PositiveIntegerField(verbose_name="Sức chứa", blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Phòng học"
        verbose_name_plural = "Các phòng học"
        ordering = ['name']

# Định nghĩa model cho Lịch đăng ký
class Booking(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Giáo viên")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name="Phòng học")
    date = models.DateField(verbose_name="Ngày dạy")
    # Giả sử trường có tối đa 10 tiết học/ngày
    period = models.PositiveIntegerField(verbose_name="Tiết học")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher.username} - {self.room.name} - Tiết {self.period} - Ngày {self.date.strftime('%d/%m/%Y')}"

    # Đảm bảo không có 2 lịch đăng ký trùng nhau cho cùng phòng, cùng ngày, cùng tiết
    class Meta:
        verbose_name = "Lịch đăng ký"
        verbose_name_plural = "Các lịch đăng ký"
        unique_together = ('room', 'date', 'period')
        ordering = ['date', 'period', 'room']

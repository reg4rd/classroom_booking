from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count
from .models import Room, Booking
from datetime import date, timedelta
from itertools import groupby

# Cài đặt ngày bắt đầu của học kỳ để tính tuần
SEMESTER_START_DATE = date(2025, 9, 8)

def get_valid_dates():
    today = date.today()
    valid_dates_info = []
    for i in range(14):
        current_date = today + timedelta(days=i)
        if current_date.weekday() != 6:
            days_since_start = (current_date - SEMESTER_START_DATE).days
            week_number = (days_since_start // 7) + 1 if days_since_start >= 0 else 1
            valid_dates_info.append({'date': current_date, 'week': week_number})
    return valid_dates_info

@login_required
def booking_page(request):
    valid_dates_info = get_valid_dates()
    
    selected_date_str = request.GET.get('selected_date')
    session = request.GET.get('session', 'sang')
    search_room = request.GET.get('search_room', '')
    search_periods_str = request.GET.getlist('search_periods')
    search_periods = [int(p) for p in search_periods_str if p.isdigit()]

    if selected_date_str:
        selected_date = date.fromisoformat(selected_date_str)
    else:
        selected_date = valid_dates_info[0]['date'] if valid_dates_info else date.today()

    if session == 'chieu':
        periods = range(6, 11)
    else:
        periods = range(1, 6)

    rooms = Room.objects.all().order_by('name')
    if search_room:
        rooms = rooms.filter(name__icontains=search_room)

    if search_periods:
        booked_room_ids = Booking.objects.filter(
            date=selected_date,
            period__in=search_periods
        ).values_list('room_id', flat=True).distinct()
        rooms = rooms.exclude(id__in=booked_room_ids)

    bookings_on_date = Booking.objects.filter(date=selected_date).select_related('teacher')
    
    bookings_in_session = bookings_on_date.filter(period__in=periods)

    booking_map = {
        (b.room_id, b.period): b.teacher.get_full_name() or b.teacher.username 
        for b in bookings_in_session
    }

    grid = []
    for room in rooms:
        row = {'room': room, 'period_data': []}
        for period in periods:
            teacher = booking_map.get((room.id, period))
            row['period_data'].append({'period': period, 'teacher': teacher})
        grid.append(row)

    all_rooms_count = Room.objects.count()
    total_bookings_in_session = bookings_in_session.count()
    user_bookings_in_session = bookings_in_session.filter(teacher=request.user).count()

    context = {
        'grid': grid,
        'periods': periods,
        'valid_dates_info': valid_dates_info,
        'selected_date': selected_date,
        'search_periods': search_periods,
        'search_room': search_room,
        'session': session,
        'rooms_count': all_rooms_count,
        'total_bookings_in_session': total_bookings_in_session,
        'user_bookings_in_session': user_bookings_in_session,
    }
    return render(request, 'booking/booking_page.html', context)

@login_required
@require_POST
def create_booking(request):
    selected_date_str = request.POST.get('selected_date')
    room_id = request.POST.get('room_id')
    selected_periods = request.POST.getlist('periods')
    redirect_url = request.META.get('HTTP_REFERER', f'/?selected_date={selected_date_str}')

    if not all([selected_date_str, room_id, selected_periods]):
        messages.error(request, "Yêu cầu không hợp lệ. Vui lòng chọn ít nhất một tiết học.")
        return redirect(redirect_url)

    success_count = 0
    conflict_periods = []
    
    try:
        room = Room.objects.get(id=room_id)
        selected_date = date.fromisoformat(selected_date_str)
        
        with transaction.atomic():
            for period_str in selected_periods:
                period = int(period_str)
                if Booking.objects.filter(room=room, date=selected_date, period=period).exists():
                    session_display = 'chiều' if period > 5 else 'sáng'
                    period_display = period if period <= 5 else period - 5
                    conflict_periods.append(f"Tiết {period_display} ({session_display})")
                else:
                    Booking.objects.create(
                        teacher=request.user,
                        room=room,
                        date=selected_date,
                        period=period
                    )
                    success_count += 1
    except Room.DoesNotExist:
        messages.error(request, "Phòng học không tồn tại.")
    except Exception as e:
        messages.error(request, f"Đã xảy ra lỗi không mong muốn: {e}")

    if success_count > 0:
        messages.success(request, f"Đã đăng ký thành công {success_count} tiết tại phòng {room.name}.")
    if conflict_periods:
        messages.warning(request, f"Các tiết sau đã có người khác đăng ký: {', '.join(conflict_periods)}.")

    return redirect(f"{redirect_url}#room-{room_id}")


@login_required
def my_bookings(request):
    today = date.today()
    user_bookings = Booking.objects.filter(teacher=request.user, date__gte=today).order_by('date', 'room__name', 'period')
    
    grouped_bookings = []

    # Hàm key để gom nhóm, bao gồm cả buổi học
    def group_key(booking):
        session = "Sáng" if booking.period <= 5 else "Chiều"
        return (booking.date, booking.room, session)

    # Gom nhóm theo ngày, phòng, VÀ buổi học
    for key, group in groupby(user_bookings, key=group_key):
        date_obj, room_obj, session_name = key
        bookings_in_group = list(group)
        
        periods = [b.period for b in bookings_in_group]
        booking_ids = ",".join(str(b.id) for b in bookings_in_group)
        
        grouped_bookings.append({
            'date': date_obj,
            'room': room_obj,
            'session': session_name,
            'periods': periods,
            'booking_ids': booking_ids
        })

    context = {'grouped_bookings': grouped_bookings}
    return render(request, 'booking/my_bookings.html', context)


@login_required
@require_POST
def cancel_booking(request):
    booking_ids_str = request.POST.get('booking_ids')
    if booking_ids_str:
        booking_ids = [int(id) for id in booking_ids_str.split(',')]
        bookings_to_delete = Booking.objects.filter(id__in=booking_ids, teacher=request.user)
        count = bookings_to_delete.count()
        if count > 0:
            bookings_to_delete.delete()
            messages.success(request, f"Đã hủy thành công {count} tiết học.")
        else:
            messages.error(request, "Không tìm thấy lịch đăng ký hoặc bạn không có quyền hủy.")
    else:
        messages.error(request, "Yêu cầu không hợp lệ.")
        
    return redirect('my_bookings')


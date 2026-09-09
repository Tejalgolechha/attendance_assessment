import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from attendance.models import Employee, Attendance
from attendance.calculator import SHIFT_GS, SHIFT_NS


class Command(BaseCommand):
    help = 'Seeds initial employee and attendance data for demo'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo employee and attendance data...')

        # Employees
        emp1, _ = Employee.objects.get_or_create(
            employee_id='EMP001',
            defaults={'name': 'Alice Johnson', 'shift': SHIFT_GS}
        )
        emp2, _ = Employee.objects.get_or_create(
            employee_id='EMP002',
            defaults={'name': 'Bob Smith', 'shift': SHIFT_NS}
        )
        emp3, _ = Employee.objects.get_or_create(
            employee_id='EMP003',
            defaults={'name': 'Charlie Davis', 'shift': SHIFT_GS}
        )

        # Users
        u1, created1 = User.objects.get_or_create(username='emp001')
        if created1:
            u1.set_password('password123')
            u1.save()
            emp1.user = u1
            emp1.save()

        u2, created2 = User.objects.get_or_create(username='emp002')
        if created2:
            u2.set_password('password123')
            u2.save()
            emp2.user = u2
            emp2.save()

        u3, created3 = User.objects.get_or_create(username='emp003')
        if created3:
            u3.set_password('password123')
            u3.save()
            emp3.user = u3
            emp3.save()

        # Admin user
        admin_u, created_admin = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
        if created_admin:
            admin_u.set_password('admin123')
            admin_u.save()

        tz = timezone.get_current_timezone()
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        prev_day = today - datetime.timedelta(days=2)

        # Sample Attendance Records
        if Attendance.objects.count() == 0:
            # 1. GS Full Day (Present) - Yesterday
            Attendance.objects.create(
                employee=emp1,
                attendance_date=yesterday,
                shift=SHIFT_GS,
                punch_in=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(12, 0, 0)), tz),
                punch_out=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(21, 0, 0)), tz)
            )

            # 2. NS Full Night Shift (Present across midnight) - Yesterday night
            Attendance.objects.create(
                employee=emp2,
                attendance_date=yesterday,
                shift=SHIFT_NS,
                punch_in=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(21, 30, 0)), tz),
                punch_out=timezone.make_aware(datetime.datetime.combine(today, datetime.time(6, 30, 0)), tz)
            )

            # 3. GS First Half Only (Half Day) - Yesterday
            Attendance.objects.create(
                employee=emp3,
                attendance_date=yesterday,
                shift=SHIFT_GS,
                punch_in=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(12, 0, 0)), tz),
                punch_out=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(16, 30, 0)), tz)
            )

            # 4. GS Full Day - Previous Day
            Attendance.objects.create(
                employee=emp1,
                attendance_date=prev_day,
                shift=SHIFT_GS,
                punch_in=timezone.make_aware(datetime.datetime.combine(prev_day, datetime.time(12, 0, 0)), tz),
                punch_out=timezone.make_aware(datetime.datetime.combine(prev_day, datetime.time(21, 0, 0)), tz)
            )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully!'))

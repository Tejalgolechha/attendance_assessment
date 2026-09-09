import datetime
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Employee, Attendance
from .serializers import (
    EmployeeSerializer,
    AttendanceSerializer,
    PunchInSerializer,
    PunchOutSerializer,
    LoginSerializer
)
from .calculator import (
    determine_attendance_date,
    validate_punch_in_rules,
    validate_punch_out_rules,
    SHIFT_GS,
    SHIFT_NS
)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username_or_id = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Check if username matches an employee_id
        try:
            employee = Employee.objects.get(employee_id__iexact=username_or_id)
            user = employee.user
            if user:
                username = user.username
            else:
                username = username_or_id
        except Employee.DoesNotExist:
            username = username_or_id

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            employee_profile = getattr(user, 'employee_profile', None)
            emp_data = EmployeeSerializer(employee_profile).data if employee_profile else None
            return Response({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'is_staff': user.is_staff
                },
                'employee': emp_data
            })
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'})


class EmployeeListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        employees = Employee.objects.all().order_by('employee_id')
        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = EmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        return Response(EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED)


class EmployeeDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        try:
            return Employee.objects.get(pk=pk)
        except Employee.DoesNotExist:
            return None

    def get(self, request, pk):
        employee = self.get_object(pk)
        if not employee:
            return Response({'error': f'Employee #{pk} not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data)

    def patch(self, request, pk):
        employee = self.get_object(pk)
        if not employee:
            return Response({'error': f'Employee #{pk} not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EmployeeSerializer(employee, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_emp = serializer.save()
        return Response(EmployeeSerializer(updated_emp).data)

    def delete(self, request, pk):
        employee = self.get_object(pk)
        if not employee:
            return Response({'error': f'Employee #{pk} not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        emp_id = employee.employee_id
        user = employee.user
        employee.delete()
        if user:
            user.delete()

        return Response({'message': f'Employee {emp_id} deleted successfully.'}, status=status.HTTP_200_OK)


class PunchInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PunchInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee_id = serializer.validated_data['employee_id']
        punch_in_dt = serializer.validated_data.get('timestamp') or timezone.now()

        if timezone.is_naive(punch_in_dt):
            punch_in_dt = timezone.make_aware(punch_in_dt, timezone.get_current_timezone())

        try:
            employee = Employee.objects.get(employee_id__iexact=employee_id)
        except Employee.DoesNotExist:
            return Response({'error': f'Employee with ID {employee_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check existing active attendance
        active_record = Attendance.objects.filter(employee=employee, punch_out__isnull=True).first()
        existing_records = Attendance.objects.filter(employee=employee)

        # Validate rules
        validate_punch_in_rules(
            employee=employee,
            punch_in_dt=punch_in_dt,
            existing_active_record=active_record,
            existing_records=existing_records
        )

        attendance_date = determine_attendance_date(employee.shift, punch_in_dt)

        attendance = Attendance.objects.create(
            employee=employee,
            attendance_date=attendance_date,
            shift=employee.shift,
            punch_in=punch_in_dt,
            status='IN'
        )

        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)


class PunchOutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PunchOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee_id = serializer.validated_data['employee_id']
        punch_out_dt = serializer.validated_data.get('timestamp') or timezone.now()

        if timezone.is_naive(punch_out_dt):
            punch_out_dt = timezone.make_aware(punch_out_dt, timezone.get_current_timezone())

        try:
            employee = Employee.objects.get(employee_id__iexact=employee_id)
        except Employee.DoesNotExist:
            return Response({'error': f'Employee with ID {employee_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        active_record = Attendance.objects.filter(employee=employee, punch_out__isnull=True).first()

        punch_out_dt = validate_punch_out_rules(
            punch_in_dt=active_record.punch_in if active_record else None,
            punch_out_dt=punch_out_dt,
            shift_code=active_record.shift if active_record else None,
            attendance_date=active_record.attendance_date if active_record else None,
        )

        active_record.punch_out = punch_out_dt
        active_record.save()

        return Response(AttendanceSerializer(active_record).data, status=status.HTTP_200_OK)


class AttendanceDashboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Attendance.objects.all().select_related('employee')

        employee_id = request.query_params.get('employee_id')
        status_param = request.query_params.get('status')
        shift_param = request.query_params.get('shift')
        date_param = request.query_params.get('date')

        if employee_id:
            queryset = queryset.filter(employee__employee_id__icontains=employee_id)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if shift_param:
            queryset = queryset.filter(shift=shift_param)
        if date_param:
            queryset = queryset.filter(attendance_date=date_param)

        serializer = AttendanceSerializer(queryset, many=True)
        return Response(serializer.data)


class AttendanceDeleteView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        try:
            record = Attendance.objects.get(pk=pk)
            record.delete()
            return Response({'message': 'Attendance record deleted successfully.'}, status=status.HTTP_200_OK)
        except Attendance.DoesNotExist:
            return Response({'error': f'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)


class SeedDataView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Create default employees
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

        # Create user for emp1 if not exists
        u1, created = User.objects.get_or_create(username='emp001')
        if created:
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

        tz = timezone.get_current_timezone()
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        # Pre-populate sample attendance records if none exist
        if Attendance.objects.count() == 0:
            # 1. GS Full Day (Present)
            Attendance.objects.create(
                employee=emp1,
                attendance_date=yesterday,
                shift=SHIFT_GS,
                punch_in=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(12, 0, 0)), tz),
                punch_out=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(21, 0, 0)), tz)
            )

            # 2. NS Full Night Shift (Present across midnight)
            ns_in = timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(21, 30, 0)), tz)
            ns_out = timezone.make_aware(datetime.datetime.combine(today, datetime.time(6, 30, 0)), tz)
            Attendance.objects.create(
                employee=emp2,
                attendance_date=yesterday,
                shift=SHIFT_NS,
                punch_in=ns_in,
                punch_out=ns_out
            )

            # 3. GS First Half Only (Half Day)
            Attendance.objects.create(
                employee=emp3,
                attendance_date=yesterday,
                shift=SHIFT_GS,
                punch_in=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(12, 0, 0)), tz),
                punch_out=timezone.make_aware(datetime.datetime.combine(yesterday, datetime.time(16, 30, 0)), tz)
            )

        return Response({'message': 'Demo data seeded successfully!'})

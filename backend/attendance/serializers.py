from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Attendance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff']


class EmployeeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'employee_id', 'name', 'shift', 'username', 'created_at']

    def validate_employee_id(self, value):
        cleaned_val = value.strip()
        qs = Employee.objects.filter(employee_id__iexact=cleaned_val)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            existing = qs.first()
            raise serializers.ValidationError(
                f"Employee ID '{cleaned_val}' already exists (as '{existing.employee_id}'). Employee IDs are case-insensitive."
            )
        return cleaned_val


class AttendanceSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id',
            'employee',
            'employee_id',
            'employee_name',
            'attendance_date',
            'shift',
            'shift_display',
            'punch_in',
            'punch_out',
            'first_half',
            'second_half',
            'total_worked_minutes',
            'status',
            'created_at',
            'updated_at',
        ]


class PunchInSerializer(serializers.Serializer):
    employee_id = serializers.CharField(required=True)
    timestamp = serializers.DateTimeField(required=False, allow_null=True)


class PunchOutSerializer(serializers.Serializer):
    employee_id = serializers.CharField(required=True)
    timestamp = serializers.DateTimeField(required=False, allow_null=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

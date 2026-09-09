from django.db import models
from django.contrib.auth.models import User
from .calculator import (
    SHIFT_GS, SHIFT_NS,
    calculate_attendance_metrics,
    determine_attendance_date
)


class Employee(models.Model):
    SHIFT_CHOICES = (
        (SHIFT_GS, 'General Shift (12:00 PM - 9:00 PM)'),
        (SHIFT_NS, 'Night Shift (9:30 PM - 6:30 AM)'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile', null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, default=SHIFT_GS)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee_id} - {self.name} ({self.shift})"


class Attendance(models.Model):
    SHIFT_CHOICES = (
        (SHIFT_GS, 'General Shift'),
        (SHIFT_NS, 'Night Shift'),
    )

    HALF_STATUS_CHOICES = (
        ('PR', 'Present'),
        ('AB', 'Absent'),
        ('', 'Pending'),
    )

    ATTENDANCE_STATUS_CHOICES = (
        ('IN', 'Punched In'),
        ('PRESENT', 'Present'),
        ('HALF_DAY', 'Half Day'),
        ('ABSENT', 'Absent'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    attendance_date = models.DateField()
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES)
    punch_in = models.DateTimeField()
    punch_out = models.DateTimeField(null=True, blank=True)
    first_half = models.CharField(max_length=5, choices=HALF_STATUS_CHOICES, default='', blank=True)
    second_half = models.CharField(max_length=5, choices=HALF_STATUS_CHOICES, default='', blank=True)
    total_worked_minutes = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS_CHOICES, default='IN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-attendance_date', '-punch_in']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        # One attendance record per employee per shift-day — enforced at DB level
        unique_together = [('employee', 'attendance_date')]

    def update_metrics(self):
        metrics = calculate_attendance_metrics(
            shift_code=self.shift,
            attendance_date=self.attendance_date,
            punch_in_dt=self.punch_in,
            punch_out_dt=self.punch_out
        )
        self.first_half = metrics['first_half']
        self.second_half = metrics['second_half']
        self.total_worked_minutes = metrics['total_worked_minutes']
        self.status = metrics['status']

    def save(self, *args, **kwargs):
        if not self.attendance_date and self.punch_in and self.employee:
            self.attendance_date = determine_attendance_date(self.employee.shift, self.punch_in)
        if not self.shift and self.employee:
            self.shift = self.employee.shift

        self.update_metrics()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.attendance_date} - {self.status}"

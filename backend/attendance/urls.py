from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    EmployeeListView,
    EmployeeDetailView,
    PunchInView,
    PunchOutView,
    AttendanceDashboardView,
    AttendanceDeleteView,
    SeedDataView
)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('attendance/punch-in/', PunchInView.as_view(), name='punch-in'),
    path('attendance/punch-out/', PunchOutView.as_view(), name='punch-out'),
    path('attendance/dashboard/', AttendanceDashboardView.as_view(), name='attendance-dashboard'),
    path('attendance/<int:pk>/delete/', AttendanceDeleteView.as_view(), name='attendance-delete'),
    path('seed/', SeedDataView.as_view(), name='seed-data'),
]

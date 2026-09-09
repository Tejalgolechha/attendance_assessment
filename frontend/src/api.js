import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const loginUser = (username, password) => api.post('/auth/login/', { username, password });
export const logoutUser = () => api.post('/auth/logout/');

export const getEmployees = () => api.get('/employees/');
export const createEmployee = (employeeData) => api.post('/employees/', employeeData);
export const updateEmployee = (id, data) => api.patch(`/employees/${id}/`, data);
export const deleteEmployee = (id) => api.delete(`/employees/${id}/`);

export const punchIn = (employee_id, timestamp = null) =>
  api.post('/attendance/punch-in/', { employee_id, timestamp });

export const punchOut = (employee_id, timestamp = null) =>
  api.post('/attendance/punch-out/', { employee_id, timestamp });

export const getDashboardAttendance = (params = {}) =>
  api.get('/attendance/dashboard/', { params });

export const deleteAttendanceRecord = (id) =>
  api.delete(`/attendance/${id}/delete/`);

export const seedDemoData = () => api.post('/seed/');


export default api;

# Employee Punch In / Punch Out & Attendance Management System

A full-stack Attendance Management System built with **Django REST Framework** (Backend) and **React Vite** (Frontend).

## Features

- **Authentication**: User / Employee login & logout.
- **Employee Management**: Employee ID, Name, and Assigned Shift (`GS` or `NS`).
- Added a unique Employee ID field to ensure that duplicate Employee IDs cannot be created. Also provide options to **change an employee’s assigned shift** and **delete an employee** when required.
- **Punch In & Punch Out**: Real-time clock punch in/out or custom timestamp mode for testing edge cases.
- **Attendance Rules Engine**:
  - **GS (General Shift)**: 12:00 PM – 9:00 PM (First Half: 12:00 PM – 4:30 PM, Second Half: 4:30 PM – 9:00 PM).
  - **NS (Night Shift)**: 9:30 PM – 6:30 AM next day (First Half: 9:30 PM – 2:00 AM, Second Half: 2:00 AM – 6:30 AM).
  - **15-Minute Grace Window**: Shift bounds include 15-minute grace on both ends (GS: 11:45 AM → 9:15 PM, NS: 9:15 PM → 6:45 AM next day).
  - **First Half Borrowing Rule**: First Half can borrow up to 60 minutes of actually worked time from the beginning of Second Half to reach the required 270 qualifying minutes (e.g. when an employee arrives late and leaves early).
  - **270 Minutes Rule**: First Half and Second Half are marked **PR** (Present) if worked minutes within that half $\ge 270$ minutes (4.5 hours); otherwise **AB** (Absent).
  - **Night Shift Midnight Crossing**: Handles shifts spanning across midnight correctly.
  - **Status**: `IN` (Punched in), `PRESENT` (Both halves PR), `HALF_DAY` (One half PR), `ABSENT` (Both halves AB).
- **Validations & Edge Cases**:
  - Duplicate active punch in prevention.
  - Punch out without punch in prevention.
  - Punch out before punch in prevention.
  - Punch in after shift end time prevention.
- **Interactive Dashboard**: Search, filter by shift, status, and date. Metrics cards for high-level statistics.
- **Manual Testing Mode**: Toggle to select custom timestamps for testing any shift scenario.

---

## Demo Employee Credentials

| Employee ID | Employee Name | Assigned Shift | Default Login Username | Default Password |
| ----------- | ------------- | -------------- | ---------------------- | ---------------- |
| **EMP001**  | Alice Johnson | GS (12:00 PM - 9:00 PM) | `emp001` | `password123` |
| **EMP002**  | Bob Smith | NS (9:30 PM - 6:30 AM) | `emp002` | `password123` |
| **EMP003**  | Charlie Davis | GS (12:00 PM - 9:00 PM) | `emp003` | `password123` |

---

## Setup & Running Instructions

### 1. Prerequisites
- Python 3.10+
- Node.js v18+ & npm

### 2. Backend Setup (Django)

```bash
# Navigate to project root
cd attendance_assessment

# Create & activate a Python Virtual Environment
# Windows PowerShell:
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS:
# python3 -m venv venv
# source venv/bin/activate

# Install Python dependencies from requirements.txt
pip install -r requirements.txt

# Navigate to backend folder
cd backend

# Apply database migrations
python manage.py migrate

# Seed demo employee & attendance data
python manage.py seed_demo_data

# Run Django unit test suite (39 tests)
python manage.py test attendance

# Start Backend Server (runs on http://127.0.0.1:8000)
python manage.py runserver 8000
```

### 3. Frontend Setup (React Vite)

```bash
# Open a new terminal and navigate to frontend directory
cd attendance_assessment/frontend

# Install Node dependencies
npm install

# Start React Dev Server (runs on http://localhost:5173)
npm run dev
```

---




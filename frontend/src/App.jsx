import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import PunchControl from './components/PunchControl';
import AttendanceDashboard from './components/AttendanceDashboard';
import LoginModal from './components/LoginModal';
import EmployeeModal from './components/EmployeeModal';
import { getEmployees, getDashboardAttendance, logoutUser } from './api';
import { ShieldCheck, LogIn, LayoutDashboard, Users, Clock } from 'lucide-react';

export default function App() {
  const [employees, setEmployees] = useState([]);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [adminUser, setAdminUser] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showEmployeeModal, setShowEmployeeModal] = useState(false);
  const [notification, setNotification] = useState(null);

  const fetchData = async () => {
    try {
      const [empRes, attRes] = await Promise.all([
        getEmployees(),
        getDashboardAttendance(),
      ]);
      setEmployees(empRes.data);
      setAttendanceRecords(attRes.data);
    } catch (err) {
      console.error('Failed to fetch data', err);
    }
  };

  useEffect(() => {
    if (adminUser) {
      fetchData();
    }
  }, [adminUser?.id]);

  const handleLogout = async () => {
    try {
      await logoutUser();
      setAdminUser(null);
      setEmployees([]);
      setAttendanceRecords([]);
      showToast('Logged out successfully.');
    } catch (err) {
      console.error(err);
    }
  };

  const showToast = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  return (
    <div>
      {/* Animated background blob (third blob, sits in center) */}
      <div className="blob-extra" aria-hidden="true" />

      <Navbar
        isAdminLoggedIn={!!adminUser}
        onLogout={handleLogout}
        onOpenLogin={() => setShowLoginModal(true)}
        onOpenEmployeeModal={() => setShowEmployeeModal(true)}
      />

      {/* Toast Notification */}
      {notification && (
        <div style={{ padding: '0 1.5rem', maxWidth: '1280px', margin: '1rem auto 0', position: 'relative', zIndex: 1 }}>
          <div className="alert alert-info">
            <span>{notification}</span>
          </div>
        </div>
      )}

      {/* ── LOGIN WALL ── */}
      {!adminUser ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: 'calc(100vh - 62px)',
            padding: '2rem',
            textAlign: 'center',
            position: 'relative',
            zIndex: 1,
          }}
        >
          <div
            className="glass-panel"
            style={{
              padding: '2.75rem 2.5rem',
              maxWidth: '460px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '1.5rem',
            }}
          >
            {/* Icon */}
            <div
              style={{
                width: '72px',
                height: '72px',
                borderRadius: '50%',
                background: 'var(--accent-primary-light)',
                border: '2px solid #c7d2fe',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ShieldCheck size={34} color="var(--accent-primary)" />
            </div>

            <div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem', letterSpacing: '-0.01em' }}>
                Admin Access Required
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
                The Attendance Management System is restricted to administrators.
                Sign in to access the dashboard, manage employees, and record attendance.
              </div>
            </div>

            {/* Feature pills */}
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', justifyContent: 'center' }}>
              {[
                { icon: <LayoutDashboard size={14} />, label: 'Dashboard' },
                { icon: <Users size={14} />, label: 'Employees' },
                { icon: <Clock size={14} />, label: 'Punch In / Out' },
              ].map((f) => (
                <span
                  key={f.label}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    padding: '0.35rem 0.75rem',
                    background: 'var(--accent-primary-light)',
                    color: 'var(--accent-primary)',
                    borderRadius: '20px',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    border: '1px solid #c7d2fe',
                  }}
                >
                  {f.icon} {f.label}
                </span>
              ))}
            </div>

            <button
              className="btn btn-success btn-lg"
              style={{ width: '100%' }}
              onClick={() => setShowLoginModal(true)}
            >
              <LogIn size={18} />
              Sign In as Administrator
            </button>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
              Use your admin credentials to sign in
            </div>
          </div>
        </div>
      ) : (
        /* ── MAIN DASHBOARD ── */
        <main className="app-container">
          <PunchControl
            employees={employees}
            currentUser={null}
            attendanceRecords={attendanceRecords}
            onAttendanceUpdated={fetchData}
          />
          <AttendanceDashboard
            attendanceRecords={attendanceRecords}
            onAttendanceUpdated={fetchData}
          />
        </main>
      )}

      {/* Admin Login Modal */}
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal(false)}
          onLoginSuccess={(user) => {
            setAdminUser(user);
            showToast('Welcome, Administrator! Access granted.');
          }}
        />
      )}

      {/* Employee Management Modal */}
      {showEmployeeModal && adminUser && (
        <EmployeeModal
          employees={employees}
          onClose={() => setShowEmployeeModal(false)}
          onEmployeeCreated={() => {
            fetchData();
            showToast('New employee added successfully!');
          }}
        />
      )}
    </div>
  );
}

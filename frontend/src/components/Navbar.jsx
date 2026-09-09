import React from 'react';
import { Clock, LogOut, ShieldCheck, UserPlus } from 'lucide-react';

export default function Navbar({ isAdminLoggedIn, onLogout, onOpenLogin, onOpenEmployeeModal }) {
  return (
    <nav className="navbar">
      <div className="nav-brand">
        <Clock size={28} />
        <span>Attendance Management</span>
      </div>

      <div className="nav-user">
        {isAdminLoggedIn && (
          <button className="nav-btn" onClick={onOpenEmployeeModal}>
            <UserPlus size={16} />
            <span>Employees</span>
          </button>
        )}

        {isAdminLoggedIn ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="badge badge-in">
              <ShieldCheck size={14} /> Admin Active
            </span>
            <button className="nav-btn" onClick={onLogout}>
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        ) : (
          <button className="nav-btn nav-btn-primary" onClick={onOpenLogin}>
            <ShieldCheck size={16} />
            <span>Admin Login</span>
          </button>
        )}
      </div>
    </nav>
  );
}

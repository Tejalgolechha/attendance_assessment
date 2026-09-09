import React, { useState } from 'react';
import { Table, Search, Filter, Calendar, Users, CheckCircle, Clock, AlertTriangle, XCircle, RotateCcw, Trash2 } from 'lucide-react';
import { deleteAttendanceRecord } from '../api';

export default function AttendanceDashboard({ attendanceRecords, onAttendanceUpdated }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterShift, setFilterShift] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterDate, setFilterDate] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDeleteRecord, setConfirmDeleteRecord] = useState(null);

  // Filter records
  const filteredRecords = attendanceRecords.filter((rec) => {
    const matchesSearch =
      rec.employee_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.employee_name.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesShift = filterShift === 'ALL' || rec.shift === filterShift;
    const matchesStatus = filterStatus === 'ALL' || rec.status === filterStatus;
    const matchesDate = !filterDate || rec.attendance_date === filterDate;

    return matchesSearch && matchesShift && matchesStatus && matchesDate;
  });

  // Calculate statistics dynamically from filteredRecords (follow filters)
  const totalRecords = filteredRecords.length;
  const activeInCount = filteredRecords.filter((r) => r.status === 'IN').length;
  const presentCount = filteredRecords.filter((r) => r.status === 'PRESENT').length;
  const halfDayCount = filteredRecords.filter((r) => r.status === 'HALF_DAY').length;
  const absentCount = filteredRecords.filter((r) => r.status === 'ABSENT').length;

  const resetFilters = () => {
    setSearchTerm('');
    setFilterShift('ALL');
    setFilterStatus('ALL');
    setFilterDate('');
  };

  const hasActiveFilters = searchTerm || filterShift !== 'ALL' || filterStatus !== 'ALL' || filterDate;

  const handleDeleteClick = (rec) => {
    setConfirmDeleteRecord(rec);
  };

  const handleConfirmDelete = async (id) => {
    setDeletingId(id);
    setConfirmDeleteRecord(null);
    try {
      await deleteAttendanceRecord(id);
      onAttendanceUpdated();
    } catch (err) {
      console.error('Delete failed:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const formatDateTime = (dtStr) => {
    if (!dtStr) return <span style={{ color: 'var(--text-dim)' }}>—</span>;
    const dt = new Date(dtStr);
    return dt.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'IN':
        return <span className="badge badge-in"><Clock size={12} /> IN</span>;
      case 'PRESENT':
        return <span className="badge badge-present"><CheckCircle size={12} /> PRESENT</span>;
      case 'HALF_DAY':
        return <span className="badge badge-half"><AlertTriangle size={12} /> HALF DAY</span>;
      case 'ABSENT':
        return <span className="badge badge-absent"><XCircle size={12} /> ABSENT</span>;
      default:
        return <span className="badge">{status}</span>;
    }
  };

  const getHalfBadge = (status) => {
    if (status === 'PR') {
      return <span className="badge badge-present" style={{ padding: '0.15rem 0.45rem', fontSize: '0.75rem' }}>PR</span>;
    }
    if (status === 'AB') {
      return <span className="badge badge-absent" style={{ padding: '0.15rem 0.45rem', fontSize: '0.75rem' }}>AB</span>;
    }
    return <span style={{ color: 'var(--text-dim)' }}>—</span>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Confirm Delete Modal */}
      {confirmDeleteRecord && (
        <div className="modal-overlay">
          <div className="glass-panel" style={{ padding: '2rem', maxWidth: '420px', width: '100%', textAlign: 'center' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🗑️</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>Delete Attendance Record?</div>
            <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: '1.5rem', lineHeight: 1.6 }}>
              This will permanently remove the attendance record for <strong style={{ color: 'var(--text-main)' }}>{confirmDeleteRecord.employee_name} ({confirmDeleteRecord.employee_id})</strong> on <strong style={{ color: 'var(--text-main)' }}>{confirmDeleteRecord.attendance_date}</strong>. This action cannot be undone.
            </div>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button className="btn btn-secondary" onClick={() => setConfirmDeleteRecord(null)}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={() => handleConfirmDelete(confirmDeleteRecord.id)}>
                <Trash2 size={16} /> Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Dynamic Filtered Metrics Cards */}
      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.6rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Summary {hasActiveFilters && <strong style={{ color: 'var(--accent-primary)' }}>— Filtered View</strong>}
        </div>
        <div className="stats-grid">
          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'var(--accent-primary-light)', color: 'var(--accent-primary)' }}>
              <Users size={22} />
            </div>
            <div>
              <div className="stat-value">{totalRecords}</div>
              <div className="stat-label">Total Records</div>
            </div>
          </div>

          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'var(--badge-in-bg)', color: 'var(--badge-in-text)' }}>
              <Clock size={22} />
            </div>
            <div>
              <div className="stat-value">{activeInCount}</div>
              <div className="stat-label">Currently IN</div>
            </div>
          </div>

          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'var(--badge-present-bg)', color: 'var(--badge-present-text)' }}>
              <CheckCircle size={22} />
            </div>
            <div>
              <div className="stat-value">{presentCount}</div>
              <div className="stat-label">Present</div>
            </div>
          </div>

          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'var(--badge-half-bg)', color: 'var(--badge-half-text)' }}>
              <AlertTriangle size={22} />
            </div>
            <div>
              <div className="stat-value">{halfDayCount}</div>
              <div className="stat-label">Half Day</div>
            </div>
          </div>

          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'var(--badge-absent-bg)', color: 'var(--badge-absent-text)' }}>
              <XCircle size={22} />
            </div>
            <div>
              <div className="stat-value">{absentCount}</div>
              <div className="stat-label">Absent</div>
            </div>
          </div>
        </div>
      </div>

      {/* Table & Filters Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div className="section-header">
          <div className="section-title">
            <Table size={22} />
            <span>Attendance Log Records</span>
          </div>
          {hasActiveFilters && (
            <button className="nav-btn" onClick={resetFilters} style={{ fontSize: '0.82rem' }}>
              <RotateCcw size={14} /> Clear Filters
            </button>
          )}
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-color)' }}>
          <div className="form-group">
            <label className="form-label"><Search size={14} /> Search Employee</label>
            <input type="text" className="form-control" placeholder="Search ID or Name..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label"><Filter size={14} /> Shift</label>
            <select className="form-control" value={filterShift} onChange={(e) => setFilterShift(e.target.value)}>
              <option value="ALL">All Shifts</option>
              <option value="GS">GS (General Shift)</option>
              <option value="NS">NS (Night Shift)</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label"><Filter size={14} /> Status</label>
            <select className="form-control" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="ALL">All Statuses</option>
              <option value="IN">Punched IN</option>
              <option value="PRESENT">PRESENT</option>
              <option value="HALF_DAY">HALF DAY</option>
              <option value="ABSENT">ABSENT</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label"><Calendar size={14} /> Attendance Date</label>
            <input type="date" className="form-control" value={filterDate} max={new Date().toISOString().split('T')[0]} onChange={(e) => setFilterDate(e.target.value)} />
          </div>
        </div>

        {/* Attendance Records Table */}
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Emp ID</th>
                <th>Employee</th>
                <th>Shift</th>
                <th>Date</th>
                <th>Punch In</th>
                <th>Punch Out</th>
                <th>Halves (1st / 2nd)</th>
                <th>Worked</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No attendance records found matching current filters.
                  </td>
                </tr>
              ) : (
                filteredRecords.map((rec) => (
                  <tr key={rec.id} style={{ opacity: deletingId === rec.id ? 0.4 : 1, transition: 'opacity 0.3s' }}>
                    <td style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>{rec.employee_id}</td>
                    <td style={{ fontWeight: 500 }}>{rec.employee_name}</td>
                    <td><span className="badge badge-shift">{rec.shift}</span></td>
                    <td style={{ color: 'var(--text-muted)' }}>{rec.attendance_date}</td>
                    <td>{formatDateTime(rec.punch_in)}</td>
                    <td>
                      {rec.punch_out ? formatDateTime(rec.punch_out) : <span className="badge badge-in">Active IN</span>}
                    </td>
                    <td>
                      <div style={{ display: 'inline-flex', gap: '0.25rem', alignItems: 'center' }}>
                        {getHalfBadge(rec.first_half)}
                        <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>/</span>
                        {getHalfBadge(rec.second_half)}
                      </div>
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      {(rec.total_worked_minutes / 60).toFixed(1)} hrs{' '}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                        ({rec.total_worked_minutes}m)
                      </span>
                    </td>
                    <td>{getStatusBadge(rec.status)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => handleDeleteClick(rec)}
                        disabled={deletingId === rec.id}
                        title="Delete this record"
                        className="btn-delete-sm"
                      >
                        <Trash2 size={13} />
                        {deletingId === rec.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

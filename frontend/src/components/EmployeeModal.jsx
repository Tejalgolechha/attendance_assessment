import React, { useState } from 'react';
import { X, UserPlus, Users, Trash2, Edit3, CheckCircle } from 'lucide-react';
import { createEmployee, updateEmployee, deleteEmployee } from '../api';

export default function EmployeeModal({ employees, onClose, onEmployeeCreated }) {
  const [employeeId, setEmployeeId] = useState('');
  const [name, setName] = useState('');
  const [shift, setShift] = useState('GS');
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDeleteEmp, setConfirmDeleteEmp] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setLoading(true);

    const trimmedId = employeeId.trim();
    // Case-insensitive duplicate check on client side
    const existing = employees.find(
      (emp) => emp.employee_id.trim().toLowerCase() === trimmedId.toLowerCase()
    );
    if (existing) {
      setErrorMsg(
        `Employee ID '${trimmedId}' already exists (as '${existing.employee_id}'). Employee IDs are case-insensitive (e.g. emp001 is same as EMP001).`
      );
      setLoading(false);
      return;
    }

    try {
      await createEmployee({ employee_id: trimmedId, name, shift });
      setSuccessMsg(`Employee ${trimmedId} created successfully!`);
      setEmployeeId('');
      setName('');
      onEmployeeCreated();
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      const msg =
        err.response?.data?.employee_id?.[0] ||
        err.response?.data?.error ||
        err.response?.data?.detail ||
        'Failed to create employee.';
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleShiftChange = async (emp, newShift) => {
    if (emp.shift === newShift) return;
    setUpdatingId(emp.id);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      await updateEmployee(emp.id, { shift: newShift });
      setSuccessMsg(`Shift for ${emp.employee_id} updated to ${newShift}!`);
      onEmployeeCreated();
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setErrorMsg('Failed to update shift.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleConfirmDelete = async (emp) => {
    setDeletingId(emp.id);
    setConfirmDeleteEmp(null);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      await deleteEmployee(emp.id);
      setSuccessMsg(`Employee ${emp.employee_id} deleted successfully!`);
      onEmployeeCreated();
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.detail || 'Failed to delete employee.';
      setErrorMsg(msg);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-content" style={{ maxWidth: '650px' }}>
        <div className="section-header">
          <div className="section-title">
            <Users size={22} color="var(--accent-primary)" />
            <span>Employee Management & Shift Assignments</span>
          </div>
          <button className="nav-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}
        {successMsg && (
          <div className="alert alert-success">
            <CheckCircle size={16} /> {successMsg}
          </div>
        )}

        {/* Delete Confirmation Sub-modal */}
        {confirmDeleteEmp && (
          <div className="alert alert-danger" style={{ flexDirection: 'column', gap: '0.75rem', alignItems: 'flex-start' }}>
            <div>
              Are you sure you want to delete employee <strong>{confirmDeleteEmp.employee_id} ({confirmDeleteEmp.name})</strong>?
              This will also remove all associated attendance logs.
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-danger" style={{ padding: '0.35rem 0.75rem', fontSize: '0.82rem' }} onClick={() => handleConfirmDelete(confirmDeleteEmp)}>
                Yes, Delete
              </button>
              <button className="btn btn-secondary" style={{ padding: '0.35rem 0.75rem', fontSize: '0.82rem' }} onClick={() => setConfirmDeleteEmp(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Create Employee Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-main)' }}>Add New Employee</div>
          
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Employee ID</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. EMP004"
                required
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Diana Prince"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Assigned Shift</label>
            <select className="form-control" value={shift} onChange={(e) => setShift(e.target.value)}>
              <option value="GS">GS - General Shift (12:00 PM – 9:00 PM)</option>
              <option value="NS">NS - Night Shift (9:30 PM – 6:30 AM next day)</option>
            </select>
          </div>

          <button type="submit" className="btn btn-success" disabled={loading}>
            <UserPlus size={18} />
            <span>{loading ? 'Creating...' : 'Add Employee'}</span>
          </button>
        </form>

        {/* Existing Employees List */}
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.75rem', color: 'var(--text-main)' }}>
            Current Employees ({employees.length})
          </div>
          <div className="table-container" style={{ maxHeight: '240px', overflowY: 'auto' }}>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Assigned Shift (Change)</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {employees.length === 0 ? (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                      No employees registered yet.
                    </td>
                  </tr>
                ) : (
                  employees.map((emp) => (
                    <tr key={emp.id || emp.employee_id} style={{ opacity: deletingId === emp.id ? 0.4 : 1 }}>
                      <td style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{emp.employee_id}</td>
                      <td style={{ fontWeight: 500 }}>{emp.name}</td>
                      <td>
                        <select
                          className="form-control"
                          value={emp.shift}
                          onChange={(e) => handleShiftChange(emp, e.target.value)}
                          disabled={updatingId === emp.id}
                          style={{ padding: '0.3rem 0.5rem', fontSize: '0.8rem', width: 'auto', display: 'inline-block' }}
                        >
                          <option value="GS">GS (General Shift)</option>
                          <option value="NS">NS (Night Shift)</option>
                        </select>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          onClick={() => setConfirmDeleteEmp(emp)}
                          disabled={deletingId === emp.id}
                          className="btn-delete-sm"
                          title="Delete employee"
                        >
                          <Trash2 size={13} />
                          {deletingId === emp.id ? 'Deleting...' : 'Delete'}
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
    </div>
  );
}

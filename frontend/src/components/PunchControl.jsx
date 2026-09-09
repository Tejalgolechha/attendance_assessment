import React, { useState, useEffect } from 'react';
import { Clock, Play, Square, AlertCircle, CheckCircle2, Calendar, UserCheck, ShieldCheck } from 'lucide-react';
import { punchIn, punchOut } from '../api';

// Generate hours 1–12, minutes 00–59
const HOURS = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0'));
const MINUTES = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));

/** Convert 4-part picker values to ISO string for Django */
function buildISOTimestamp(date, hour, minute, ampm) {
  if (!date || !hour || !minute || !ampm) return null;
  let h = parseInt(hour, 10);
  if (ampm === 'AM' && h === 12) h = 0;   // 12 AM = midnight = 0
  if (ampm === 'PM' && h !== 12) h += 12; // 1–11 PM → 13–23
  const hh = String(h).padStart(2, '0');
  // Construct as local time string, let Date parse it as local, then export as UTC ISO
  const localStr = `${date}T${hh}:${minute}:00`;
  return new Date(localStr).toISOString();
}

/** Today's date in YYYY-MM-DD format (local) */
function todayStr() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export default function PunchControl({ employees, currentUser, attendanceRecords, onAttendanceUpdated }) {
  const [selectedEmpId, setSelectedEmpId] = useState(currentUser?.employee_id || 'EMP001');
  const [useCustomTime, setUseCustomTime] = useState(false);

  // 4-part picker state
  const [customDate, setCustomDate] = useState(todayStr());
  const [customHour, setCustomHour] = useState('12');
  const [customMinute, setCustomMinute] = useState('00');
  const [customAmPm, setCustomAmPm] = useState('PM');

  // Admin punch-out timing modal state
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [adminChoice, setAdminChoice] = useState('DEFAULT'); // 'DEFAULT' or 'CUSTOM'
  const [adminDate, setAdminDate] = useState(todayStr());
  const [adminHour, setAdminHour] = useState('11');
  const [adminMinute, setAdminMinute] = useState('00');
  const [adminAmPm, setAdminAmPm] = useState('PM');

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [currentTime, setCurrentTime] = useState(new Date());

  // Real-time clock
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Sync selected employee when currentUser changes
  useEffect(() => {
    if (currentUser?.employee_id) {
      setSelectedEmpId(currentUser.employee_id);
    }
  }, [currentUser]);

  const selectedEmployee = employees.find((e) => e.employee_id === selectedEmpId) || employees[0];
  const activeRecord = attendanceRecords.find(
    (rec) => rec.employee_id === selectedEmpId && rec.punch_out === null
  );

  const extractError = (err, fallback) => {
    const data = err.response?.data;
    if (!data) return fallback;
    if (Array.isArray(data) && data.length > 0) return data[0];
    if (typeof data === 'string') return data;
    return data?.error || data?.detail || data?.non_field_errors?.[0] || fallback;
  };

  const getTimestamp = () => {
    if (!useCustomTime) return null;
    return buildISOTimestamp(customDate, customHour, customMinute, customAmPm);
  };

  const isFutureTimestamp = (ts) => {
    if (!ts) return false;
    return new Date(ts) > new Date();
  };

  const handlePunchIn = async () => {
    setErrorMsg('');
    setSuccessMsg('');

    const ts = getTimestamp();
    if (useCustomTime && ts && isFutureTimestamp(ts)) {
      setErrorMsg('Punch-in cannot be for a future date or time.');
      return;
    }

    setLoading(true);
    try {
      await punchIn(selectedEmpId, ts);
      setSuccessMsg(`✅ Punched In successfully for ${selectedEmpId}!`);
      onAttendanceUpdated();
    } catch (err) {
      setErrorMsg(extractError(err, 'Punch In request failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  // Trigger Punch Out click — if in custom timestamp mode, prompt administrator
  const handlePunchOutClick = () => {
    setErrorMsg('');
    setSuccessMsg('');

    if (useCustomTime) {
      // Setup admin defaults based on shift
      if (activeRecord) {
        setAdminDate(activeRecord.attendance_date || todayStr());
        if (selectedEmployee?.shift === 'NS') {
          // NS default: 8:30 AM next day
          const d = new Date(activeRecord.attendance_date || todayStr());
          d.setDate(d.getDate() + 1);
          const yyyy = d.getFullYear();
          const mm = String(d.getMonth() + 1).padStart(2, '0');
          const dd = String(d.getDate()).padStart(2, '0');
          setAdminDate(`${yyyy}-${mm}-${dd}`);
          setAdminHour('08');
          setAdminMinute('30');
          setAdminAmPm('AM');
        } else {
          // GS default: 11:00 PM
          setAdminHour('11');
          setAdminMinute('00');
          setAdminAmPm('PM');
        }
      }
      setShowAdminModal(true);
    } else {
      executePunchOut(null);
    }
  };

  const executePunchOut = async (ts) => {
    if (ts && isFutureTimestamp(ts)) {
      setErrorMsg('Punch-out cannot be for a future date or time.');
      return;
    }

    setLoading(true);
    try {
      await punchOut(selectedEmpId, ts);
      setSuccessMsg(`✅ Punched Out successfully for ${selectedEmpId}!`);
      setShowAdminModal(false);
      onAttendanceUpdated();
    } catch (err) {
      setErrorMsg(extractError(err, 'Punch Out request failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleAdminConfirmPunchOut = () => {
    let finalTs = null;
    if (adminChoice === 'CUSTOM') {
      finalTs = buildISOTimestamp(adminDate, adminHour, adminMinute, adminAmPm);
    } else {
      // DEFAULT option: 11:00 PM for GS, 8:30 AM next day for NS on attendance_date
      if (activeRecord) {
        if (selectedEmployee?.shift === 'NS') {
          const d = new Date(activeRecord.attendance_date);
          d.setDate(d.getDate() + 1);
          const yyyy = d.getFullYear();
          const mm = String(d.getMonth() + 1).padStart(2, '0');
          const dd = String(d.getDate()).padStart(2, '0');
          finalTs = buildISOTimestamp(`${yyyy}-${mm}-${dd}`, '08', '30', 'AM');
        } else {
          finalTs = buildISOTimestamp(activeRecord.attendance_date, '11', '00', 'PM');
        }
      } else {
        finalTs = buildISOTimestamp(adminDate, adminHour, adminMinute, adminAmPm);
      }
    }
    executePunchOut(finalTs);
  };

  const getShiftBadge = (shift) => {
    if (shift === 'GS') {
      return <span className="badge badge-shift">GS: 12:00 PM – 9:00 PM</span>;
    }
    return (
      <span className="badge badge-shift" style={{ borderColor: '#a855f7', color: '#c084fc', background: 'rgba(168, 85, 247, 0.15)' }}>
        NS: 9:30 PM – 6:30 AM (Next Day)
      </span>
    );
  };

  // Live preview of the assembled timestamp so user can verify before submitting
  const previewTs = useCustomTime ? buildISOTimestamp(customDate, customHour, customMinute, customAmPm) : null;
  const isPreviewFuture = previewTs ? isFutureTimestamp(previewTs) : false;
  const previewLabel = previewTs
    ? new Date(previewTs).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : '';

  return (
    <div className="glass-panel" style={{ padding: '1.75rem' }}>
      {/* Administrator Punch Out Timing Modal */}
      {showAdminModal && (
        <div className="modal-overlay">
          <div className="glass-panel" style={{ padding: '2rem', maxWidth: '520px', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <ShieldCheck className="text-indigo-400" size={28} />
              <div>
                <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  Administrator Punch-Out Timing Rights
                </h3>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Specify or confirm punch-out timing for <strong>{selectedEmployee?.name}</strong> ({selectedEmpId})
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', margin: '1.25rem 0' }}>
              {/* Option 1: Auto 11 PM / 8:30 AM */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${adminChoice === 'DEFAULT' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                  background: adminChoice === 'DEFAULT' ? 'var(--accent-primary-light)' : 'var(--bg-input)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="adminPunchOut"
                  checked={adminChoice === 'DEFAULT'}
                  onChange={() => setAdminChoice('DEFAULT')}
                  style={{ marginTop: '0.2rem' }}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.92rem' }}>
                    Auto-set Default Time ({selectedEmployee?.shift === 'NS' ? '8:30 AM Next Morning' : '11:00 PM Night'})
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                    Automatically sets punch-out to 2 hours post-shift end time ({selectedEmployee?.shift === 'NS' ? '8:30 AM' : '11:00 PM'}) for forgotten punch-outs.
                  </div>
                </div>
              </label>

              {/* Option 2: Custom Admin Punch Out Time */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${adminChoice === 'CUSTOM' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                  background: adminChoice === 'CUSTOM' ? 'var(--accent-primary-light)' : 'var(--bg-input)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="adminPunchOut"
                  checked={adminChoice === 'CUSTOM'}
                  onChange={() => setAdminChoice('CUSTOM')}
                  style={{ marginTop: '0.2rem' }}
                />
                <div style={{ width: '100%' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.92rem' }}>
                    Administrator Custom Punch-Out Timing
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                    Select specific date and time for employee punch-out.
                  </div>

                  {adminChoice === 'CUSTOM' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.8rem' }}>
                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label">Punch-Out Date</label>
                        <input
                          type="date"
                          className="form-control"
                          value={adminDate}
                          max={todayStr()}
                          onChange={(e) => setAdminDate(e.target.value)}
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                        <div className="form-group" style={{ margin: 0 }}>
                          <label className="form-label">Hour</label>
                          <select className="form-control" value={adminHour} onChange={(e) => setAdminHour(e.target.value)}>
                            {HOURS.map((h) => <option key={h} value={h}>{h}</option>)}
                          </select>
                        </div>
                        <div className="form-group" style={{ margin: 0 }}>
                          <label className="form-label">Minute</label>
                          <select className="form-control" value={adminMinute} onChange={(e) => setAdminMinute(e.target.value)}>
                            {MINUTES.map((m) => <option key={m} value={m}>{m}</option>)}
                          </select>
                        </div>
                        <div className="form-group" style={{ margin: 0 }}>
                          <label className="form-label">AM / PM</label>
                          <select className="form-control" value={adminAmPm} onChange={(e) => setAdminAmPm(e.target.value)}>
                            <option value="AM">AM</option>
                            <option value="PM">PM</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowAdminModal(false)}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                className="btn btn-success"
                onClick={handleAdminConfirmPunchOut}
                disabled={loading}
              >
                Confirm & Submit Punch-Out
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="section-header">
        <div className="section-title">
          <Clock className="text-indigo-400" size={24} />
          <span>Punch In / Punch Out Action Center</span>
        </div>
        {selectedEmployee && getShiftBadge(selectedEmployee.shift)}
      </div>

      {errorMsg && (
        <div className="alert alert-danger">
          <AlertCircle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="alert alert-success">
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* Left Side: Employee selector + time controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Select Employee</label>
            <select
              className="form-control"
              value={selectedEmpId}
              onChange={(e) => setSelectedEmpId(e.target.value)}
            >
              {employees.map((emp) => (
                <option key={emp.employee_id} value={emp.employee_id}>
                  {emp.employee_id} - {emp.name} ({emp.shift})
                </option>
              ))}
            </select>
          </div>

          {/* Toggle Custom Timestamp Testing Mode */}
          <div className="toggle-wrapper">
            <div
              className={`toggle-switch ${useCustomTime ? 'active' : ''}`}
              onClick={() => setUseCustomTime(!useCustomTime)}
            >
              <div className="toggle-slider"></div>
            </div>
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Custom Timestamp Mode (For Testing)</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Pick a date and time to test GS, NS, early/late punch in/out scenarios
              </div>
            </div>
          </div>

          {useCustomTime ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {/* Date picker */}
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">
                  <Calendar size={14} /> Date (Future dates disabled)
                </label>
                <input
                  type="date"
                  className="form-control"
                  value={customDate}
                  max={todayStr()}
                  onChange={(e) => {
                    const selected = e.target.value;
                    if (selected > todayStr()) {
                      setErrorMsg('Future dates cannot be used for punch-in.');
                      setCustomDate(todayStr());
                    } else {
                      setErrorMsg('');
                      setCustomDate(selected);
                    }
                  }}
                />
              </div>

              {/* Hour / Minute / AM-PM row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Hour</label>
                  <select
                    className="form-control"
                    value={customHour}
                    onChange={(e) => setCustomHour(e.target.value)}
                  >
                    {HOURS.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Minute</label>
                  <select
                    className="form-control"
                    value={customMinute}
                    onChange={(e) => setCustomMinute(e.target.value)}
                  >
                    {MINUTES.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">AM / PM</label>
                  <select
                    className="form-control"
                    value={customAmPm}
                    onChange={(e) => setCustomAmPm(e.target.value)}
                  >
                    <option value="AM">AM</option>
                    <option value="PM">PM</option>
                  </select>
                </div>
              </div>

              {/* Live preview of the constructed timestamp */}
              {previewLabel && (
                <div style={{
                  background: isPreviewFuture ? 'rgba(239, 68, 68, 0.12)' : 'var(--accent-primary-light)',
                  border: `1px solid ${isPreviewFuture ? '#fca5a5' : '#c7d2fe'}`,
                  borderRadius: '6px',
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.82rem',
                  color: isPreviewFuture ? '#dc2626' : 'var(--accent-primary)',
                  fontWeight: 500,
                }}>
                  {isPreviewFuture ? (
                    <span>⚠️ Selected timestamp <strong>{previewLabel}</strong> is in the future. Punch-in/out for future dates is not allowed.</span>
                  ) : (
                    <span>⏱ Will use: <strong>{previewLabel}</strong></span>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div
              style={{
                background: 'var(--bg-input)',
                padding: '1rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
                Current System Time
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--accent-primary)', marginTop: '0.25rem' }}>
                {currentTime.toLocaleTimeString()}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {currentTime.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'short', day: 'numeric' })}
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Status & Action Buttons */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1.25rem',
            padding: '1rem',
            borderLeft: '1px solid var(--border-color)',
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Current Employee Status</span>
            <div style={{ marginTop: '0.4rem' }}>
              {activeRecord ? (
                <span className="badge badge-in" style={{ padding: '0.5rem 1rem', fontSize: '1rem' }}>
                  <UserCheck size={18} /> Currently Punched IN
                </span>
              ) : (
                <span className="badge badge-absent" style={{ padding: '0.5rem 1rem', fontSize: '1rem' }}>
                  Off Clock (Punched OUT)
                </span>
              )}
            </div>

            {activeRecord && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Punched In at: {new Date(activeRecord.punch_in).toLocaleString()}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '1rem', width: '100%', justifyContent: 'center' }}>
            <button
              className="btn btn-success btn-lg"
              style={{ flex: 1 }}
              onClick={handlePunchIn}
              disabled={loading || !!activeRecord}
            >
              <Play size={20} />
              <span>Punch IN</span>
            </button>

            <button
              className="btn btn-danger btn-lg"
              style={{ flex: 1 }}
              onClick={handlePunchOutClick}
              disabled={loading || !activeRecord}
            >
              <Square size={20} />
              <span>Punch OUT</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

import datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError

# Shift Constants
SHIFT_GS = 'GS'
SHIFT_NS = 'NS'

HALF_DAY_MINUTES_THRESHOLD = 270  # 4.5 hours
GRACE_MINUTES = 15

# Allowed Punch In Lead Time (1 hour before shift start)
PUNCH_IN_LEAD_HOURS = 1




def get_shift_schedule(shift_code, attendance_date):
    """
    Returns timezone-aware datetime objects for shift start, end, first/second half bounds (with 15-min grace window),
    and allowed punch-in window for a given shift code and attendance date.
    """
    if isinstance(attendance_date, str):
        attendance_date = datetime.date.fromisoformat(attendance_date)

    tz = timezone.get_current_timezone()
    grace_delta = datetime.timedelta(minutes=GRACE_MINUTES)

    if shift_code == SHIFT_GS:
        # GS: 12:00 PM – 9:00 PM on attendance_date
        shift_start_base    = timezone.make_aware(datetime.datetime.combine(attendance_date, datetime.time(12, 0)), tz)
        first_half_end_base = timezone.make_aware(datetime.datetime.combine(attendance_date, datetime.time(16, 30)), tz)
        shift_end_base      = timezone.make_aware(datetime.datetime.combine(attendance_date, datetime.time(21, 0)), tz)

        first_half_start  = shift_start_base - grace_delta
        first_half_end    = first_half_end_base + grace_delta
        second_half_start = first_half_end_base - grace_delta
        second_half_end   = shift_end_base + grace_delta

        shift_start = shift_start_base - grace_delta
        shift_end   = shift_end_base + grace_delta

        # Earliest allowed Punch In: 11:00 AM (1 hr before 12:00 PM shift start base)
        # Latest allowed Punch In:   shift_end_base itself (9:00 PM) — punch in AT end is still valid
        allowed_punch_in_start = shift_start_base - datetime.timedelta(hours=PUNCH_IN_LEAD_HOURS)
        allowed_punch_in_end   = shift_end_base

    elif shift_code == SHIFT_NS:
        # NS: 9:30 PM (attendance_date) – 6:30 AM (attendance_date + 1)
        next_day            = attendance_date + datetime.timedelta(days=1)
        shift_start_base    = timezone.make_aware(datetime.datetime.combine(attendance_date, datetime.time(21, 30)), tz)
        first_half_end_base = timezone.make_aware(datetime.datetime.combine(next_day, datetime.time(2, 0)), tz)
        shift_end_base      = timezone.make_aware(datetime.datetime.combine(next_day, datetime.time(6, 30)), tz)

        first_half_start  = shift_start_base - grace_delta
        first_half_end    = first_half_end_base + grace_delta
        second_half_start = first_half_end_base - grace_delta
        second_half_end   = shift_end_base + grace_delta

        shift_start = shift_start_base - grace_delta
        shift_end   = shift_end_base + grace_delta

        # Earliest: 8:30 PM (1 hr before 9:30 PM); Latest: shift_end_base (6:30 AM next day)
        allowed_punch_in_start = shift_start_base - datetime.timedelta(hours=PUNCH_IN_LEAD_HOURS)
        allowed_punch_in_end   = shift_end_base

    else:
        raise ValueError(f"Unknown shift code: {shift_code}")

    return {
        'shift_start':            shift_start,
        'shift_end':              shift_end,
        'shift_start_base':       shift_start_base,
        'shift_end_base':         shift_end_base,
        'first_half_start':       first_half_start,
        'first_half_end':         first_half_end,
        'second_half_start':      second_half_start,
        'second_half_end':        second_half_end,
        'allowed_punch_in_start': allowed_punch_in_start,
        'allowed_punch_in_end':   allowed_punch_in_end,
    }




def determine_attendance_date(shift_code, punch_in_dt):
    """
    Determines the canonical attendance_date for a punch-in timestamp.

    GS:  Local calendar date of punch_in_dt.
    NS:  If local time is between 00:00 and 06:30 (inclusive), this belongs to
         the night shift that STARTED the previous calendar day.
         Otherwise it belongs to the local calendar date of punch_in_dt.

    Always converts to local timezone before computing to handle UTC-stored datetimes.
    """
    tz = timezone.get_current_timezone()

    if timezone.is_naive(punch_in_dt):
        punch_in_dt = timezone.make_aware(punch_in_dt, tz)

    local_dt   = punch_in_dt.astimezone(tz)
    punch_date = local_dt.date()
    punch_time = local_dt.time()

    if shift_code == SHIFT_NS:
        # 00:00 – 06:30 belongs to the previous day's night shift
        if datetime.time(0, 0, 0) <= punch_time <= datetime.time(6, 30, 0):
            return punch_date - datetime.timedelta(days=1)
        return punch_date

    return punch_date


def calculate_overlap_minutes(start_a, end_a, start_b, end_b):
    """
    Returns the overlap in whole minutes between [start_a, end_a] and [start_b, end_b].
    Returns 0 if there is no overlap or any argument is None.
    """
    if not start_a or not end_a or not start_b or not end_b:
        return 0

    latest_start  = max(start_a, start_b)
    earliest_end  = min(end_a,   end_b)

    if earliest_end > latest_start:
        delta = earliest_end - latest_start
        return int(delta.total_seconds() // 60)
    return 0


def calculate_attendance_metrics(shift_code, attendance_date, punch_in_dt, punch_out_dt=None):
    """
    Computes first_half ('PR'/'AB'), second_half ('PR'/'AB'), total_worked_minutes, and status.
    All calculations are strictly capped to the scheduled shift window via overlap logic —
    any time outside the shift is ignored.
    """
    schedule = get_shift_schedule(shift_code, attendance_date)

    if punch_out_dt is None:
        return {
            'first_half':          '',
            'second_half':         '',
            'first_half_minutes':  0,
            'second_half_minutes': 0,
            'total_worked_minutes': 0,
            'status':              'IN',
        }

    raw_fh_minutes = calculate_overlap_minutes(
        punch_in_dt, punch_out_dt,
        schedule['first_half_start'], schedule['first_half_end']
    )

    raw_sh_minutes = calculate_overlap_minutes(
        punch_in_dt, punch_out_dt,
        schedule['second_half_start'], schedule['second_half_end']
    )

    # First half borrowing rule: allow up to 60 minutes from the start of second half
    borrow_window_start = schedule['second_half_start']
    borrow_window_end = borrow_window_start + datetime.timedelta(minutes=60)
    borrowable_minutes = min(
        calculate_overlap_minutes(
            punch_in_dt, punch_out_dt,
            borrow_window_start, borrow_window_end
        ),
        60
    )

    qualifying_fh_minutes = raw_fh_minutes
    qualifying_sh_minutes = raw_sh_minutes

    if raw_fh_minutes >= HALF_DAY_MINUTES_THRESHOLD and raw_sh_minutes >= HALF_DAY_MINUTES_THRESHOLD:
        first_half_status = 'PR'
        second_half_status = 'PR'
    elif raw_fh_minutes >= HALF_DAY_MINUTES_THRESHOLD:
        first_half_status = 'PR'
        second_half_status = 'AB'
    elif raw_sh_minutes >= HALF_DAY_MINUTES_THRESHOLD:
        # Second half is PR. Since total worked time is less than 9 hours (540 min),
        # second half cannot give up time without dropping below PR.
        # Only second half is PR.
        first_half_status = 'AB'
        second_half_status = 'PR'
    else:
        # Both raw halves are below HALF_DAY_MINUTES_THRESHOLD (second half is already AB).
        # First half borrows actual worked time in borrow window (up to 60 min) to reach >= 270 min.
        if (raw_fh_minutes + borrowable_minutes) >= HALF_DAY_MINUTES_THRESHOLD:
            first_half_status = 'PR'
            second_half_status = 'AB'
            qualifying_fh_minutes = raw_fh_minutes + borrowable_minutes
        else:
            first_half_status = 'AB'
            second_half_status = 'AB'

    # Total worked minutes: overlap with the scheduled shift including 15‑minute grace on both ends
    total_worked_minutes = calculate_overlap_minutes(
        punch_in_dt, punch_out_dt,
        schedule['shift_start'], schedule['shift_end']
    )

    if first_half_status == 'PR' and second_half_status == 'PR':
        status = 'PRESENT'
    elif first_half_status == 'PR' or second_half_status == 'PR':
        status = 'HALF_DAY'
    else:
        status = 'ABSENT'

    return {
        'first_half':          first_half_status,
        'second_half':         second_half_status,
        'first_half_minutes':  qualifying_fh_minutes,
        'second_half_minutes': qualifying_sh_minutes,
        'total_worked_minutes': total_worked_minutes,
        'status':              status,
    }


def validate_punch_in_rules(employee, punch_in_dt, existing_active_record=None, existing_records=None):
    """
    Validates punch-in datetime against strict rules. Raises ValidationError with a
    clear message on any violation.

    Rules (in order):
    0. Reject if punch_in_dt is in the future.
    1. Reject if there is already an active (not yet punched-out) record for this employee.
    2. Reject if punch_in_dt is outside the allowed window for the shift:
         GS: 11:00 AM – 9:00 PM   (shift_start - 1h  to  shift_end)
         NS: 8:30 PM – 6:30 AM    (shift_start - 1h  to  shift_end next day)
    3. Reject if a COMPLETED attendance record already exists for this employee on the
       same attendance_date (i.e. they already punched in and out today — one record per day).
    """

    tz = timezone.get_current_timezone()
    if timezone.is_naive(punch_in_dt):
        punch_in_dt = timezone.make_aware(punch_in_dt, tz)

    # ── Rule 0: punch_in_dt cannot be in the future ──────────────────────────
    if punch_in_dt > timezone.now():
        raise ValidationError("Punch-in cannot be for a future date or time.")

    # ── Rule 1: active punch-in already exists ──────────────────────────────
    if existing_active_record:
        raise ValidationError(
            "Employee already has an active punch-in. "
            "Please punch out before starting a new session."
        )

    # ── Determine attendance_date for this punch_in ──────────────────────────
    shift_code      = employee.shift
    attendance_date = determine_attendance_date(shift_code, punch_in_dt)
    schedule        = get_shift_schedule(shift_code, attendance_date)

    allowed_start = schedule['allowed_punch_in_start']
    allowed_end   = schedule['allowed_punch_in_end']

    # ── Rule 2: punch_in must be within the allowed window ───────────────────
    if not (allowed_start <= punch_in_dt <= allowed_end):
        start_str = allowed_start.strftime('%I:%M %p')
        end_str   = allowed_end.strftime('%I:%M %p')

        if punch_in_dt > allowed_end:
            # Tried to punch in AFTER the shift has already ended
            if shift_code == SHIFT_NS:
                raise ValidationError(
                    f"Punch-in is not allowed after the Night Shift has ended ({end_str})."
                )
            else:
                raise ValidationError(
                    f"Punch-in is not allowed after the General Shift has ended ({end_str})."
                )
        else:
            # Too early
            if shift_code == SHIFT_NS:
                raise ValidationError(
                    f"Punch-in for Night Shift (NS) is only allowed between {start_str} and {end_str} next morning."
                )
            else:
                raise ValidationError(
                    f"Punch-in for General Shift (GS) is only allowed between {start_str} and {end_str}."
                )

    # ── Rule 3: duration overlap & one record per attendance_date ─────────────
    if existing_records is not None:
        for rec in existing_records:
            if rec.punch_out is not None:
                # 3a. Reject if punch_in_dt falls within an existing session duration [punch_in, punch_out]
                if rec.punch_in <= punch_in_dt <= rec.punch_out:
                    raise ValidationError(
                        "Attendance already completed or active during this session. Duplicate punch-in is not allowed."
                    )
                # 3b. Reject if a completed record already exists for this attendance_date
                if rec.attendance_date == attendance_date:
                    raise ValidationError(
                        f"Attendance already completed for {employee.employee_id} "
                        f"on {attendance_date}. Duplicate punch-in is not allowed."
                    )
            else:
                # Active record (punch_out is None)
                if punch_in_dt >= rec.punch_in:
                    raise ValidationError(
                        "Employee already has an active punch-in. "
                        "Please punch out before starting a new session."
                    )


def validate_punch_out_rules(punch_in_dt, punch_out_dt, shift_code=None, attendance_date=None):
    """
    Validates punch-out rules and returns the punch_out_dt unchanged.

    Rules:
    1. A valid punch-in must exist.
    2. punch_out must not be before punch_in.
    3. punch_out must not be in the future.

    NOTE: The actual punch_out time is stored as-is (e.g. 8:30 AM even for NS).
    Time calculation is automatically capped to the shift window by calculate_overlap_minutes
    inside calculate_attendance_metrics, so overtime outside the shift is never COUNTED
    but the real departure time is always STORED correctly.
    """
    tz = timezone.get_current_timezone()
    if timezone.is_naive(punch_out_dt):
        punch_out_dt = timezone.make_aware(punch_out_dt, tz)

    if punch_out_dt > timezone.now():
        raise ValidationError("Punch-out cannot be for a future date or time.")
    if not punch_in_dt:
        raise ValidationError("Cannot punch out without a valid punch-in record.")

    if punch_out_dt < punch_in_dt:
        raise ValidationError("Punch-out time cannot be earlier than punch-in time.")

    return punch_out_dt

import datetime
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from attendance.models import Employee, Attendance
from attendance.calculator import (
    SHIFT_GS,
    SHIFT_NS,
    get_shift_schedule,
    determine_attendance_date,
    calculate_attendance_metrics,
    validate_punch_in_rules,
    validate_punch_out_rules,
)


class AttendanceCalculatorTests(TestCase):
    """
    All original tests + new tests covering every scenario from the spec.
    """

    def setUp(self):
        self.tz         = timezone.get_current_timezone()
        self.date_sep8  = datetime.date(2026, 9, 8)
        self.date_sep7  = datetime.date(2026, 9, 7)

        self.emp_gs = Employee.objects.create(employee_id='GS_EMP', name='GS Worker', shift=SHIFT_GS)
        self.emp_ns = Employee.objects.create(employee_id='NS_EMP', name='NS Worker', shift=SHIFT_NS)

    def aw(self, dt):
        """Make a naive datetime timezone-aware."""
        return timezone.make_aware(dt, self.tz)

    # ─────────────────────────────────────────────────────────────────
    # ORIGINAL TESTS (kept intact)
    # ─────────────────────────────────────────────────────────────────

    def test_gs_full_day_present(self):
        """GS 12:00 PM → 9:00 PM = 540 min, PRESENT"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 12, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 21, 0))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['total_worked_minutes'], 540)
        self.assertEqual(m['status'], 'PRESENT')

    def test_gs_first_half_only(self):
        """GS 12:00 PM → 4:30 PM = 270 min, HALF_DAY"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 12, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 16, 30))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['total_worked_minutes'], 270)
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_gs_borrow_up_to_one_hour_to_reach_pr(self):
        """Employee starts late, works into early second half, borrowing makes first half PR while second half remains AB.
        Example: punch in at 12:30 PM, punch out at 5:00 PM.
        - FH overlap (11:45-4:45) = 255 minutes
        - Borrow window (4:15-5:15) overlap = 45 minutes
        - Qualifying FH = 300 minutes => PR
        - SH overlap = 45 minutes => AB
        """
        punch_in = self.aw(datetime.datetime(2026, 9, 8, 12, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 17, 0))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'], 'PR')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_gs_borrow_cap_at_sixty_minutes(self):
        """Borrowing is capped at 60 minutes even if employee works longer into second half.
        Example: punch in at 12:00 PM, punch out at 7:00 PM.
        - FH overlap = 285 minutes (12:00-4:45)
        - Borrow window overlap = 60 minutes (4:15-5:15 fully covered)
        - Qualifying FH = 345 minutes => PR
        - SH overlap = 210 minutes (4:15-7:00) => AB (since <270)
        """
        punch_in = self.aw(datetime.datetime(2026, 9, 8, 12, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 19, 0))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'], 'PR')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['status'], 'HALF_DAY')
        # Ensure total worked minutes reflect shift caps (up to shift end 9:15 PM)
        self.assertEqual(m['total_worked_minutes'], 420)

    def test_gs_example1_late_start_full_shift(self):
        """
        GS Example 1: 1:00 PM → 9:00 PM
        First half qualifying time is short (225 min < 270 min).
        Second half has 285 min. If 45 min borrowed by first half, second half drops to 240 min (< 270 min).
        Because second half would become AB if borrowed, borrowing is NOT allowed.
        Expected: First Half = AB, Second Half = PR.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 13, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 21, 0))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'AB')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_gs_example2_late_start_early_leave(self):
        """
        GS Example 2: 12:50 PM → 5:30 PM
        First half has 235 min (< 270 min). Second half has 75 min (< 270 min -> already AB).
        Worked overlap in borrow window (4:15-5:15 / 4:30-5:30) is 60 min.
        First half borrows time to reach >= 270 min.
        Expected: First Half = PR, Second Half = AB.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 12, 50))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 17, 30))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_ns_example1_late_start_full_shift(self):
        """
        NS Example 1: 10:30 PM → 6:30 AM next day
        First half is 225 min (< 270 min). Second half is 285 min.
        Borrowing would reduce second half below 270 min, so borrowing is prohibited.
        Expected: First Half = AB, Second Half = PR.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 22, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  6, 30))
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'AB')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_ns_example2_late_start_early_leave(self):
        """
        NS Example 2: 10:20 PM → 3:00 AM next day
        First half is 235 min (< 270 min). Second half is 75 min (< 270 min -> already AB).
        First half borrows worked overlap from second half borrow window to reach >= 270 min.
        Expected: First Half = PR, Second Half = AB.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 22, 20))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  3,  0))
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_gs_late_start_total_less_than_nine_hours_second_half_pr_only(self):
        """
        GS 12:30 PM → 9:15 PM (8h 45m worked < 9 hours total):
        First half = 255 min (< 270 min). Second half = 300 min (>= 270 min).
        Since total worked time is not 9 hours, second half cannot give up time to make first half PR.
        Expected: First Half = AB, Second Half = PR, Status = HALF_DAY.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 12, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 21, 15))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'AB')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['status'], 'HALF_DAY')


    def test_ns_afternoon_punch_in_prohibited(self):
        """NS: punch in at 3:00 PM must be rejected"""
        punch = self.aw(datetime.datetime(2026, 9, 8, 15, 0))
        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_ns, punch)
        self.assertIn("Night Shift", str(ctx.exception))

    def test_ns_valid_evening_punch_in(self):
        """NS: punch in at 8:45 PM (within 8:30 PM window) must be accepted"""
        punch = self.aw(datetime.datetime(2026, 9, 8, 20, 45))
        try:
            validate_punch_in_rules(self.emp_ns, punch)
        except ValidationError:
            self.fail("Unexpected ValidationError for valid NS evening punch-in")

    def test_ns_too_early_punch_in_prohibited(self):
        """NS: punch in at 8:00 PM (before 8:30 PM 1-hr lead time) must be rejected"""
        punch = self.aw(datetime.datetime(2026, 9, 8, 20, 0))
        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_ns, punch)
        self.assertIn("Night Shift", str(ctx.exception))

    def test_gs_early_punch_in_outside_window_prohibited(self):
        """GS: punch in at 10:30 AM (before 11:00 AM 1-hr lead time) must be rejected"""
        punch = self.aw(datetime.datetime(2026, 9, 8, 10, 30))
        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_gs, punch)
        self.assertIn("General Shift", str(ctx.exception))

    def test_duplicate_active_punch_in_prohibited(self):
        """Cannot punch in while an active record already exists"""
        att = Attendance.objects.create(
            employee=self.emp_gs,
            attendance_date=self.date_sep8,
            shift=SHIFT_GS,
            punch_in=self.aw(datetime.datetime(2026, 9, 8, 12, 0)),
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_gs, self.aw(datetime.datetime(2026, 9, 8, 13, 0)),
                                    existing_active_record=att)
        self.assertIn("active punch-in", str(ctx.exception))

    def test_punch_out_before_punch_in_prohibited(self):
        """Punch-out before punch-in must be rejected"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 14, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 13, 0))
        with self.assertRaises(ValidationError):
            validate_punch_out_rules(punch_in, punch_out)

    def test_gs_punchout_beyond_shift_end_capped(self):
        """GS 12:00 PM → 10:00 PM: punch_out stored as 10 PM, but capped at grace end 9:15 PM (555 min counted)"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 12, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 7, 22, 0))
        returned  = validate_punch_out_rules(punch_in, punch_out, SHIFT_GS, self.date_sep7)
        # Actual punch_out is stored unchanged
        self.assertEqual(returned, punch_out, "punch_out must be stored as actual time (not capped)")
        # Calculation via overlap counts up to 9:15 PM grace end
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep7, punch_in, returned)
        self.assertEqual(m['total_worked_minutes'], 555)

    def test_gs_late_punch_in_capped_correctly(self):
        """GS 8:00 PM → 10:00 PM: 8:00 PM to 9:15 PM (grace end) = 75 min"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 20, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 7, 22, 0))
        returned  = validate_punch_out_rules(punch_in, punch_out, SHIFT_GS, self.date_sep7)
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep7, punch_in, returned)
        self.assertEqual(m['total_worked_minutes'], 75)

    def test_ns_punchout_beyond_shift_end_capped(self):
        """NS 9:30 PM → 7:30 AM: stored as 7:30 AM, calculation caps at 6:45 AM grace end (555 min)"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 21, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  7, 30))
        returned  = validate_punch_out_rules(punch_in, punch_out, SHIFT_NS, self.date_sep7)
        # Actual time stored unchanged
        self.assertEqual(returned, punch_out, "punch_out must be stored as actual time (7:30 AM)")
        # Calculation caps at 6:45 AM
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, returned)
        self.assertEqual(m['total_worked_minutes'], 555)

    # ─────────────────────────────────────────────────────────────────
    # NEW SCENARIO TESTS (from spec & grace window requirements)
    # ─────────────────────────────────────────────────────────────────

    def test_gs_1250pm_to_500pm_is_absent(self):
        """
        GS 12:50 PM → 5:00 PM:
        Total worked time is 250 minutes (< 270 minutes threshold).
        Employee didn't work enough 270 mins, so first half and second half are AB and status is ABSENT.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 12, 50))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 17,  0))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['total_worked_minutes'], 250)
        self.assertEqual(m['first_half'],  'AB')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['status'], 'ABSENT')


    def test_gs_grace_total_worked_1130am_to_417pm(self):
        """
        GS 11:30 AM → 4:17 PM:
        Counting starts at grace start (11:45 AM), so 11:45 AM → 4:17 PM = 272 minutes.
        First Half = PR (272 min >= 270 min), Second Half = AB (2 min), Status = HALF_DAY.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 11, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 16, 17))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['total_worked_minutes'], 272)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_ns_grace_total_worked_900pm_to_147am(self):
        """
        NS 9:00 PM → 1:47 AM next day:
        Counting starts at grace start (9:15 PM), so 9:15 PM → 1:47 AM = 272 minutes.
        First Half = PR (272 min >= 270 min), Second Half = AB (2 min), Status = HALF_DAY.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 21,  0))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  1, 47))
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, punch_out)
        self.assertEqual(m['total_worked_minutes'], 272)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'AB')
        self.assertEqual(m['status'], 'HALF_DAY')

    def test_gs_grace_window_1210pm_to_910pm(self):
        """GS 12:10 PM → 9:10 PM: 15-min grace window allows PR for both halves"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 12, 10))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 21, 10))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['status'], 'PRESENT')

    def test_gs_grace_window_1150am_to_850pm(self):
        """GS 11:50 AM → 8:50 PM: 15-min grace window allows PR for both halves"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 8, 11, 50))
        punch_out = self.aw(datetime.datetime(2026, 9, 8, 20, 50))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['status'], 'PRESENT')

    def test_ns_grace_window_940pm_to_640am(self):
        """NS 9:40 PM → 6:40 AM next day: 15-min grace window allows PR for both halves"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 21, 40))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  6, 40))
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['status'], 'PRESENT')

    def test_ns_grace_window_920pm_to_620am(self):
        """NS 9:20 PM → 6:20 AM next day: 15-min grace window allows PR for both halves"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 21, 20))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  6, 20))
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, punch_out)
        self.assertEqual(m['first_half'],  'PR')
        self.assertEqual(m['second_half'], 'PR')
        self.assertEqual(m['status'], 'PRESENT')


    def test_gs_punch_in_530pm_out_230am_caps_to_9pm(self):
        """
        SPEC: GS Punch In 5:30 PM, Punch Out 2:30 AM next day.
        Stored punch_out = 2:30 AM (actual). 5:30 PM–9:15 PM (grace end) = 225 min.
        """
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 17, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  2, 30))  # next day 2:30 AM

        returned = validate_punch_out_rules(punch_in, punch_out, SHIFT_GS, self.date_sep7)
        # Actual time stored
        self.assertEqual(returned, punch_out, "punch_out should be stored as actual time (2:30 AM)")

        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep7, punch_in, returned)
        # 5:30 PM to 9:15 PM = 225 minutes
        self.assertEqual(m['total_worked_minutes'], 225)

    def test_gs_punchout_after_10pm_capped(self):
        """GS 12:00 PM → 10:00 PM: capped to 9:15 PM (grace end) → 555 min, PRESENT"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 12, 0))
        punch_out = self.aw(datetime.datetime(2026, 9, 7, 22, 0))
        capped = validate_punch_out_rules(punch_in, punch_out, SHIFT_GS, self.date_sep7)
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep7, punch_in, capped)
        self.assertEqual(m['total_worked_minutes'], 555)
        self.assertEqual(m['status'], 'PRESENT')

    def test_gs_punch_in_after_shift_end_rejected(self):
        """
        SPEC: GS punch-in after 9:00 PM must be rejected.
        Example: punch in at 9:01 PM.
        """
        punch = self.aw(datetime.datetime(2026, 9, 8, 21, 1))  # 9:01 PM
        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_gs, punch)
        err = str(ctx.exception)
        self.assertIn("not allowed after", err)

    def test_gs_completed_then_second_punch_in_same_date_rejected(self):
        """
        SPEC: GS Punch In → Punch Out → try Punch In again on same date → REJECT.
        """
        # Create a completed record for today
        Attendance.objects.create(
            employee=self.emp_gs,
            attendance_date=self.date_sep8,
            shift=SHIFT_GS,
            punch_in=self.aw(datetime.datetime(2026, 9, 8, 17, 30)),
            punch_out=self.aw(datetime.datetime(2026, 9, 8, 20, 30)),
        )

        # Second punch-in attempt on same date
        second_punch = self.aw(datetime.datetime(2026, 9, 8, 18, 0))
        existing_records = list(Attendance.objects.filter(employee=self.emp_gs))

        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_gs, second_punch,
                                    existing_active_record=None,
                                    existing_records=existing_records)
        self.assertIn("already completed", str(ctx.exception))

    def test_ns_full_shift_930pm_to_630am(self):
        """NS 9:30 PM → 6:30 AM next day = 540 min, PRESENT"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 21, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  6, 30))
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, punch_out)
        self.assertEqual(m['total_worked_minutes'], 540)
        self.assertEqual(m['status'], 'PRESENT')

    def test_ns_punch_out_at_8am_capped_to_630am(self):
        """NS 9:30 PM → 8:00 AM: stored as 8:00 AM (actual), capped to 6:45 AM (555 min)"""
        punch_in  = self.aw(datetime.datetime(2026, 9, 7, 21, 30))
        punch_out = self.aw(datetime.datetime(2026, 9, 8,  8,  0))
        returned  = validate_punch_out_rules(punch_in, punch_out, SHIFT_NS, self.date_sep7)
        self.assertEqual(returned, punch_out, "punch_out should be stored as actual time (8:00 AM)")
        m = calculate_attendance_metrics(SHIFT_NS, self.date_sep7, punch_in, returned)
        self.assertEqual(m['total_worked_minutes'], 555)

    def test_ns_completed_then_duplicate_punch_in_rejected(self):
        """NS: completed record → second punch-in on same attendance_date → REJECT"""
        ns_att_date = self.date_sep7  # 7 Sep (shift starts 7 Sep 9:30 PM)

        Attendance.objects.create(
            employee=self.emp_ns,
            attendance_date=ns_att_date,
            shift=SHIFT_NS,
            punch_in=self.aw(datetime.datetime(2026, 9, 7, 21, 30)),
            punch_out=self.aw(datetime.datetime(2026, 9, 8,  6, 30)),
        )

        # Second attempt: punch in at 9:45 PM on same shift night
        second_punch = self.aw(datetime.datetime(2026, 9, 7, 21, 45))
        existing_records = list(Attendance.objects.filter(employee=self.emp_ns))

        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_ns, second_punch,
                                    existing_active_record=None,
                                    existing_records=existing_records)
        self.assertIn("already completed", str(ctx.exception))

    def test_active_punch_in_half_status_is_blank(self):
        """Active punch-in record (punch_out is None) must have blank first_half and second_half (not 'AB')"""
        punch_in = self.aw(datetime.datetime(2026, 9, 8, 12, 0))
        m = calculate_attendance_metrics(SHIFT_GS, self.date_sep8, punch_in, punch_out_dt=None)
        self.assertEqual(m['first_half'], '')
        self.assertEqual(m['second_half'], '')
        self.assertEqual(m['status'], 'IN')


    def test_ns_attendance_date_correctly_assigned_for_after_midnight_punch_in(self):
        """NS punch-in at 2:00 AM (after midnight) → attendance_date = previous day"""
        punch_in = self.aw(datetime.datetime(2026, 9, 8, 2, 0))  # 2 AM on Sep 8
        att_date = determine_attendance_date(SHIFT_NS, punch_in)
        self.assertEqual(att_date, datetime.date(2026, 9, 7),
                         "Punch-in at 2 AM should belong to Sep 7 night shift")

    def test_multiday_duration_punch_in_rejected(self):
        """
        SPEC: If an employee punched in on 3 Sept and punched out on 5 Sept,
        a punch-in attempt during this duration (e.g. 4 Sept) must be rejected without time specs in error message.
        """
        date_sep3 = datetime.date(2026, 9, 3)
        punch_in_sep3 = self.aw(datetime.datetime(2026, 9, 3, 12, 0))
        punch_out_sep5 = self.aw(datetime.datetime(2026, 9, 5, 9, 0))

        Attendance.objects.create(
            employee=self.emp_gs,
            attendance_date=date_sep3,
            shift=SHIFT_GS,
            punch_in=punch_in_sep3,
            punch_out=punch_out_sep5,
        )

        # Attempt to punch in on 4 Sept at 1:00 PM (during the 3 Sept - 5 Sept session)
        punch_in_sep4 = self.aw(datetime.datetime(2026, 9, 4, 13, 0))
        existing_recs = list(Attendance.objects.filter(employee=self.emp_gs))

        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_gs, punch_in_sep4, existing_records=existing_recs)

        err_msg = str(ctx.exception)
        self.assertIn("Attendance already completed or active during this session", err_msg)
        # Ensure no time range details like "(Sep 03, 12:00 PM to..." are present in the error message
        self.assertNotIn("05:31 PM", err_msg)
        self.assertNotIn("12:00 PM", err_msg)

    def test_future_date_punch_in_rejected(self):
        """Punch-in with a future date/time must be rejected."""
        future_dt = timezone.now() + datetime.timedelta(days=1)
        with self.assertRaises(ValidationError) as ctx:
            validate_punch_in_rules(self.emp_gs, future_dt)
        self.assertIn("Punch-in cannot be for a future date or time.", str(ctx.exception))

    def test_future_date_punch_out_rejected(self):
        """Punch-out with a future date/time must be rejected."""
        punch_in = self.aw(datetime.datetime(2026, 9, 8, 12, 0))
        future_out = timezone.now() + datetime.timedelta(days=1)
        with self.assertRaises(ValidationError) as ctx:
            validate_punch_out_rules(punch_in, future_out)
        self.assertIn("Punch-out cannot be for a future date or time.", str(ctx.exception))


class EmployeeManagementAPITests(TestCase):
    """
    Tests for Employee CRUD, case-insensitive ID uniqueness, shift change, and employee deletion.
    """

    def setUp(self):
        self.emp = Employee.objects.create(
            employee_id='emp001',
            name='Test User',
            shift=SHIFT_GS
        )

    def test_case_insensitive_employee_id_creation_rejected(self):
        """If emp001 exists, creating EMP001 or Emp001 must be rejected"""
        from attendance.serializers import EmployeeSerializer
        # Attempt to create EMP001
        data = {'employee_id': 'EMP001', 'name': 'Duplicate User', 'shift': 'GS'}
        serializer = EmployeeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('employee_id', serializer.errors)
        self.assertIn('already exists', str(serializer.errors['employee_id']))

    def test_change_employee_shift(self):
        """Change employee shift from GS to NS"""
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.patch(f'/api/employees/{self.emp.id}/', {'shift': 'NS'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.shift, 'NS')

    def test_delete_employee(self):
        """Delete an existing employee"""
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.delete(f'/api/employees/{self.emp.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Employee.objects.filter(id=self.emp.id).exists())


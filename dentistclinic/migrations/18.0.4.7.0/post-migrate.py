"""Treatment lines now carry their own session date.

Lines that were linked by hand to an existing appointment get that
appointment's start and length, so the plan keeps showing when they happen.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE dental_treatment_line l
           SET planned_start = a.start_datetime,
               duration = GREATEST(COALESCE(EXTRACT(EPOCH FROM (a.stop_datetime - a.start_datetime)) / 3600.0, 0.5), 0.25)
          FROM dental_appointment a
         WHERE l.appointment_id = a.id
           AND l.planned_start IS NULL
    """)

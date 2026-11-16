from datetime import timedelta

from odoo import api, fields, models


class DentalDashboard(models.AbstractModel):
    _name = 'dental.dashboard'
    _description = 'Diş Kliniği Dashboard Verisi'

    @api.model
    def get_dashboard_data(self, company_id=None):
        company_domain = [('company_id', '=', company_id)] if company_id else []

        Appointment = self.env['dental.appointment']
        TreatmentPlan = self.env['dental.treatment.plan']
        TreatmentLine = self.env['dental.treatment.line']
        LabOrder = self.env['dental.lab.order']

        today = fields.Date.today()
        month_start = today.replace(day=1)
        today_start = fields.Datetime.to_datetime(today)
        today_end = today_start + timedelta(days=1)
        month_start_dt = fields.Datetime.to_datetime(month_start)

        appointments_today = Appointment.search_count(company_domain + [
            ('start_datetime', '>=', today_start),
            ('start_datetime', '<', today_end),
            ('state', '!=', 'cancelled'),
        ])
        appointments_month = Appointment.search_count(company_domain + [
            ('start_datetime', '>=', month_start_dt),
        ])
        no_show_month = Appointment.search_count(company_domain + [
            ('start_datetime', '>=', month_start_dt),
            ('state', '=', 'no_show'),
        ])
        website_leads_month = Appointment.search_count(company_domain + [
            ('start_datetime', '>=', month_start_dt),
            ('source', '=', 'website'),
        ])

        active_treatment_plans = TreatmentPlan.search_count(company_domain + [
            ('state', 'in', ('confirmed', 'in_progress')),
        ])
        pending_recalls = TreatmentPlan.search_count(company_domain + [
            ('state', '=', 'done'),
            ('recall_sent', '=', False),
            ('recall_date', '!=', False),
            ('recall_date', '<=', today),
        ])
        pending_lab_orders = LabOrder.search_count(company_domain + [
            ('state', 'in', ('sent', 'in_progress')),
        ])
        overdue_lab_orders = LabOrder.search_count(company_domain + [
            ('state', 'in', ('sent', 'in_progress')),
            ('expected_date', '!=', False),
            ('expected_date', '<', today),
        ])

        appointment_by_state = Appointment.read_group(
            company_domain + [('start_datetime', '>=', month_start_dt)],
            [], ['state'],
        )
        appointment_by_state_data = [
            {'state': row['state'], 'label': dict(
                Appointment._fields['state'].selection).get(row['state'], row['state']),
             'count': row['state_count']}
            for row in appointment_by_state
        ]

        appointments_by_doctor = Appointment.read_group(
            company_domain + [
                ('start_datetime', '>=', month_start_dt),
                ('doctor_id', '!=', False),
            ],
            [], ['doctor_id'],
        )
        doctor_stats = {
            row['doctor_id'][0]: {
                'doctor_name': row['doctor_id'][1],
                'appointment_count': row['doctor_id_count'],
                'completed_lines': 0,
            }
            for row in appointments_by_doctor
        }

        completed_lines_by_doctor = TreatmentLine.read_group(
            company_domain + [('state', '=', 'done'), ('doctor_id', '!=', False)],
            [], ['doctor_id'],
        )
        for row in completed_lines_by_doctor:
            doctor_id = row['doctor_id'][0]
            if doctor_id not in doctor_stats:
                doctor_stats[doctor_id] = {
                    'doctor_name': row['doctor_id'][1],
                    'appointment_count': 0,
                    'completed_lines': 0,
                }
            doctor_stats[doctor_id]['completed_lines'] = row['doctor_id_count']

        return {
            'appointments_today': appointments_today,
            'appointments_month': appointments_month,
            'no_show_month': no_show_month,
            'website_leads_month': website_leads_month,
            'active_treatment_plans': active_treatment_plans,
            'pending_recalls': pending_recalls,
            'pending_lab_orders': pending_lab_orders,
            'overdue_lab_orders': overdue_lab_orders,
            'appointment_by_state': appointment_by_state_data,
            'doctor_stats': list(doctor_stats.values()),
            'companies': self._get_company_options(),
            'company_comparison': self._get_company_comparison(month_start_dt, today),
        }

    @api.model
    def _get_company_options(self):
        companies = self.env.companies
        return [{'id': company.id, 'name': company.name} for company in companies]

    @api.model
    def _get_company_comparison(self, month_start_dt, today):
        Appointment = self.env['dental.appointment']
        TreatmentPlan = self.env['dental.treatment.plan']
        TreatmentLine = self.env['dental.treatment.line']

        companies = self.env.companies
        comparison = []
        for company in companies:
            domain = [('company_id', '=', company.id)]
            month_appointments = Appointment.search_count(
                domain + [('start_datetime', '>=', month_start_dt)])
            no_show = Appointment.search_count(
                domain + [('start_datetime', '>=', month_start_dt), ('state', '=', 'no_show')])
            completed_lines = TreatmentLine.search_count(
                domain + [('state', '=', 'done')])
            active_plans = TreatmentPlan.search_count(
                domain + [('state', 'in', ('confirmed', 'in_progress'))])
            no_show_rate = round((no_show / month_appointments) * 100, 1) if month_appointments else 0.0

            comparison.append({
                'company_id': company.id,
                'company_name': company.name,
                'appointment_count': month_appointments,
                'no_show_count': no_show,
                'no_show_rate': no_show_rate,
                'completed_lines': completed_lines,
                'active_treatment_plans': active_plans,
            })
        return comparison

from datetime import datetime, timedelta

from odoo import api, fields, models


class DentalAppointment(models.Model):
    _name = 'dental.appointment'
    _description = 'Diş Hekimliği Randevusu'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'dental.whatsapp.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(string='Randevu No', compute='_compute_name', store=True)
    patient_id = fields.Many2one('res.partner', string='Hasta', required=True)
    doctor_id = fields.Many2one(
        'hr.employee', string='Hekim',
        domain=[('is_dentist', '=', True)])
    company_id = fields.Many2one(
        'res.company', string='Klinik/Şube', required=True,
        default=lambda self: self.env.company)
    calendar_event_id = fields.Many2one(
        'calendar.event', string='Takvim Kaydı', ondelete='cascade')
    start_datetime = fields.Datetime(string='Başlangıç', required=True)
    stop_datetime = fields.Datetime(string='Bitiş')
    appointment_type = fields.Selection([
        ('examination', 'Muayene'),
        ('control', 'Kontrol'),
        ('treatment', 'Tedavi'),
        ('emergency', 'Acil'),
    ], string='Randevu Türü', default='examination', required=True)
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('confirmed', 'Onaylı'),
        ('done', 'Geldi'),
        ('no_show', 'Gelmedi'),
        ('cancelled', 'İptal'),
    ], string='Durum', default='draft', required=True, tracking=True)
    reminder_sent = fields.Boolean(string='Hatırlatma Gönderildi', default=False)
    treatment_plan_id = fields.Many2one(
        'dental.treatment.plan', string='Tedavi Planı')
    notes = fields.Text(string='Notlar')
    source = fields.Selection([
        ('backend', 'Klinik'),
        ('website', 'Web Sitesi'),
    ], string='Kaynak', default='backend', required=True)

    @api.depends('patient_id', 'start_datetime')
    def _compute_name(self):
        for appointment in self:
            if appointment.patient_id and appointment.start_datetime:
                appointment.name = '%s - %s' % (
                    appointment.patient_id.name,
                    appointment.start_datetime,
                )
            else:
                appointment.name = 'Yeni Randevu'

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_no_show(self):
        self.write({'state': 'no_show'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model_create_multi
    def create(self, vals_list):
        appointments = super().create(vals_list)
        for appointment in appointments:
            appointment._sync_calendar_event()
        return appointments

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ('start_datetime', 'stop_datetime', 'patient_id', 'doctor_id')):
            for appointment in self:
                appointment._sync_calendar_event()
        return res

    @api.model
    def _cron_send_appointment_reminders(self, hours_before=24):
        now = fields.Datetime.now()
        window_start = now
        window_end = now + timedelta(hours=hours_before)
        appointments = self.search([
            ('state', '=', 'confirmed'),
            ('reminder_sent', '=', False),
            ('start_datetime', '>=', window_start),
            ('start_datetime', '<=', window_end),
        ])
        mail_template = self.env.ref(
            'dentistclinic.mail_template_appointment_reminder', raise_if_not_found=False)
        sms_template = self.env.ref(
            'dentistclinic.sms_template_appointment_reminder', raise_if_not_found=False)
        for appointment in appointments:
            if mail_template and appointment.patient_id.email:
                mail_template.send_mail(appointment.id, force_send=True)
            if sms_template and appointment.patient_id.mobile:
                body = sms_template._render_field('body', appointment.ids)[appointment.id]
                appointment._message_sms(
                    body, partner_ids=appointment.patient_id.ids)
            appointment._send_whatsapp_template(
                'dentistclinic.whatsapp_template_appointment_reminder')
            appointment.reminder_sent = True

    @api.model
    def _parse_preferred_date(self, date_str):
        if not date_str:
            return False
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return False
        return parsed_date.replace(hour=10, minute=0, second=0)

    @api.model
    def _default_fallback_datetime(self):
        return fields.Datetime.now() + timedelta(days=1)

    def _sync_calendar_event(self):
        self.ensure_one()
        event_vals = {
            'name': self.name,
            'start': self.start_datetime,
            'stop': self.stop_datetime or self.start_datetime,
            'partner_ids': [(6, 0, self.patient_id.ids)],
        }
        if self.calendar_event_id:
            self.calendar_event_id.write(event_vals)
        else:
            self.calendar_event_id = self.env['calendar.event'].create(event_vals)

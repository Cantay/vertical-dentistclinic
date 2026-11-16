from odoo import api, fields, models


class DentalLabOrder(models.Model):
    _name = 'dental.lab.order'
    _description = 'Diş Laboratuvar Talebi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Talep No', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code('dental.lab.order'))
    treatment_line_id = fields.Many2one(
        'dental.treatment.line', string='Tedavi Satırı', required=True, ondelete='cascade')
    treatment_plan_id = fields.Many2one(
        related='treatment_line_id.plan_id', string='Tedavi Planı', store=True)
    patient_id = fields.Many2one(
        related='treatment_line_id.patient_id', string='Hasta', store=True)
    company_id = fields.Many2one(
        related='treatment_line_id.company_id', string='Klinik/Şube', store=True)
    lab_partner_id = fields.Many2one(
        'res.partner', string='Laboratuvar', required=True,
        domain=[('is_company', '=', True)])
    work_type = fields.Selection([
        ('crown', 'Kuron'),
        ('bridge', 'Köprü'),
        ('denture', 'Protez'),
        ('implant', 'İmplant Üstü Yapı'),
        ('aligner', 'Şeffaf Plak'),
        ('other', 'Diğer'),
    ], string='İş Türü', default='crown', required=True)
    tooth_number = fields.Char(related='treatment_line_id.tooth_number', string='Diş No')
    sent_date = fields.Date(string='Gönderim Tarihi', default=fields.Date.today)
    expected_date = fields.Date(string='Beklenen Teslim Tarihi')
    received_date = fields.Date(string='Teslim Alınan Tarih')
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('sent', 'Laboratuvara Gönderildi'),
        ('in_progress', 'Üretimde'),
        ('received', 'Teslim Alındı'),
        ('cancelled', 'İptal'),
    ], string='Durum', default='draft', required=True, tracking=True)
    notes = fields.Text(string='Notlar')

    def action_send(self):
        self.write({'state': 'sent', 'sent_date': fields.Date.today()})

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_receive(self):
        self.write({'state': 'received', 'received_date': fields.Date.today()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def _cron_notify_overdue_lab_orders(self):
        today = fields.Date.today()
        overdue_orders = self.search([
            ('state', 'in', ('sent', 'in_progress')),
            ('expected_date', '!=', False),
            ('expected_date', '<', today),
        ])
        for order in overdue_orders:
            order.message_post(
                body='Bu laboratuvar talebi beklenen teslim tarihini (%s) geçti.' % order.expected_date,
            )

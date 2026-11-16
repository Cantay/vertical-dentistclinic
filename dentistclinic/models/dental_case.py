from odoo import fields, models


class DentalCase(models.Model):
    _name = 'dental.case'
    _description = 'Diş Vakası'
    _order = 'id desc'

    name = fields.Char(string='Vaka Başlığı', required=True)
    patient_id = fields.Many2one('res.partner', string='Hasta', required=True)
    doctor_id = fields.Many2one(
        'hr.employee', string='Hekim',
        domain=[('is_dentist', '=', True)])
    company_id = fields.Many2one(
        'res.company', string='Klinik/Şube', required=True,
        default=lambda self: self.env.company)
    treatment_plan_id = fields.Many2one('dental.treatment.plan', string='Tedavi Planı')
    description = fields.Text(string='Açıklama')
    state = fields.Selection([
        ('open', 'Açık'),
        ('closed', 'Kapalı'),
    ], string='Durum', default='open', required=True)

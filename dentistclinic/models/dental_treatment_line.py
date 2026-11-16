from odoo import fields, models


class DentalTreatmentLine(models.Model):
    _name = 'dental.treatment.line'
    _description = 'Diş Tedavi Satırı'

    plan_id = fields.Many2one(
        'dental.treatment.plan', string='Tedavi Planı',
        required=True, ondelete='cascade')
    patient_id = fields.Many2one(
        related='plan_id.patient_id', string='Hasta', store=True)
    company_id = fields.Many2one(
        related='plan_id.company_id', string='Klinik/Şube', store=True)
    tooth_number = fields.Char(string='Diş No (FDI)')
    procedure_id = fields.Many2one('product.product', string='Tedavi/Prosedür')
    doctor_id = fields.Many2one(
        'hr.employee', string='Hekim',
        domain=[('is_dentist', '=', True)])
    appointment_id = fields.Many2one('dental.appointment', string='Randevu')
    state = fields.Selection([
        ('planned', 'Planlandı'),
        ('done', 'Uygulandı'),
        ('invoiced', 'Faturalandı'),
    ], string='Durum', default='planned', required=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Satış Satırı')
    notes = fields.Text(string='Notlar')
    lab_order_ids = fields.One2many(
        'dental.lab.order', 'treatment_line_id', string='Laboratuvar Talepleri')

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    dental_treatment_line_id = fields.Many2one(
        'dental.treatment.line', string='Tedavi Satırı')

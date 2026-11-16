from odoo import api, fields, models


class DentalCommission(models.Model):
    _name = 'dental.commission'
    _description = 'Sağlık Turizmi Acente Komisyonu'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Komisyon No', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code('dental.commission'))
    agency_id = fields.Many2one(
        'res.partner', string='Acente', required=True,
        domain=[('is_health_tourism_agency', '=', True)])
    treatment_plan_id = fields.Many2one(
        'dental.treatment.plan', string='Tedavi Planı', required=True, ondelete='cascade')
    patient_id = fields.Many2one(
        related='treatment_plan_id.patient_id', string='Hasta', store=True)
    company_id = fields.Many2one(
        related='treatment_plan_id.company_id', string='Klinik/Şube', store=True)
    invoice_id = fields.Many2one('account.move', string='Fatura', required=True)
    commission_rate = fields.Float(string='Komisyon Oranı (%)', required=True)
    invoice_amount = fields.Monetary(string='Fatura Tutarı', currency_field='currency_id')
    amount = fields.Monetary(string='Komisyon Tutarı', currency_field='currency_id')
    currency_id = fields.Many2one(related='invoice_id.currency_id', string='Para Birimi', store=True)
    state = fields.Selection([
        ('pending', 'Bekliyor'),
        ('invoiced', 'Faturalandı'),
        ('paid', 'Ödendi'),
    ], string='Durum', default='pending', required=True, tracking=True)
    payment_move_id = fields.Many2one('account.move', string='Ödeme Faturası')

    _sql_constraints = [
        ('unique_invoice', 'UNIQUE(invoice_id)',
         'Bu fatura için zaten bir komisyon kaydı oluşturulmuş.'),
    ]

    def action_mark_invoiced(self):
        self.write({'state': 'invoiced'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    @api.model
    def _create_from_invoice(self, invoice):
        """Fatura onaylandığında, ilişkili tedavi planının acentesi varsa
        otomatik komisyon kaydı oluşturur. Fatura tek bir tedavi planına
        bağlı olmalıdır (sale_order_id.dental_treatment_plan_id)."""
        plan = self.env['dental.treatment.plan'].search([
            ('sale_order_id.invoice_ids', 'in', invoice.id),
        ], limit=1)
        if not plan or not plan.patient_id.referring_agency_id:
            return self.browse()
        if self.search([('invoice_id', '=', invoice.id)], limit=1):
            return self.browse()
        agency = plan.patient_id.referring_agency_id
        rate = plan.commission_rate or agency.commission_rate
        amount = invoice.amount_total * (rate / 100.0)
        return self.create({
            'agency_id': agency.id,
            'treatment_plan_id': plan.id,
            'invoice_id': invoice.id,
            'commission_rate': rate,
            'invoice_amount': invoice.amount_total,
            'amount': amount,
            'state': 'invoiced',
        })

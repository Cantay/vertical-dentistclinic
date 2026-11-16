from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DentalTravelInfo(models.Model):
    _name = 'dental.travel.info'
    _description = 'Yurtdışı Hasta Seyahat/Konaklama Bilgisi'
    _inherit = ['mail.thread']
    _order = 'arrival_date desc'

    patient_id = fields.Many2one('res.partner', string='Hasta', required=True)
    treatment_plan_id = fields.Many2one('dental.treatment.plan', string='Tedavi Planı')
    company_id = fields.Many2one(
        'res.company', string='Klinik/Şube', required=True,
        default=lambda self: self.env.company)

    arrival_date = fields.Datetime(string='Varış Tarihi')
    departure_date = fields.Datetime(string='Ayrılış Tarihi')
    flight_number_arrival = fields.Char(string='Varış Uçuş No')
    flight_number_departure = fields.Char(string='Ayrılış Uçuş No')
    hotel_name = fields.Char(string='Otel Adı')
    hotel_address = fields.Text(string='Otel Adresi')
    needs_transfer = fields.Boolean(string='Transfer Gerekiyor')
    transfer_notes = fields.Text(string='Transfer Notları')
    needs_translator = fields.Boolean(string='Tercüman Gerekiyor')
    translator_language = fields.Selection(
        selection='_get_translator_language_selection', string='Tercüman Dili')
    notes = fields.Text(string='Notlar')

    @api.model
    def _get_translator_language_selection(self):
        return self.env['res.lang'].get_installed()

    @api.constrains('arrival_date', 'departure_date')
    def _check_dates(self):
        for record in self:
            if record.arrival_date and record.departure_date \
                    and record.departure_date < record.arrival_date:
                raise ValidationError(
                    self.env._('Ayrılış tarihi varış tarihinden önce olamaz.'))

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_dental_patient = fields.Boolean(string='Hasta')
    identification_no = fields.Char(string='TC Kimlik No')
    passport_no = fields.Char(string='Pasaport No')
    nationality_id = fields.Many2one('res.country', string='Uyruk')
    is_international_patient = fields.Boolean(
        string='Uluslararası Hasta', compute='_compute_is_international_patient',
        store=True)
    birth_date = fields.Date(string='Doğum Tarihi')
    blood_type = fields.Selection([
        ('a_pos', 'A Rh+'),
        ('a_neg', 'A Rh-'),
        ('b_pos', 'B Rh+'),
        ('b_neg', 'B Rh-'),
        ('ab_pos', 'AB Rh+'),
        ('ab_neg', 'AB Rh-'),
        ('o_pos', '0 Rh+'),
        ('o_neg', '0 Rh-'),
    ], string='Kan Grubu')
    allergies = fields.Text(string='Alerjiler')
    anamnesis = fields.Text(string='Anamnez')
    referral_source = fields.Selection([
        ('website', 'Web Sitesi'),
        ('referral', 'Hasta Yönlendirmesi'),
        ('social_media', 'Sosyal Medya'),
        ('advertisement', 'Reklam'),
        ('agency', 'Sağlık Turizmi Acentesi'),
        ('other', 'Diğer'),
    ], string='Nereden Geldi')
    referring_agency_id = fields.Many2one(
        'res.partner', string='Yönlendiren Acente',
        domain=[('is_health_tourism_agency', '=', True)])

    is_health_tourism_agency = fields.Boolean(string='Sağlık Turizmi Acentesi')
    commission_rate = fields.Float(
        string='Varsayılan Komisyon Oranı (%)',
        help='Bu acente için tedavi planlarında varsayılan olarak önerilecek komisyon oranı.')
    commission_ids = fields.One2many(
        'dental.commission', 'agency_id', string='Komisyon Kayıtları')
    dental_patient_ids = fields.One2many(
        'res.partner', 'referring_agency_id', string='Yönlendirilen Hastalar')

    appointment_ids = fields.One2many(
        'dental.appointment', 'patient_id', string='Randevular')
    treatment_plan_ids = fields.One2many(
        'dental.treatment.plan', 'patient_id', string='Tedavi Planları')
    travel_info_ids = fields.One2many(
        'dental.travel.info', 'patient_id', string='Seyahat Bilgileri')
    appointment_count = fields.Integer(
        string='Randevu Sayısı', compute='_compute_dental_counts')
    treatment_plan_count = fields.Integer(
        string='Tedavi Planı Sayısı', compute='_compute_dental_counts')

    def _compute_dental_counts(self):
        for partner in self:
            partner.appointment_count = len(partner.appointment_ids)
            partner.treatment_plan_count = len(partner.treatment_plan_ids)

    @api.depends('nationality_id', 'country_id')
    def _compute_is_international_patient(self):
        tr_country = self.env.ref('base.tr', raise_if_not_found=False)
        for partner in self:
            countries = partner.nationality_id | partner.country_id
            partner.is_international_patient = bool(countries) and tr_country not in countries

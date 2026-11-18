from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    dental_case_count = fields.Integer(string='Vaka', compute='_compute_dental_counts')
    dental_consent_count = fields.Integer(string='Onam', compute='_compute_dental_counts')
    dental_lab_order_count = fields.Integer(string='Laboratuvar', compute='_compute_dental_counts')
    dental_travel_count = fields.Integer(string='Seyahat', compute='_compute_dental_counts')
    dental_invoice_count = fields.Integer(string='Fatura', compute='_compute_dental_counts')
    dental_upcoming_appointment = fields.Datetime(
        string='Sıradaki Randevu', compute='_compute_dental_counts')

    def _compute_dental_counts(self):
        def counts(model, field='patient_id', extra=()):
            if model not in self.env:
                return {}
            groups = self.env[model].sudo()._read_group(
                [(field, 'in', self.ids), *extra], [field], ['__count'])
            return {partner.id: count for partner, count in groups}
        cases = counts('dental.case')
        consents = counts('dental.consent')
        labs = counts('dental.lab.order')
        travels = counts('dental.travel.info')
        invoices = counts('account.move', 'partner_id',
                          [('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '!=', 'cancel')])
        now = fields.Datetime.now()
        for partner in self:
            partner.appointment_count = len(partner.appointment_ids)
            partner.treatment_plan_count = len(partner.treatment_plan_ids)
            partner.dental_case_count = cases.get(partner.id, 0)
            partner.dental_consent_count = consents.get(partner.id, 0)
            partner.dental_lab_order_count = labs.get(partner.id, 0)
            partner.dental_travel_count = travels.get(partner.id, 0)
            partner.dental_invoice_count = invoices.get(partner.id, 0)
            upcoming = partner.appointment_ids.filtered(
                lambda a: a.start_datetime and a.start_datetime >= now and a.state in ('draft', 'confirmed'))
            partner.dental_upcoming_appointment = min(upcoming.mapped('start_datetime')) if upcoming else False

    # ------------------------------------------------------------------
    # Patient form buttons
    # ------------------------------------------------------------------

    def _dental_open(self, model, name, domain, context=None, views='list,form'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': views,
            'domain': domain,
            'context': dict(context or {}),
        }

    def action_dental_appointments(self):
        return self._dental_open('dental.appointment', _('Randevular'), [('patient_id', '=', self.id)],
                                 {'default_patient_id': self.id}, 'calendar,list,form')

    def action_dental_treatment_plans(self):
        return self._dental_open('dental.treatment.plan', _('Tedavi Planları'), [('patient_id', '=', self.id)],
                                 {'default_patient_id': self.id})

    def action_dental_quotes(self):
        return self._dental_open('sale.order', _('Teklifler / Siparişler'), [('partner_id', '=', self.id)],
                                 {'default_partner_id': self.id})

    def action_dental_invoices(self):
        return self._dental_open('account.move', _('Faturalar'),
                                 [('partner_id', '=', self.id), ('move_type', 'in', ('out_invoice', 'out_refund'))],
                                 {'default_partner_id': self.id, 'default_move_type': 'out_invoice'})

    def action_dental_cases(self):
        return self._dental_open('dental.case', _('Vakalar'), [('patient_id', '=', self.id)],
                                 {'default_patient_id': self.id})

    def action_dental_consents(self):
        return self._dental_open('dental.consent', _('Onam Formları'), [('patient_id', '=', self.id)],
                                 {'default_patient_id': self.id})

    def action_dental_lab_orders(self):
        return self._dental_open('dental.lab.order', _('Laboratuvar Talepleri'), [('patient_id', '=', self.id)],
                                 {'default_patient_id': self.id})

    def action_dental_travel(self):
        return self._dental_open('dental.travel.info', _('Seyahat Bilgileri'), [('patient_id', '=', self.id)],
                                 {'default_patient_id': self.id})

    def action_dental_opportunities(self):
        return self._dental_open('crm.lead', _('Fırsatlar'), [('partner_id', '=', self.id)],
                                 {'default_partner_id': self.id, 'default_type': 'opportunity'},
                                 'kanban,list,form')

    def action_dental_quick_price(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'dentistclinic.quick_price',
            'name': _('Hızlı Fiyat'),
            'params': {'patient_id': self.id},
        }

    def action_dental_whatsapp(self):
        self.ensure_one()
        phone = ''.join(ch for ch in (self.mobile or self.phone or '') if ch.isdigit())
        if phone.startswith('00'):
            phone = phone[2:]
        elif phone.startswith('0'):
            phone = '90' + phone[1:]
        if not phone:
            raise UserError(_('Hastanın telefon numarası yok.'))
        return {'type': 'ir.actions.act_url', 'url': 'https://wa.me/%s' % phone, 'target': 'new'}

    @api.depends('nationality_id', 'country_id')
    def _compute_is_international_patient(self):
        tr_country = self.env.ref('base.tr', raise_if_not_found=False)
        for partner in self:
            countries = partner.nationality_id | partner.country_id
            partner.is_international_patient = bool(countries) and tr_country not in countries

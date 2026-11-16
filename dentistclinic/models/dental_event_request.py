from odoo import api, fields, models

TREATMENT_INTERESTS = [
    ('implant', 'İmplant'),
    ('aesthetic', 'Estetik / Zirkonyum / Lamina'),
    ('orthodontics', 'Ortodonti / Şeffaf Plak'),
    ('checkup', 'Genel Muayene'),
    ('other', 'Diğer'),
]


class DentalEventRequest(models.Model):
    _name = 'dental.event.request'
    _description = 'Dental Event Başvurusu / Talebi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Talep No', required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('dental.event.request'))
    event_id = fields.Many2one(
        'dental.event', string='Etkinlik', tracking=True, index=True,
        help='Boşsa genel talep: kişi kendi şehrinde etkinlik yapılmasını istiyor.')
    contact_name = fields.Char(string='Ad Soyad', required=True, tracking=True)
    phone = fields.Char(string='Telefon')
    email = fields.Char(string='E-posta')
    lang = fields.Char(string='Dil', help='Talebin gönderildiği website dili.')
    country_id = fields.Many2one('res.country', string='Ülke', required=True, tracking=True)
    city = fields.Char(string='Şehir', required=True, tracking=True)
    treatment_interest = fields.Selection(TREATMENT_INTERESTS, string='İlgilendiği Tedavi')
    notes = fields.Text(string='Not')
    privacy_consent = fields.Boolean(string='KVKK Onayı', readonly=True)
    privacy_consent_date = fields.Datetime(string='Onay Tarihi', readonly=True)
    source = fields.Selection([
        ('website', 'Web Sitesi'),
        ('manual', 'Manuel'),
    ], string='Kaynak', default='manual', required=True)
    state = fields.Selection([
        ('new', 'Yeni'),
        ('contacted', 'İletişime Geçildi'),
        ('invited', 'Davet Edildi / Onaylandı'),
        ('attended', 'Katıldı'),
        ('closed', 'Kapandı'),
    ], string='Durum', default='new', required=True, tracking=True)
    agency_id = fields.Many2one(
        'res.partner', string='Acente', domain=[('is_health_tourism_agency', '=', True)])
    crm_lead_id = fields.Many2one('crm.lead', string='CRM Fırsatı', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Klinik/Şube', required=True,
        default=lambda self: self.env.company)

    def action_mark_contacted(self):
        self.write({'state': 'contacted'})

    def action_mark_invited(self):
        self.write({'state': 'invited'})

    def action_mark_attended(self):
        self.write({'state': 'attended'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'new'})

    def action_convert_to_lead(self):
        self.ensure_one()
        if not self.crm_lead_id:
            team = self.env.ref('dentistclinic.crm_team_health_tourism', raise_if_not_found=False)
            interest = dict(TREATMENT_INTERESTS).get(self.treatment_interest, '')
            self.crm_lead_id = self.env['crm.lead'].create({
                'name': '%s - %s, %s' % (self.contact_name, self.city, self.country_id.name),
                'type': 'opportunity',
                'is_health_tourism': True,
                'team_id': team.id if team else False,
                'agency_id': self.agency_id.id,
                'contact_name': self.contact_name,
                'email_from': self.email,
                'phone': self.phone,
                'country_id': self.country_id.id,
                'city': self.city,
                'company_id': self.company_id.id,
                'description': '\n'.join(filter(None, [
                    'Etkinlik talebi: %s' % self.name,
                    self.event_id and 'Etkinlik: %s (%s)' % (self.event_id.name, self.event_id._website_date_label()),
                    interest and 'İlgilendiği tedavi: %s' % interest,
                    self.notes,
                ])),
            })
            self.message_post(body=self.env._('CRM fırsatı oluşturuldu: %s', self.crm_lead_id.name))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.crm_lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.onchange('event_id')
    def _onchange_event_id(self):
        if self.event_id:
            self.country_id = self.event_id.country_id
            self.city = self.event_id.city
            self.agency_id = self.agency_id or self.event_id.agency_id
            self.company_id = self.event_id.company_id

    @api.model
    def _create_from_website(self, vals):
        return self.sudo().create(dict(
            vals,
            source='website',
            state='new',
            privacy_consent=True,
            privacy_consent_date=fields.Datetime.now(),
        ))

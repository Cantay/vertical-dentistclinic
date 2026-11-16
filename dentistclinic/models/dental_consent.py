import secrets

from odoo import api, fields, models


class DentalConsent(models.Model):
    _name = 'dental.consent'
    _description = 'Diş Tedavi Onam Formu'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Onam No', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code('dental.consent'))
    treatment_plan_id = fields.Many2one(
        'dental.treatment.plan', string='Tedavi Planı', required=True, ondelete='cascade')
    patient_id = fields.Many2one(
        related='treatment_plan_id.patient_id', string='Hasta', store=True)
    company_id = fields.Many2one(
        related='treatment_plan_id.company_id', string='Klinik/Şube', store=True)
    consent_text = fields.Html(
        string='Onam Metni', required=True,
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'dentistclinic.default_consent_text',
            '<p>Planlanan diş tedavisi hakkında bilgilendirildiğimi, '
            'riskleri ve alternatifleri anladığımı, tedaviye onay verdiğimi beyan ederim.</p>'))
    access_token = fields.Char(string='Erişim Anahtarı', copy=False, readonly=True)
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('sent', 'Gönderildi'),
        ('signed', 'Onaylandı'),
        ('declined', 'Reddedildi'),
    ], string='Durum', default='draft', required=True, tracking=True)
    sent_date = fields.Datetime(string='Gönderim Tarihi')
    signed_date = fields.Datetime(string='Onay Tarihi')
    signer_name = fields.Char(string='Onaylayan Ad Soyad')
    signer_ip = fields.Char(string='Onaylayan IP')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('access_token', secrets.token_urlsafe(32))
        return super().create(vals_list)

    def action_send(self):
        mail_template = self.env.ref(
            'dentistclinic.mail_template_consent_request', raise_if_not_found=False)
        for consent in self:
            if not consent.access_token:
                consent.access_token = secrets.token_urlsafe(32)
            if mail_template and consent.patient_id.email:
                mail_template.send_mail(consent.id, force_send=True)
            consent.write({'state': 'sent', 'sent_date': fields.Datetime.now()})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def _portal_sign(self, signer_name, signer_ip):
        self.ensure_one()
        if self.state == 'signed':
            return
        self.write({
            'state': 'signed',
            'signed_date': fields.Datetime.now(),
            'signer_name': signer_name,
            'signer_ip': signer_ip,
        })

    def _portal_decline(self):
        self.ensure_one()
        if self.state == 'signed':
            return
        self.write({'state': 'declined'})

    def get_portal_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '%s/dentistclinic/consent/%s/%s' % (base_url, self.id, self.access_token)

from odoo import fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dentistclinic_health_tourism_enabled = fields.Boolean(
        related='company_id.dentistclinic_health_tourism_enabled', readonly=False,
        string='Sağlık Turizmi Modülü')
    dentistclinic_whatsapp_enabled = fields.Boolean(
        related='company_id.dentistclinic_whatsapp_enabled', readonly=False,
        string='WhatsApp Hatırlatmaları')
    dentistclinic_online_appointment_enabled = fields.Boolean(
        related='company_id.dentistclinic_online_appointment_enabled', readonly=False,
        string='Online Randevu (Website)')
    dentistclinic_lab_tracking_enabled = fields.Boolean(
        related='company_id.dentistclinic_lab_tracking_enabled', readonly=False,
        string='Laboratuvar Takibi')
    dentistclinic_consent_enabled = fields.Boolean(
        related='company_id.dentistclinic_consent_enabled', readonly=False,
        string='Dijital Onam Formu')
    dentistclinic_slot_duration = fields.Integer(
        related='company_id.dentistclinic_slot_duration', readonly=False,
        string='Online Randevu Süresi (dk)')
    dentistclinic_whatsapp_gateway_id = fields.Many2one(
        'mail.gateway', string='WhatsApp Gateway',
        domain=[('gateway_type', '=', 'whatsapp')],
        compute='_compute_dentistclinic_whatsapp_gateway_id')
    dentistclinic_whatsapp_templates_ready = fields.Boolean(
        string='WhatsApp Şablonları Hazır',
        compute='_compute_dentistclinic_whatsapp_templates_ready')

    def _compute_dentistclinic_whatsapp_gateway_id(self):
        for settings in self:
            settings.dentistclinic_whatsapp_gateway_id = self.env['mail.gateway'].search([
                ('gateway_type', '=', 'whatsapp'),
            ], limit=1)

    def _compute_dentistclinic_whatsapp_templates_ready(self):
        for settings in self:
            settings.dentistclinic_whatsapp_templates_ready = bool(
                self.env.ref(
                    'dentistclinic.whatsapp_template_appointment_reminder',
                    raise_if_not_found=False)
                and self.env.ref(
                    'dentistclinic.whatsapp_template_recall_reminder',
                    raise_if_not_found=False))

    def action_dentistclinic_create_whatsapp_templates(self):
        self.ensure_one()
        gateway = self.dentistclinic_whatsapp_gateway_id
        if not gateway:
            raise UserError(self.env._(
                'Önce bir WhatsApp gateway kaydı oluşturup Meta hesabınızı bağlamanız gerekiyor.'))

        appointment_model = self.env.ref('dentistclinic.model_dental_appointment')
        recall_model = self.env.ref('dentistclinic.model_dental_treatment_plan')

        templates_to_create = [
            ('whatsapp_template_appointment_reminder', {
                'name': 'Randevu Hatırlatma (WhatsApp)',
                'gateway_id': gateway.id,
                'model_id': appointment_model.id,
                'category': 'utility',
                'language': 'tr',
                'body': 'Randevunuzu hatırlatmak isteriz. Lütfen klinikle iletişime geçin.',
            }),
            ('whatsapp_template_recall_reminder', {
                'name': 'Kontrol Hatırlatma (WhatsApp)',
                'gateway_id': gateway.id,
                'model_id': recall_model.id,
                'category': 'utility',
                'language': 'tr',
                'body': 'Tedavinizin kontrol zamanı geldi. Randevu için bizi arayabilirsiniz.',
            }),
        ]
        IrModelData = self.env['ir.model.data']
        for xmlid_name, vals in templates_to_create:
            existing = self.env.ref('dentistclinic.%s' % xmlid_name, raise_if_not_found=False)
            if existing:
                continue
            template = self.env['mail.whatsapp.template'].create(vals)
            IrModelData.create({
                'name': xmlid_name,
                'module': 'dentistclinic',
                'model': 'mail.whatsapp.template',
                'res_id': template.id,
                'noupdate': True,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

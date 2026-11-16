from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    dentistclinic_health_tourism_enabled = fields.Boolean(
        string='Sağlık Turizmi Modülü', default=False,
        help='CRM pipeline, acente/komisyon takibi ve seyahat bilgisi özelliklerini açar.')
    dentistclinic_whatsapp_enabled = fields.Boolean(
        string='WhatsApp Hatırlatmaları', default=False,
        help='Randevu ve kontrol hatırlatmalarının WhatsApp üzerinden gönderilmesini açar.')
    dentistclinic_online_appointment_enabled = fields.Boolean(
        string='Online Randevu (Website)', default=True,
        help='Website üzerinden online randevu talep formunun kabul edilmesini açar.')
    dentistclinic_lab_tracking_enabled = fields.Boolean(
        string='Laboratuvar Takibi', default=True,
        help='Dış laboratuvar talebi takibi menüsünü ve özelliğini açar.')
    dentistclinic_consent_enabled = fields.Boolean(
        string='Dijital Onam Formu', default=True,
        help='Dijital onam formu oluşturma/gönderme özelliğini açar.')
    dentistclinic_slot_duration = fields.Integer(
        string='Online Randevu Süresi (dk)', default=30,
        help='Website rezervasyon formunda her randevu slotunun süresi.')

    @api.constrains('dentistclinic_slot_duration')
    def _check_dentistclinic_slot_duration(self):
        for company in self:
            if not 5 <= company.dentistclinic_slot_duration <= 240:
                raise ValidationError(self.env._(
                    'Online randevu süresi 5 ile 240 dakika arasında olmalıdır.'))

    _FEATURE_GROUP_XMLIDS = {
        'dentistclinic_health_tourism_enabled': 'dentistclinic.group_dentistclinic_feature_health_tourism',
        'dentistclinic_whatsapp_enabled': 'dentistclinic.group_dentistclinic_feature_whatsapp',
        'dentistclinic_online_appointment_enabled': 'dentistclinic.group_dentistclinic_feature_online_appointment',
        'dentistclinic_lab_tracking_enabled': 'dentistclinic.group_dentistclinic_feature_lab_tracking',
        'dentistclinic_consent_enabled': 'dentistclinic.group_dentistclinic_feature_consent',
    }

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._sync_feature_groups(self._FEATURE_GROUP_XMLIDS.keys())
        return companies

    def write(self, vals):
        res = super().write(vals)
        changed_fields = [f for f in self._FEATURE_GROUP_XMLIDS if f in vals]
        if changed_fields:
            self._sync_feature_groups(changed_fields)
        return res

    def _sync_feature_groups(self, field_names):
        """Klinik personeli grubundaki tüm kullanıcılara, bu şirkette açık
        olan özelliklerin teknik grubunu ekler/kaldırır. Menüler bu teknik
        gruplara bağlıdır (bkz. views/menus.xml groups="...")."""
        staff_group = self.env.ref('dentistclinic.group_dentistclinic_user', raise_if_not_found=False)
        if not staff_group:
            return
        users = staff_group.users
        if not users:
            return
        for field_name in field_names:
            xmlid = self._FEATURE_GROUP_XMLIDS.get(field_name)
            if not xmlid:
                continue
            feature_group = self.env.ref(xmlid, raise_if_not_found=False)
            if not feature_group:
                continue
            is_enabled_anywhere = bool(self.search_count([(field_name, '=', True)]))
            command = 4 if is_enabled_anywhere else 3
            feature_group.write({'users': [(command, user.id) for user in users]})

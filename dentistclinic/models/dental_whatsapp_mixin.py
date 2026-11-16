import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DentalWhatsappMixin(models.AbstractModel):
    _name = 'dental.whatsapp.mixin'
    _description = 'Diş Kliniği WhatsApp Gönderim Yardımcısı'

    def _whatsapp_get_partner(self):
        return self.patient_id

    def _send_whatsapp_template(self, template_xmlid):
        """Hastaya WhatsApp üzerinden onaylı bir şablon mesajı gönderir.

        Gateway kurulu/yapılandırılmamışsa (Meta hesabı bağlanmamışsa)
        sessizce atlanır; bu entegrasyon SMS/e-posta kanallarının yerini
        almaz, onlara ek bir kanaldır.
        """
        self.ensure_one()
        if not self.company_id.dentistclinic_whatsapp_enabled:
            return False
        if not self.patient_id.mobile:
            return False
        gateway = self.env['mail.gateway'].search([
            ('gateway_type', '=', 'whatsapp'),
            ('company_id', 'in', (self.company_id.id, False)),
        ], limit=1)
        if not gateway:
            return False
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template or template.state != 'approved':
            return False
        try:
            channel = self._whatsapp_get_channel('mobile', gateway)
        except UserError as exc:
            _logger.warning(
                'WhatsApp kanalı oluşturulamadı (%s #%s): %s',
                self._name, self.id, exc,
            )
            return False
        channel.with_context(whatsapp_template_id=template.id).message_post(
            body=template.render_body_message(),
            subtype_xmlid='mail.mt_comment',
            message_type='comment',
        )
        return True

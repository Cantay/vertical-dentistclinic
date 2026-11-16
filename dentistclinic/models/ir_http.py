from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        # Website bloklarındaki _t() çevirileri ziyaretçiye ancak bu listedeki modüllerden gider.
        return super()._get_translation_frontend_modules_name() + ['dentistclinic']

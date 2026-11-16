from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            self.env['dental.commission']._create_from_invoice(move)
        return res

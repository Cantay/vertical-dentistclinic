from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    is_health_tourism = fields.Boolean(string='Sağlık Turizmi Fırsatı')
    treatment_plan_ids = fields.One2many(
        'dental.treatment.plan', 'crm_lead_id', string='Tedavi Planları')
    agency_id = fields.Many2one(
        'res.partner', string='Acente',
        domain=[('is_health_tourism_agency', '=', True)])

    def action_create_treatment_plan(self):
        self.ensure_one()
        if self.treatment_plan_ids:
            plan = self.treatment_plan_ids[0]
        else:
            if not self.partner_id:
                self.partner_id = self.env['res.partner'].create({
                    'name': self.contact_name or self.partner_name or self.name,
                    'email': self.email_from,
                    'phone': self.phone,
                    'is_dental_patient': True,
                    'is_company': False,
                    'referring_agency_id': self.agency_id.id,
                })
            plan = self.env['dental.treatment.plan'].create({
                'patient_id': self.partner_id.id,
                'state': 'quote',
                'is_remote_quote': True,
                'crm_lead_id': self.id,
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dental.treatment.plan',
            'res_id': plan.id,
            'view_mode': 'form',
            'target': 'current',
        }

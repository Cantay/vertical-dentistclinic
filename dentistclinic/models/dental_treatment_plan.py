from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class DentalTreatmentPlan(models.Model):
    _name = 'dental.treatment.plan'
    _description = 'Diş Tedavi Planı'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'dental.whatsapp.mixin']
    _order = 'id desc'

    name = fields.Char(string='Plan Kodu', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code('dental.treatment.plan'))
    patient_id = fields.Many2one('res.partner', string='Hasta', required=True)
    doctor_id = fields.Many2one(
        'hr.employee', string='Hekim',
        domain=[('is_dentist', '=', True)])
    company_id = fields.Many2one(
        'res.company', string='Klinik/Şube', required=True,
        default=lambda self: self.env.company)
    state = fields.Selection([
        ('quote', 'Ön Teklif'),
        ('draft', 'Taslak'),
        ('confirmed', 'Onaylandı'),
        ('in_progress', 'Devam Ediyor'),
        ('done', 'Tamamlandı'),
        ('cancelled', 'İptal'),
    ], string='Durum', default='draft', required=True, tracking=True)
    is_remote_quote = fields.Boolean(
        string='Uzaktan Ön Teklif',
        help='Hasta henüz klinikte değilken, gönderilen fotoğraf/röntgen üzerinden '
             'hazırlanan bağlayıcı olmayan ön teklif.')
    line_ids = fields.One2many(
        'dental.treatment.line', 'plan_id', string='Tedavi Satırları')
    sale_order_id = fields.Many2one('sale.order', string='Satış Siparişi')
    notes = fields.Text(string='Notlar')
    crm_lead_id = fields.Many2one('crm.lead', string='CRM Fırsatı')
    commission_rate = fields.Float(
        string='Komisyon Oranı (%)',
        help='Acenteye ödenecek komisyon oranı. Boş bırakılırsa hastanın '
             'yönlendiren acentesindeki varsayılan oran kullanılır.')
    commission_ids = fields.One2many(
        'dental.commission', 'treatment_plan_id', string='Komisyon Kayıtları')
    consent_ids = fields.One2many(
        'dental.consent', 'treatment_plan_id', string='Onam Formları')
    consent_signed = fields.Boolean(
        string='Onam Alındı', compute='_compute_consent_signed')
    lab_order_ids = fields.One2many(
        'dental.lab.order', compute='_compute_lab_order_ids', string='Laboratuvar Talepleri')
    consent_feature_enabled = fields.Boolean(
        related='company_id.dentistclinic_consent_enabled', string='Onam Özelliği Açık')

    @api.depends('line_ids.lab_order_ids')
    def _compute_lab_order_ids(self):
        for plan in self:
            plan.lab_order_ids = plan.line_ids.lab_order_ids

    @api.depends('consent_ids.state')
    def _compute_consent_signed(self):
        for plan in self:
            plan.consent_signed = bool(
                plan.consent_ids.filtered(lambda c: c.state == 'signed'))

    done_date = fields.Date(string='Tamamlanma Tarihi')
    recall_months = fields.Integer(
        string='Kontrol Süresi (Ay)', default=6,
        help='Tedavi tamamlandıktan kaç ay sonra kontrol hatırlatması gönderilsin.')
    recall_date = fields.Date(
        string='Kontrol Tarihi', compute='_compute_recall_date', store=True)
    recall_sent = fields.Boolean(string='Kontrol Hatırlatması Gönderildi', default=False)

    @api.depends('done_date', 'recall_months')
    def _compute_recall_date(self):
        for plan in self:
            if plan.done_date and plan.recall_months:
                plan.recall_date = plan.done_date + relativedelta(months=plan.recall_months)
            else:
                plan.recall_date = False

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        self._sync_crm_stage('confirmed')

    def action_start(self):
        self.write({'state': 'in_progress'})
        self._sync_crm_stage('in_progress')

    def action_done(self):
        self.write({'state': 'done', 'done_date': fields.Date.today()})
        self._sync_crm_stage('done')

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self._sync_crm_stage('cancelled')

    def _sync_crm_stage(self, plan_state):
        """Tedavi planının durumu değiştiğinde, bağlı CRM fırsatının
        (sağlık turizmi pipeline'ındaki) aşamasını otomatik günceller."""
        stage_xmlid_map = {
            'confirmed': 'dentistclinic.crm_stage_health_tourism_approved',
            'in_progress': 'dentistclinic.crm_stage_health_tourism_in_clinic',
            'done': 'dentistclinic.crm_stage_health_tourism_completed',
        }
        for plan in self:
            if not plan.crm_lead_id:
                continue
            if plan_state == 'cancelled':
                plan.crm_lead_id.action_set_lost()
                continue
            if plan_state == 'done':
                plan.crm_lead_id.action_set_won()
                continue
            stage_xmlid = stage_xmlid_map.get(plan_state)
            stage = self.env.ref(stage_xmlid, raise_if_not_found=False) if stage_xmlid else False
            if stage:
                plan.crm_lead_id.stage_id = stage

    @api.model
    def _cron_send_recall_reminders(self):
        today = fields.Date.today()
        plans = self.search([
            ('state', '=', 'done'),
            ('recall_sent', '=', False),
            ('recall_date', '!=', False),
            ('recall_date', '<=', today),
        ])
        mail_template = self.env.ref(
            'dentistclinic.mail_template_recall_reminder', raise_if_not_found=False)
        sms_template = self.env.ref(
            'dentistclinic.sms_template_recall_reminder', raise_if_not_found=False)
        for plan in plans:
            if mail_template and plan.patient_id.email:
                mail_template.send_mail(plan.id, force_send=True)
            if sms_template and plan.patient_id.mobile:
                body = sms_template._render_field('body', plan.ids)[plan.id]
                plan._message_sms(body, partner_ids=plan.patient_id.ids)
            plan._send_whatsapp_template('dentistclinic.whatsapp_template_recall_reminder')
            plan.recall_sent = True

    def action_create_consent(self):
        self.ensure_one()
        consent = self.env['dental.consent'].create({
            'treatment_plan_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dental.consent',
            'res_id': consent.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_sale_order(self):
        self.ensure_one()
        if self.sale_order_id:
            return self.sale_order_id
        treatment_lines = self.line_ids.filtered(lambda l: l.procedure_id)
        order = self.env['sale.order'].create({
            'partner_id': self.patient_id.id,
            'company_id': self.company_id.id,
        })
        for line in treatment_lines:
            order_line = self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': line.procedure_id.id,
                'product_uom_qty': 1,
                'dental_treatment_line_id': line.id,
            })
            line.sale_order_line_id = order_line
        self.sale_order_id = order
        return order

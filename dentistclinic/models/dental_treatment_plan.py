from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DentalTreatmentPlan(models.Model):
    _name = 'dental.treatment.plan'
    _description = 'Diş Tedavi Planı'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'dental.whatsapp.mixin']
    _order = 'id desc'

    name = fields.Char(string='Plan Kodu', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code('dental.treatment.plan'))
    patient_id = fields.Many2one('res.partner', string='Hasta', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Para Birimi', required=True,
        default=lambda self: self.env.company.currency_id,
        domain=[('active', '=', True)])
    global_discount = fields.Float(string='Genel İndirim (%)', digits='Discount')
    amount_subtotal = fields.Monetary(
        string='Ara Toplam', compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_discount = fields.Monetary(
        string='Genel İndirim', compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_total = fields.Monetary(
        string='Toplam', compute='_compute_amounts', store=True, currency_field='currency_id')
    quote_valid_until = fields.Date(string='Teklif Geçerlilik Tarihi')
    dentition = fields.Selection([
        ('permanent', 'Daimi Dişler (Yetişkin)'),
        ('primary', 'Süt Dişleri (Çocuk)'),
        ('mixed', 'Karma Dişlenme'),
    ], string='Dişlenme', default='permanent', required=True,
        help='Diş haritasında gösterilecek dişler. Karma dişlenmede süt ve daimi dişler birlikte gösterilir.')
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

    @api.depends('line_ids.price_subtotal', 'global_discount')
    def _compute_amounts(self):
        for plan in self:
            subtotal = sum(plan.line_ids.mapped('price_subtotal'))
            discount = plan.currency_id.round(subtotal * (plan.global_discount or 0.0) / 100.0) if plan.currency_id else 0.0
            plan.amount_subtotal = subtotal
            plan.amount_discount = discount
            plan.amount_total = subtotal - discount

    @api.constrains('global_discount')
    def _check_global_discount(self):
        self._dental_check_discount_limit()

    def _dental_check_discount_limit(self):
        """Users may discount up to the company limit; managers have no limit."""
        if self.env.user.has_group('dentistclinic.group_dentistclinic_manager') or self.env.su:
            return
        for plan in self:
            limit = plan.company_id.dentistclinic_max_discount
            discounts = [plan.global_discount] + plan.line_ids.mapped('discount')
            if any((d or 0.0) > limit + 1e-6 for d in discounts):
                raise ValidationError(_(
                    'En fazla %%%(limit)s indirim yapabilirsiniz. Daha yüksek indirim için '
                    'klinik yöneticisinin onayı gerekir.', limit=f'{limit:g}'))

    def action_reprice(self):
        """Re-read the procedure prices in the plan currency (after a currency change)."""
        for plan in self:
            for line in plan.line_ids.filtered('procedure_id'):
                line.price_unit = line.procedure_id.product_tmpl_id._dental_price(plan.currency_id)[0]

    def write(self, vals):
        res = super().write(vals)
        if {'doctor_id', 'patient_id'} & set(vals):
            self.line_ids.filtered('planned_start')._sync_treatment_appointments()
        return res

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

    def _dental_pricelist(self):
        """A pricelist in the plan currency (created on first use)."""
        self.ensure_one()
        Pricelist = self.env['product.pricelist'].sudo()
        pricelist = Pricelist.search([
            ('currency_id', '=', self.currency_id.id),
            ('company_id', 'in', (self.company_id.id, False)),
        ], limit=1)
        return pricelist or Pricelist.create({
            'name': _('Diş Tedavileri (%s)', self.currency_id.name),
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
        })

    def action_create_sale_order(self):
        self.ensure_one()
        if self.sale_order_id:
            return self.sale_order_id
        treatment_lines = self.line_ids.filtered(lambda l: l.procedure_id)
        order = self.env['sale.order'].create({
            'partner_id': self.patient_id.id,
            'company_id': self.company_id.id,
            'pricelist_id': self._dental_pricelist().id,
            'validity_date': self.quote_valid_until,
        })
        for line in treatment_lines:
            # Line and plan discounts combined into one sale line discount.
            discount = 100.0 * (1 - (1 - (line.discount or 0.0) / 100.0) * (1 - (self.global_discount or 0.0) / 100.0))
            order_line = self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': line.procedure_id.id,
                'name': ('%s · %s' % (line.tooth_number, line.procedure_id.display_name))
                        if line.tooth_number else line.procedure_id.display_name,
                'product_uom_qty': 1,
                'price_unit': line.price_unit,
                'discount': discount,
                'dental_treatment_line_id': line.id,
            })
            line.sale_order_line_id = order_line
        self.sale_order_id = order
        return order

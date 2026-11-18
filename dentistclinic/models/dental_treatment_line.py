from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# FDI two-digit notation: quadrants 1-4 permanent (units 1-8), 5-8 primary (units 1-5).
PERMANENT_QUADRANTS = {1, 2, 3, 4}
PRIMARY_QUADRANTS = {5, 6, 7, 8}
OPEN_APPOINTMENT_STATES = ('draft', 'confirmed')


def fdi_dentition(tooth_number):
    """'permanent' / 'primary' for a valid FDI number, else False."""
    value = (tooth_number or '').strip()
    if len(value) != 2 or not value.isdigit():
        return False
    quadrant, unit = int(value[0]), int(value[1])
    if quadrant in PERMANENT_QUADRANTS and 1 <= unit <= 8:
        return 'permanent'
    if quadrant in PRIMARY_QUADRANTS and 1 <= unit <= 5:
        return 'primary'
    return False


class DentalTreatmentLine(models.Model):
    _name = 'dental.treatment.line'
    _description = 'Diş Tedavi Satırı'
    _order = 'planned_start, id'

    plan_id = fields.Many2one(
        'dental.treatment.plan', string='Tedavi Planı',
        required=True, ondelete='cascade')
    patient_id = fields.Many2one(
        related='plan_id.patient_id', string='Hasta', store=True)
    company_id = fields.Many2one(
        related='plan_id.company_id', string='Klinik/Şube', store=True)
    tooth_number = fields.Char(string='Diş No (FDI)')
    tooth_dentition = fields.Selection([
        ('permanent', 'Daimi'),
        ('primary', 'Süt Dişi'),
    ], string='Diş Tipi', compute='_compute_tooth_dentition', store=True)
    procedure_id = fields.Many2one(
        'product.product', string='Tedavi/Prosedür',
        domain=[('dental_is_procedure', '=', True)])
    doctor_id = fields.Many2one(
        'hr.employee', string='Hekim',
        domain=[('is_dentist', '=', True)])
    planned_start = fields.Datetime(
        string='Planlanan Tarih',
        help='Bu tedavinin seansı. Kaydedildiğinde hasta için randevu oluşturulur; '
             'aynı plan, aynı hekim ve aynı saatteki satırlar tek randevuda birleşir '
             've süreleri toplanır.')
    duration = fields.Float(string='Süre', default=0.5, help='Seans süresi (saat).')
    appointment_id = fields.Many2one(
        'dental.appointment', string='Randevu', readonly=True, copy=False)
    appointment_state = fields.Selection(related='appointment_id.state', string='Randevu Durumu')
    currency_id = fields.Many2one(related='plan_id.currency_id', string='Para Birimi')
    price_unit = fields.Monetary(string='Fiyat', currency_field='currency_id')
    discount = fields.Float(string='İndirim (%)', digits='Discount')
    price_subtotal = fields.Monetary(
        string='Tutar', currency_field='currency_id', compute='_compute_price_subtotal', store=True)
    state = fields.Selection([
        ('planned', 'Planlandı'),
        ('done', 'Uygulandı'),
        ('invoiced', 'Faturalandı'),
    ], string='Durum', default='planned', required=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Satış Satırı')
    notes = fields.Text(string='Notlar')
    lab_order_ids = fields.One2many(
        'dental.lab.order', 'treatment_line_id', string='Laboratuvar Talepleri')

    @api.depends('price_unit', 'discount')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

    @api.constrains('discount')
    def _check_discount(self):
        self.mapped('plan_id')._dental_check_discount_limit()

    @api.depends('tooth_number')
    def _compute_tooth_dentition(self):
        for line in self:
            line.tooth_dentition = fdi_dentition(line.tooth_number)

    @api.constrains('tooth_number')
    def _check_tooth_number(self):
        for line in self:
            if line.tooth_number and not fdi_dentition(line.tooth_number):
                raise ValidationError(_(
                    '"%s" geçerli bir FDI diş numarası değil. Daimi dişler 11-48 '
                    '(birler basamağı 1-8), süt dişleri 51-85 (birler basamağı 1-5).',
                    line.tooth_number))

    @api.constrains('procedure_id', 'tooth_number')
    def _check_procedure_tooth(self):
        for line in self:
            procedure = line.procedure_id.product_tmpl_id
            if not procedure or not line.tooth_dentition:
                continue
            if procedure.dental_dentition not in ('all', line.tooth_dentition):
                raise ValidationError(_(
                    '"%(procedure)s" %(kind)s için tanımlı; %(tooth)s numaralı diş %(tooth_kind)s.',
                    procedure=procedure.display_name,
                    kind=dict(procedure._fields['dental_dentition'].selection)[procedure.dental_dentition].lower(),
                    tooth=line.tooth_number,
                    tooth_kind=dict(self._fields['tooth_dentition'].selection)[line.tooth_dentition].lower()))

    @api.onchange('procedure_id')
    def _onchange_procedure_id(self):
        if not self.procedure_id:
            return
        if self.procedure_id.dental_duration:
            self.duration = self.procedure_id.dental_duration
        currency = self.plan_id.currency_id or self.env.company.currency_id
        self.price_unit = self.procedure_id.product_tmpl_id._dental_price(currency)[0]

    @api.onchange('planned_start', 'duration', 'doctor_id')
    def _onchange_planning_conflict(self):
        doctor = self.doctor_id or self.plan_id.doctor_id
        if not (self.planned_start and doctor):
            return None
        conflicts = self._conflicting_appointments(doctor, self.planned_start, self._stop(self.planned_start))
        if conflicts:
            return {'warning': {
                'title': _('Hekimin bu saatte randevusu var'),
                'message': _('%(doctor)s için çakışan randevu(lar):\n%(list)s',
                             doctor=doctor.name,
                             list='\n'.join('• %s' % appointment.display_name for appointment in conflicts[:5])),
            }}
        return None

    # ------------------------------------------------------------------
    # Appointment scheduling
    # ------------------------------------------------------------------

    def _stop(self, start):
        return start + timedelta(hours=self.duration or 0.5)

    def _conflicting_appointments(self, doctor, start, stop):
        domain = [
            ('doctor_id', '=', doctor.id),
            ('state', 'not in', ('cancelled', 'no_show')),
            ('start_datetime', '<', stop),
            ('stop_datetime', '>', start),
        ]
        own = self.appointment_id.id or (self._origin.appointment_id.id if self._origin else False)
        if own:
            domain.append(('id', '!=', own))
        return self.env['dental.appointment'].search(domain, order='start_datetime')

    def _session_key(self):
        doctor = self.doctor_id or self.plan_id.doctor_id
        return (self.plan_id.id, doctor.id, self.planned_start)

    def _session_description(self, lines):
        parts = []
        for line in lines:
            tooth = ''
            if line.tooth_number:
                kind = dict(line._fields['tooth_dentition'].selection).get(line.tooth_dentition, '')
                tooth = '%s (%s) ' % (line.tooth_number, kind.lower()) if kind else '%s ' % line.tooth_number
            parts.append('%s%s' % (tooth, line.procedure_id.display_name or _('Tedavi')))
        return _('Tedavi planı %(plan)s:\n%(lines)s', plan=lines[:1].plan_id.name,
                 lines='\n'.join('• %s' % part for part in parts))

    def _sync_treatment_appointments(self):
        """Create / move the appointment of each planned session of the plans of self.

        A session = same plan, same doctor, same start; its appointment lasts as
        long as all its lines together. Appointments that are done, cancelled or
        no-show are never moved, and lines without a planned date are left alone.
        """
        Appointment = self.env['dental.appointment']
        Line = self.env['dental.treatment.line']
        for plan in self.mapped('plan_id'):
            before = plan.line_ids.appointment_id
            sessions = {}
            for line in plan.line_ids.filtered('planned_start'):
                sessions[line._session_key()] = sessions.get(line._session_key(), Line) | line
            for (_plan_id, doctor_id, start), session in sessions.items():
                session = session.filtered(
                    lambda l: not l.appointment_id or l.appointment_id.state in OPEN_APPOINTMENT_STATES)
                if not session:
                    continue
                values = {
                    'patient_id': plan.patient_id.id,
                    'doctor_id': doctor_id or False,
                    'company_id': plan.company_id.id,
                    'start_datetime': start,
                    'stop_datetime': start + timedelta(hours=sum(line.duration or 0.5 for line in session)),
                    'appointment_type': 'treatment',
                    'treatment_plan_id': plan.id,
                    'notes': session._session_description(session),
                }
                appointment = session.appointment_id[:1]
                # Reuse it only if no line outside this session still points to it.
                if appointment and (appointment.treatment_line_ids - session):
                    appointment = Appointment
                if appointment:
                    changed = {
                        key: value for key, value in values.items()
                        if (appointment[key].id if appointment._fields[key].type == 'many2one' else appointment[key])
                        != value
                    }
                    if changed:
                        appointment.write(changed)
                else:
                    appointment = Appointment.create(values)
                session.filtered(lambda l: l.appointment_id != appointment).with_context(
                    dental_skip_appointment_sync=True).write({'appointment_id': appointment.id})
            # Sessions that were merged leave an empty draft behind: cancel it.
            (before - plan.line_ids.appointment_id).filtered(
                lambda a: a.state == 'draft' and a.treatment_plan_id == plan and not a.treatment_line_ids
            ).action_cancel()

    def _release_appointments(self):
        """The planned date was cleared: unlink the line, cancel an emptied draft."""
        for line in self.filtered('appointment_id'):
            appointment = line.appointment_id
            line.with_context(dental_skip_appointment_sync=True).appointment_id = False
            if appointment.state == 'draft' and not appointment.treatment_line_ids:
                appointment.action_cancel()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.filtered('planned_start')._sync_treatment_appointments()
        return lines

    def write(self, vals):
        cleared = self.filtered('planned_start') if 'planned_start' in vals and not vals['planned_start'] else self.browse()
        res = super().write(vals)
        if self.env.context.get('dental_skip_appointment_sync'):
            return res
        cleared._release_appointments()
        if {'planned_start', 'duration', 'doctor_id', 'procedure_id', 'tooth_number'} & set(vals):
            self.with_context(dental_skip_appointment_sync=True)._sync_treatment_appointments()
        return res

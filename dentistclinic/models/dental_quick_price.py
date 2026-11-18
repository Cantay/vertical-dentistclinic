from datetime import timedelta
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

QUOTE_CURRENCIES = ('TRY', 'EUR', 'GBP', 'USD')


class DentalQuickPrice(models.AbstractModel):
    """Server side of the "Hızlı Fiyat" (quick price) screen.

    The screen works like a till: pick teeth, tap procedures, see the total
    in the patient's currency, then turn the ticket into a treatment plan,
    book the first session in a free slot and share the quote.
    """
    _name = 'dental.quick.price'
    _description = 'Diş Kliniği Hızlı Fiyat'

    # ------------------------------------------------------------------
    # Catalogue
    # ------------------------------------------------------------------

    @api.model
    def get_setup(self):
        company = self.env.company
        currencies = self.env['res.currency'].search([('name', 'in', QUOTE_CURRENCIES), ('active', '=', True)])
        doctors = self.env['hr.employee'].search(
            [('is_dentist', '=', True), ('company_id', 'in', (company.id, False))], order='name')
        return {
            'company_currency': company.currency_id.name,
            'currencies': [{'id': c.id, 'name': c.name, 'symbol': c.symbol} for c in
                           sorted(currencies, key=lambda c: QUOTE_CURRENCIES.index(c.name))],
            'max_discount': 100.0 if self._is_manager() else company.dentistclinic_max_discount,
            'is_manager': self._is_manager(),
            'doctors': [{'id': d.id, 'name': ('%s %s' % (d.dental_title, d.name)) if d.dental_title else d.name}
                        for d in doctors],
            'whatsapp_number': company.phone or '',
        }

    @api.model
    def get_catalog(self, currency_id):
        currency = self.env['res.currency'].browse(currency_id).exists() or self.env.company.currency_id
        templates = self.env['product.template'].search(
            [('dental_is_procedure', '=', True), ('sale_ok', '=', True)], order='categ_id, name')
        categories = []
        seen = set()
        procedures = []
        for template in templates:
            category = template.categ_id
            if category.id not in seen:
                seen.add(category.id)
                categories.append({'id': category.id, 'name': category.name})
            price, converted = template._dental_price(currency)
            procedures.append({
                'id': template.product_variant_id.id,
                'name': template.name,
                'category_id': category.id,
                'dentition': template.dental_dentition,
                'per_tooth': template.dental_per_tooth,
                'duration': template.dental_duration,
                'price': price,
                'converted': converted,
            })
        return {'categories': categories, 'procedures': procedures,
                'currency': {'id': currency.id, 'name': currency.name, 'symbol': currency.symbol,
                             'decimals': currency.decimal_places}}

    # ------------------------------------------------------------------
    # Patients
    # ------------------------------------------------------------------

    @api.model
    def search_patients(self, query, limit=8):
        query = (query or '').strip()
        if len(query) < 2:
            return []
        digits = ''.join(ch for ch in query if ch.isdigit())
        domain = [('is_dental_patient', '=', True)]
        search = ['|', '|', ('name', 'ilike', query), ('email', 'ilike', query), ('ref', 'ilike', query)]
        if len(digits) >= 4:
            search = ['|', '|'] + search + [('phone', 'ilike', digits[-7:]), ('mobile', 'ilike', digits[-7:])]
        partners = self.env['res.partner'].search(domain + search, limit=limit)
        return [self._patient_card(p) for p in partners]

    @api.model
    def create_patient(self, name, phone):
        name = (name or '').strip()
        if not name:
            raise UserError(_('Hasta adı gerekli.'))
        partner = self.env['res.partner'].create({
            'name': name,
            'mobile': (phone or '').strip() or False,
            'is_dental_patient': True,
            'is_company': False,
        })
        return self._patient_card(partner)

    def _patient_card(self, partner):
        return {
            'id': partner.id,
            'name': partner.name,
            'phone': partner.mobile or partner.phone or '',
            'international': partner.is_international_patient,
            'plans': partner.treatment_plan_count,
        }

    @api.model
    def get_patient(self, partner_id):
        partner = self.env['res.partner'].browse(partner_id).exists()
        return self._patient_card(partner) if partner else False

    # ------------------------------------------------------------------
    # Ticket -> treatment plan
    # ------------------------------------------------------------------

    @api.model
    def create_plan(self, ticket):
        """ticket = {patient_id, currency_id, global_discount, doctor_id,
        lines: [{procedure_id, tooth_number, price_unit, discount, duration}]}"""
        lines = ticket.get('lines') or []
        if not ticket.get('patient_id'):
            raise UserError(_('Önce bir hasta seçin ya da yeni hasta ekleyin.'))
        if not lines:
            raise UserError(_('Teklifte en az bir tedavi olmalı.'))
        company = self.env.company
        plan = self.env['dental.treatment.plan'].create({
            'patient_id': ticket['patient_id'],
            'currency_id': ticket.get('currency_id') or company.currency_id.id,
            'global_discount': ticket.get('global_discount') or 0.0,
            'doctor_id': ticket.get('doctor_id') or False,
            'dentition': ticket.get('dentition') or 'permanent',
            'quote_valid_until': fields.Date.context_today(self) + timedelta(
                days=company.dentistclinic_quote_validity_days or 30),
            'line_ids': [(0, 0, {
                'procedure_id': line['procedure_id'],
                'tooth_number': line.get('tooth_number') or False,
                'price_unit': line.get('price_unit') or 0.0,
                'discount': line.get('discount') or 0.0,
                'duration': line.get('duration') or 0.5,
            }) for line in lines],
        })
        return self._plan_card(plan)

    def _plan_card(self, plan):
        return {
            'id': plan.id,
            'name': plan.name,
            'total': plan.amount_total,
            'currency': plan.currency_id.name,
            'valid_until': fields.Date.to_string(plan.quote_valid_until) if plan.quote_valid_until else False,
        }

    # ------------------------------------------------------------------
    # Booking
    # ------------------------------------------------------------------

    @api.model
    def get_slots(self, doctor_id, day, duration_hours):
        doctor = self.env['hr.employee'].browse(doctor_id).exists()
        if not doctor:
            return []
        minutes = max(int(round((duration_hours or 0.5) * 60)), 15)
        return doctor._dental_get_available_slots(fields.Date.to_date(day), minutes)

    @api.model
    def book_first_session(self, plan_id, doctor_id, start):
        """All lines of the quote become one session at `start` (UTC string)."""
        plan = self.env['dental.treatment.plan'].browse(plan_id).exists()
        doctor = self.env['hr.employee'].browse(doctor_id).exists()
        if not plan or not doctor:
            raise UserError(_('Plan ya da hekim bulunamadı.'))
        start_dt = fields.Datetime.to_datetime(start)
        stop_dt = start_dt + timedelta(hours=sum(plan.line_ids.mapped('duration')) or 0.5)
        if doctor._dental_slot_is_taken(start_dt, stop_dt):
            raise ValidationError(_('Bu saat az önce doldu, lütfen başka bir saat seçin.'))
        plan.write({'doctor_id': doctor.id})
        # One session: same start and doctor for every line (durations add up).
        plan.line_ids.write({'doctor_id': doctor.id, 'planned_start': start_dt})
        appointment = plan.line_ids.appointment_id[:1]
        return {
            'appointment_id': appointment.id,
            'appointment_name': appointment.display_name,
            'start_label': fields.Datetime.context_timestamp(self, start_dt).strftime('%d.%m.%Y %H:%M'),
            'doctor': doctor.name,
        }

    # ------------------------------------------------------------------
    # Sharing
    # ------------------------------------------------------------------

    @api.model
    def get_share(self, plan_id):
        plan = self.env['dental.treatment.plan'].browse(plan_id).exists()
        if not plan:
            raise UserError(_('Plan bulunamadı.'))
        currency = plan.currency_id

        def money(amount):
            return '%s %s' % (f'{amount:,.{currency.decimal_places}f}', currency.name)

        lines = []
        for line in plan.line_ids:
            label = line.procedure_id.display_name or ''
            if line.tooth_number:
                label = '%s (%s)' % (label, line.tooth_number)
            discount = ' (-%s%%)' % f'{line.discount:g}' if line.discount else ''
            lines.append('• %s: %s%s' % (label, money(line.price_subtotal), discount))
        text = '\n'.join(filter(None, [
            _('Merhaba %s,', plan.patient_id.name),
            _('%s için tedavi teklifiniz:', plan.company_id.name),
            '',
            *lines,
            '',
            _('Genel indirim: %s', money(plan.amount_discount)) if plan.amount_discount else '',
            _('Toplam: %s', money(plan.amount_total)),
            _('Geçerlilik: %s', plan.quote_valid_until.strftime('%d.%m.%Y')) if plan.quote_valid_until else '',
            _('Teklif no: %s', plan.name),
        ]))
        phone = ''.join(ch for ch in (plan.patient_id.mobile or plan.patient_id.phone or '') if ch.isdigit())
        if phone.startswith('00'):
            phone = phone[2:]
        elif phone.startswith('0'):
            phone = '90' + phone[1:]  # national Turkish number
        return {
            'text': text,
            'whatsapp_url': 'https://wa.me/%s?text=%s' % (phone, quote(text)) if phone
                            else 'https://wa.me/?text=%s' % quote(text),
            'has_phone': bool(phone),
            'report_url': '/report/pdf/dentistclinic.report_dental_quote/%s' % plan.id,
        }

    def _is_manager(self):
        return self.env.user.has_group('dentistclinic.group_dentistclinic_manager')

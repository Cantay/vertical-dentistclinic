import secrets
from datetime import datetime, timedelta

import pytz
from werkzeug.exceptions import NotFound

from odoo import fields, http
from odoo.http import request


class DentistClinicOnlineAppointment(http.Controller):

    @http.route(
        '/dentistclinic/appointment/submit', type='http', auth='public',
        methods=['POST'], website=True, csrf=True)
    def submit_online_appointment(self, **post):
        env = request.env(su=True)
        if not env.company.dentistclinic_online_appointment_enabled:
            return request.make_json_response(
                {'success': False, 'error': request.env._('Online booking is currently unavailable.')})

        name = (post.get('name') or '').strip()[:140]
        phone = (post.get('phone') or '').strip()[:32]
        email = (post.get('email') or '').strip()[:140]
        preferred_date = (post.get('preferred_date') or '').strip()[:10]
        appointment_type = (post.get('appointment_type') or 'examination').strip()
        notes = (post.get('notes') or '').strip()[:2000]

        if not name or not phone:
            return request.make_json_response(
                {'success': False, 'error': request.env._('Name and phone are required.')})

        if appointment_type not in ('examination', 'control', 'treatment', 'emergency'):
            appointment_type = 'examination'

        partner = self._get_or_create_patient(env, name, phone, email)

        start_datetime = env['dental.appointment']._parse_preferred_date(preferred_date)

        appointment_notes = notes
        if preferred_date and not start_datetime:
            appointment_notes = (
                'Hastanın talep ettiği tarih: %s\n%s' % (preferred_date, notes)
            ).strip()

        appointment = env['dental.appointment'].create({
            'patient_id': partner.id,
            'company_id': env.company.id,
            'start_datetime': start_datetime or env['dental.appointment']._default_fallback_datetime(),
            'appointment_type': appointment_type,
            'state': 'draft',
            'source': 'website',
            'notes': appointment_notes,
        })

        return request.make_json_response({
            'success': True,
            'message': request.env._('Your appointment request has been received. Our clinic team will call you shortly.'),
            'appointment_id': appointment.id,
        })

    def _get_or_create_patient(self, env, name, phone, email):
        partner = env['res.partner'].search([
            ('phone', '=', phone), ('is_dental_patient', '=', True),
        ], limit=1)
        if not partner:
            partner = env['res.partner'].create({
                'name': name,
                'phone': phone,
                'email': email or False,
                'is_dental_patient': True,
                'is_company': False,
            })
        return partner

    # --- Gelişmiş rezervasyon sihirbazı ---

    BOOKING_DAYS_AHEAD = 90

    def _booking_doctors(self, env, company):
        return env['hr.employee'].search([
            ('is_dentist', '=', True),
            ('dental_online_booking', '=', True),
            ('company_id', '=', company.id),
        ], order='name')

    def _booking_parse_day(self, value):
        try:
            day = datetime.strptime((value or '')[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
        today = fields.Date.today()
        if day < today or day > today + timedelta(days=self.BOOKING_DAYS_AHEAD):
            return None
        return day

    def _booking_doctor(self, env, company, doctor_id):
        try:
            doctor_id = int(doctor_id)
        except (TypeError, ValueError):
            return env['hr.employee']
        return self._booking_doctors(env, company).filtered(lambda d: d.id == doctor_id)

    @http.route('/dentistclinic/booking/doctors', type='http', auth='public',
                methods=['GET'], website=True, sitemap=False)
    def booking_doctors(self, **kwargs):
        env = request.env(su=True)
        company = request.website.company_id
        if not company.dentistclinic_online_appointment_enabled:
            return request.make_json_response({'success': False, 'error': request.env._('Online booking is currently unavailable.')})
        doctors = self._booking_doctors(env, company)
        return request.make_json_response({
            'success': True,
            'doctors': [{'id': d.id, 'name': d.name} for d in doctors],
            'days_ahead': self.BOOKING_DAYS_AHEAD,
        })

    @http.route('/dentistclinic/booking/slots', type='http', auth='public',
                methods=['GET'], website=True, sitemap=False)
    def booking_slots(self, doctor_id=None, date=None, **kwargs):
        env = request.env(su=True)
        company = request.website.company_id
        if not company.dentistclinic_online_appointment_enabled:
            return request.make_json_response({'success': False, 'error': request.env._('Online booking is currently unavailable.')})
        doctor = self._booking_doctor(env, company, doctor_id)
        day = self._booking_parse_day(date)
        if not doctor or not day:
            return request.make_json_response({'success': False, 'error': request.env._('Invalid dentist or date.')})
        slots = doctor._dental_get_available_slots(day, company.dentistclinic_slot_duration)
        return request.make_json_response({'success': True, 'slots': slots})

    @http.route('/dentistclinic/booking/submit', type='http', auth='public',
                methods=['POST'], website=True, csrf=True, sitemap=False)
    def booking_submit(self, **post):
        env = request.env(su=True)
        company = request.website.company_id
        if not company.dentistclinic_online_appointment_enabled:
            return request.make_json_response({'success': False, 'error': request.env._('Online booking is currently unavailable.')})

        name = (post.get('name') or '').strip()[:140]
        phone = (post.get('phone') or '').strip()[:32]
        email = (post.get('email') or '').strip()[:140]
        notes = (post.get('notes') or '').strip()[:2000]
        appointment_type = (post.get('appointment_type') or '').strip()
        slot_start = (post.get('slot_start') or '').strip()[:19]
        if not name or not phone:
            return request.make_json_response({'success': False, 'error': request.env._('Name and phone are required.')})
        if appointment_type not in ('examination', 'control', 'treatment', 'emergency'):
            return request.make_json_response({'success': False, 'error': request.env._('Invalid appointment type.')})

        doctor = self._booking_doctor(env, company, post.get('doctor_id'))
        try:
            start_utc = fields.Datetime.to_datetime(slot_start)
        except ValueError:
            start_utc = None
        if not doctor or not start_utc:
            return request.make_json_response({'success': False, 'error': request.env._('Invalid dentist or time.')})

        # Aynı hekim için eşzamanlı rezervasyonları sıraya sok; aksi halde iki
        # istek aynı boş slotu görüp ikisi de kayıt oluşturabilir.
        env.cr.execute('SELECT id FROM hr_employee WHERE id = %s FOR UPDATE', [doctor.id])
        tz = pytz.timezone(doctor._get_tz() or 'UTC')
        local_day = pytz.utc.localize(start_utc).astimezone(tz).date()
        day = self._booking_parse_day(local_day.isoformat())
        duration = company.dentistclinic_slot_duration
        available = {s['start'] for s in doctor._dental_get_available_slots(day, duration)} if day else set()
        if slot_start not in available:
            return request.make_json_response({
                'success': False,
                'error': request.env._('The time you selected is no longer available, please choose another time.'),
                'slot_taken': True,
            })

        partner = self._get_or_create_patient(env, name, phone, email)
        appointment = env['dental.appointment'].create({
            'patient_id': partner.id,
            'doctor_id': doctor.id,
            'company_id': company.id,
            'start_datetime': start_utc,
            'stop_datetime': start_utc + timedelta(minutes=duration),
            'appointment_type': appointment_type,
            'state': 'draft',
            'source': 'website',
            'notes': notes,
        })
        return request.make_json_response({
            'success': True,
            'message': request.env._('Your appointment request has been received. Our clinic team will contact you to confirm.'),
            'appointment_id': appointment.id,
        })

    def _get_consent_or_404(self, consent_id, token):
        env = request.env(su=True)
        consent = env['dental.consent'].browse(consent_id).exists()
        if not consent or not token or not consent.access_token or \
                not secrets.compare_digest(consent.access_token, token):
            raise NotFound()
        return consent

    @http.route(
        '/dentistclinic/consent/<int:consent_id>/<string:token>', type='http',
        auth='public', methods=['GET'], website=True, csrf=False)
    def view_consent(self, consent_id, token, **kwargs):
        consent = self._get_consent_or_404(consent_id, token)
        return request.render('dentistclinic.portal_consent_page', {
            'consent': consent,
        })

    @http.route(
        '/dentistclinic/consent/<int:consent_id>/<string:token>/sign', type='http',
        auth='public', methods=['POST'], website=True, csrf=True)
    def sign_consent(self, consent_id, token, **post):
        consent = self._get_consent_or_404(consent_id, token)
        signer_name = (post.get('signer_name') or '').strip()[:140]
        action = post.get('action')
        if action == 'decline':
            consent._portal_decline()
        elif signer_name:
            consent._portal_sign(signer_name, request.httprequest.remote_addr)
        return request.redirect('/dentistclinic/consent/%s/%s' % (consent_id, token))

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.osv.expression import OR as Domain_OR

from ..models.dental_event_request import TREATMENT_INTERESTS


class DentistClinicEventRequest(http.Controller):

    def _closed_response(self):
        return request.make_json_response({'success': False, 'error': request.env._('The request form is currently closed.')})

    @http.route('/dentistclinic/event-request/countries', type='http', auth='public',
                methods=['GET'], website=True, sitemap=False)
    def event_request_countries(self, **kwargs):
        if not request.website.company_id.dentistclinic_health_tourism_enabled:
            return self._closed_response()
        countries = request.env['res.country'].sudo().search([], order='name')
        return request.make_json_response({
            'success': True,
            'countries': [{'id': c.id, 'name': c.name} for c in countries],
        })

    def _open_events(self, company):
        Event = request.env['dental.event'].sudo()
        return Event.search(Event._website_domain(company), order='date_begin, id')

    @http.route('/dentistclinic/events/data', type='http', auth='public', methods=['GET'],
                website=True, sitemap=False)
    def events_data(self, **kwargs):
        company = request.website.company_id
        if not company.dentistclinic_health_tourism_enabled:
            return self._closed_response()
        return request.make_json_response({
            'success': True,
            'events': [event._website_card() for event in self._open_events(company)],
        })

    @http.route('/dentistclinic/events/image/<int:event_id>', type='http', auth='public',
                methods=['GET'], website=True, sitemap=False)
    def event_image(self, event_id, **kwargs):
        # Only events currently listed on the website expose their image.
        event = self._open_events(request.website.company_id).filtered(lambda e: e.id == event_id)
        if not event or not event.image:
            raise NotFound()
        stream = request.env['ir.binary']._get_image_stream_from(event, 'image')
        return stream.get_response(max_age=86400)

    @http.route('/dentistclinic/event-request/submit', type='http', auth='public',
                methods=['POST'], website=True, csrf=True, sitemap=False)
    def event_request_submit(self, **post):
        company = request.website.company_id
        if not company.dentistclinic_health_tourism_enabled:
            return self._closed_response()

        event = request.env['dental.event'].sudo()
        if post.get('event_id'):
            try:
                event = self._open_events(company).filtered(lambda e: e.id == int(post['event_id']))
            except ValueError:
                event = event.browse()
            if not event:
                return request.make_json_response({'success': False, 'error': request.env._('This event is no longer accepting applications.')})

        if event:
            message = request.env._('Your application for %s has been received. We will contact you to confirm your place.', event.name)
        else:
            message = request.env._('Your request has been received. We will let you know when a consultation day is planned in your area.')
        success = {'success': True, 'message': message}
        # Gizli tuzak alanı: insanlar görmez, botlar doldurur. Bota başarılı
        # görünür ama kayıt oluşturulmaz.
        if post.get('website_url'):
            return request.make_json_response(success)

        contact_name = (post.get('contact_name') or '').strip()[:140]
        phone = (post.get('phone') or '').strip()[:32]
        email = (post.get('email') or '').strip()[:140]
        city = (post.get('city') or '').strip()[:100]
        notes = (post.get('notes') or '').strip()[:2000]
        treatment_interest = post.get('treatment_interest') or False
        if treatment_interest not in dict(TREATMENT_INTERESTS):
            treatment_interest = False

        if not contact_name:
            return request.make_json_response({'success': False, 'error': request.env._('Full name is required.')})
        if not event and not city:
            return request.make_json_response({'success': False, 'error': request.env._('Full name and city are required.')})
        if not phone and not email:
            return request.make_json_response({'success': False, 'error': request.env._('Please enter at least a phone number or an email address.')})
        if not post.get('privacy_consent'):
            return request.make_json_response({'success': False, 'error': request.env._('To continue, please accept the privacy notice.')})
        if event:
            country, city = event.country_id, event.city
            # Aynı anda gelen başvurular kontenjanı aşmasın diye etkinlik satırı kilitlenir.
            request.env.cr.execute('SELECT id FROM dental_event WHERE id = %s FOR UPDATE', [event.id])
            event.invalidate_recordset(['seats_taken', 'seats_available', 'is_full'])
            if not event._registration_open():
                return request.make_json_response({'success': False, 'error': request.env._('Sorry, this event is fully booked.')})
            duplicate_domain = [('event_id', '=', event.id), ('state', '!=', 'closed')]
            contact_domain = []
            if email:
                contact_domain.append([('email', '=ilike', email)])
            if phone:
                contact_domain.append([('phone', '=', phone)])
            if request.env['dental.event.request'].sudo().search_count(
                    duplicate_domain + Domain_OR(contact_domain), limit=1):
                return request.make_json_response({'success': False, 'error': request.env._('You have already applied for this event. We will be in touch soon.')})
        else:
            try:
                country = request.env['res.country'].sudo().browse(int(post.get('country_id') or 0)).exists()
            except ValueError:
                country = None
            if not country:
                return request.make_json_response({'success': False, 'error': request.env._('Please select a country.')})

        request.env['dental.event.request']._create_from_website({
            'event_id': event.id or False,
            'agency_id': event.agency_id.id or False,
            'contact_name': contact_name,
            'phone': phone or False,
            'email': email or False,
            'country_id': country.id,
            'city': city,
            'treatment_interest': treatment_interest,
            'notes': notes,
            'lang': request.lang.code if request.lang else False,
            'company_id': company.id,
        })
        return request.make_json_response(success)

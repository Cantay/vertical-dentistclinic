from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


def _published_domain(company):
    return [
        ('dental_website_published', '=', True),
        ('company_id', '=', company.id),
    ]


def sitemap_team(env, rule, qs):
    if not qs or qs.lower() in '/our-team':
        yield {'loc': '/our-team'}
    company = env['website'].get_current_website().company_id
    for member in env['hr.employee'].sudo().search(_published_domain(company)):
        loc = member.dental_website_url
        if not qs or qs.lower() in loc:
            yield {'loc': loc}


class DentistClinicTeam(http.Controller):

    def _team_members(self):
        company = request.website.company_id
        return request.env['hr.employee'].sudo().search(
            _published_domain(company), order='dental_website_sequence, name')

    def _team_member_or_404(self, member_id):
        member = self._team_members().filtered(lambda m: m.id == member_id)
        if not member:
            raise NotFound()
        return member

    @http.route('/our-team', type='http', auth='public', website=True, sitemap=sitemap_team)
    def team_page(self, **kwargs):
        return request.render('dentistclinic.team_page', {'members': self._team_members()})

    @http.route('/our-team/<string:member_slug>', type='http', auth='public', website=True, sitemap=False)
    def team_profile(self, member_slug, **kwargs):
        _name, member_id = request.env['ir.http']._unslug(member_slug)
        if not member_id:
            raise NotFound()
        member = self._team_member_or_404(member_id)
        if request.httprequest.path != member.dental_website_url:
            return request.redirect(member.dental_website_url, code=301)
        return request.render('dentistclinic.team_profile_page', {
            'member': member,
            'education_lines': [line.strip() for line in (member.dental_education or '').splitlines() if line.strip()],
        })

    @http.route('/our-team/photo/<int:member_id>', type='http', auth='public', website=True, sitemap=False)
    def team_photo(self, member_id, **kwargs):
        member = self._team_member_or_404(member_id)
        # Website portrait is independent from the employee's backend avatar.
        field_name = 'dental_website_image' if member.dental_website_image else 'image_1024'
        stream = request.env['ir.binary']._get_image_stream_from(member, field_name)
        return stream.get_response(max_age=86400)

    @http.route('/dentistclinic/team/data', type='http', auth='public', methods=['GET'],
                website=True, sitemap=False)
    def team_data(self, lang=None, **kwargs):
        # The page passes its own language so cards match it even when the
        # request itself carries no language prefix / cookie.
        members = self._team_members()
        if lang and lang in request.website.language_ids.mapped('code'):
            members = members.with_context(lang=lang)
        return request.make_json_response({
            'success': True,
            'members': [member._dental_website_card() for member in members],
        })

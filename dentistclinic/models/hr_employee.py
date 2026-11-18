from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models

DENTAL_TEAM_ROLES = [
    ('dentist', 'Diş Hekimi'),
    ('assistant', 'Diş Hekimi Asistanı'),
    ('hygienist', 'Ağız ve Diş Sağlığı Teknikeri'),
    ('coordinator', 'Hasta Koordinatörü'),
    ('reception', 'Resepsiyon'),
    ('management', 'Yönetim'),
    ('other', 'Diğer'),
]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_dentist = fields.Boolean(string='Diş Hekimi')
    dental_online_booking = fields.Boolean(
        string='Online Randevuya Açık', default=True,
        help='İşaretliyse hekim, website rezervasyon formunda seçilebilir. '
             'Müsait saatler çalışanın Çalışma Saatleri takviminden hesaplanır.')

    # Klinik ekibi profili
    dental_team_role = fields.Selection(DENTAL_TEAM_ROLES, string='Ekip Rolü')
    dental_title = fields.Char(string='Ünvan', translate=True, help='Örn. Dt., Uzm. Dt., Dr. Dt., Prof. Dr.')
    dental_specialty = fields.Char(string='Uzmanlık Alanı', translate=True,
                                   help='Örn. Ortodonti, İmplantoloji, Pedodonti')
    dental_short_bio = fields.Text(string='Kısa Tanıtım', translate=True,
                                   help='Ekip listesinde kartın altında görünen 1-2 cümle.')
    dental_bio = fields.Html(string='Biyografi', translate=True, sanitize=True)
    dental_education = fields.Text(string='Eğitim', translate=True,
                                   help='Her satıra bir okul/derece yazın.')
    dental_career_start_year = fields.Integer(string='Mesleğe Başlangıç Yılı')
    dental_experience_years = fields.Integer(
        string='Deneyim (yıl)', compute='_compute_dental_experience_years')
    dental_languages = fields.Char(
        string='Konuştuğu Diller (eski metin)', translate=True,
        help='Eski serbest metin alanı; yerini "Konuştuğu Diller" seçimi aldı.')
    dental_language_ids = fields.Many2many(
        'res.lang', 'hr_employee_dental_lang_rel', 'employee_id', 'lang_id',
        string='Konuştuğu Diller', context={'active_test': False},
        help='Web sitesinde bayrak ve dil adıyla gösterilir. Sitede kurulu olmayan diller de seçilebilir.')
    dental_website_image = fields.Image(
        string='Web Sitesi Portresi', max_width=1024, max_height=1024,
        help='Ekip kartları için yüz ve omuz kadrajında ayrı fotoğraf. Boş bırakılırsa personel fotoğrafı kullanılır.')
    dental_instagram_url = fields.Char(string='Instagram')
    dental_linkedin_url = fields.Char(string='LinkedIn')

    # Website yayını
    dental_website_published = fields.Boolean(
        string='Web Sitesinde Göster', copy=False,
        help='İşaretliyse kişi web sitesindeki Ekibimiz bölümünde ve profil sayfasında yayınlanır.')
    dental_website_name = fields.Char(
        string='Sitede Görünen Ad', translate=True,
        help='Web sitesinde gösterilecek ad; her dil için ayrı yazılabilir (ör. Latin / Kiril yazımı). '
             'Boş bırakılırsa çalışanın adı kullanılır.')
    dental_public_name = fields.Char(
        string='Sitedeki Ad', compute='_compute_dental_public_name')
    dental_website_sequence = fields.Integer(string='Sıralama', default=10)
    dental_website_separator_after = fields.Boolean(
        string='Bu kişiden sonra ayırıcı göster',
        help='Web sitesinde bu kişinin ardından ekip gruplarını ayıran çizgi gösterir.')
    dental_website_separator_heading = fields.Boolean(
        string='Ayraçta başlık göster',
        help='İşaretliyse ayraçta, sonraki grubu tanıtan başlık ve açıklama da gösterilir.')
    dental_website_separator_title = fields.Char(
        string='Ayraç Başlığı', translate=True, help='Örn. Klinik Ekibimiz')
    dental_website_separator_text = fields.Text(
        string='Ayraç Açıklaması', translate=True,
        help='Başlığın altında görünen 1-2 cümle (isteğe bağlı).')
    dental_website_show_contact = fields.Boolean(
        string='İletişim Bilgilerini Sitede Göster',
        help='İş e-postası ve iş telefonu profil sayfasında gösterilir. '
             'Kişisel/mobil numara hiçbir zaman sitede gösterilmez.')
    dental_website_url = fields.Char(string='Profil Sayfası', compute='_compute_dental_website_url')
    dental_website_subtitle = fields.Char(compute='_compute_dental_website_subtitle')

    @api.depends('dental_specialty', 'dental_team_role')
    def _compute_dental_website_subtitle(self):
        role_labels = dict(DENTAL_TEAM_ROLES)
        for employee in self:
            employee.dental_website_subtitle = (
                employee.dental_specialty or role_labels.get(employee.dental_team_role, ''))

    @api.depends('dental_career_start_year')
    def _compute_dental_experience_years(self):
        current_year = fields.Date.today().year
        for employee in self:
            start = employee.dental_career_start_year
            employee.dental_experience_years = max(current_year - start, 0) if start else 0

    def _compute_dental_website_url(self):
        for employee in self:
            employee.dental_website_url = (
                '/our-team/%s' % self.env['ir.http']._slug(employee) if employee.id else False)

    @api.onchange('dental_team_role')
    def _onchange_dental_team_role(self):
        if self.dental_team_role == 'dentist':
            self.is_dentist = True

    def action_dental_open_website_profile(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.dental_website_url, 'target': 'new'}

    def _dental_website_languages(self):
        """[{code, name, flag_url}] — dil adı kendi dilinde (Türkçe, English, Deutsch…)."""
        self.ensure_one()
        return [{
            'code': lang.code,
            'name': lang._dental_native_name(),
            'flag_url': lang._dental_flag_url(),
        } for lang in self.dental_language_ids.sorted(lambda l: (l.code != 'tr_TR', l.name))]

    def _dental_separator_heading(self):
        """(başlık, açıklama) — yalnızca ayraç ve başlık seçeneği açıksa dolu."""
        self.ensure_one()
        if not (self.dental_website_separator_after and self.dental_website_separator_heading):
            return '', ''
        return self.dental_website_separator_title or '', self.dental_website_separator_text or ''

    @api.depends('name', 'dental_website_name')
    @api.depends_context('lang')
    def _compute_dental_public_name(self):
        for employee in self:
            employee.dental_public_name = employee.dental_website_name or employee.name

    def _dental_website_card(self):
        """Website'e açılan (yayınlanmış) ekip üyesinin güvenli alan seti."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'title': self.dental_title or '',
            'team_role': self.dental_team_role or '',
            'separator_after': self.dental_website_separator_after,
            'separator_title': self._dental_separator_heading()[0],
            'separator_text': self._dental_separator_heading()[1],
            'is_dentist': self.is_dentist,
            'subtitle': self.dental_website_subtitle or '',
            'short_bio': self.dental_short_bio or '',
            'experience_years': self.dental_experience_years,
            'languages': self._dental_website_languages(),
            'image_url': '/our-team/photo/%s?v=%s' % (
                self.id, self.write_date.strftime('%Y%m%d%H%M%S')),
            'profile_url': self.dental_website_url,
        }

    def _dental_slot_is_taken(self, start, stop):
        """True when the doctor has an active appointment overlapping [start, stop) (UTC)."""
        self.ensure_one()
        return bool(self.env['dental.appointment'].sudo().search_count([
            ('doctor_id', '=', self.id),
            ('state', 'not in', ('cancelled', 'no_show')),
            ('start_datetime', '<', stop),
            ('stop_datetime', '>', start),
        ]))

    def _dental_get_available_slots(self, day, duration_minutes):
        """Verilen gün için boş randevu başlangıçlarını döndürür.

        Çalışma aralıkları resource.calendar'dan gelir (öğle arası, resmi
        tatil ve izinler düşülmüş olarak); iptal edilmemiş randevularla
        çakışan ve geçmişte kalan slotlar elenir. Dönen 'start' değeri UTC
        (naive) olup sunucuya aynen geri gönderilir; 'label' hekimin saat
        diliminde gösterim içindir.
        """
        self.ensure_one()
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        if not calendar or duration_minutes <= 0:
            return []

        tz = pytz.timezone(self._get_tz() or 'UTC')
        day_start = tz.localize(datetime.combine(day, time.min))
        day_end = day_start + timedelta(days=1)
        work_intervals = calendar._work_intervals_batch(
            day_start, day_end, resources=self.resource_id, tz=tz,
        )[self.resource_id.id]

        day_start_utc = day_start.astimezone(pytz.utc).replace(tzinfo=None)
        day_end_utc = day_end.astimezone(pytz.utc).replace(tzinfo=None)
        duration = timedelta(minutes=duration_minutes)
        appointments = self.env['dental.appointment'].sudo().search([
            ('doctor_id', '=', self.id),
            ('state', '!=', 'cancelled'),
            ('start_datetime', '<', day_end_utc),
            ('start_datetime', '>=', day_start_utc - timedelta(days=1)),
        ])
        busy = [
            (appt.start_datetime, appt.stop_datetime or appt.start_datetime + duration)
            for appt in appointments
        ]

        now_utc = fields.Datetime.now()
        slots = []
        for interval_start, interval_stop, _records in work_intervals:
            slot_start = interval_start
            while slot_start + duration <= interval_stop:
                start_utc = slot_start.astimezone(pytz.utc).replace(tzinfo=None)
                stop_utc = start_utc + duration
                is_busy = any(b_start < stop_utc and b_stop > start_utc for b_start, b_stop in busy)
                if start_utc > now_utc and not is_busy:
                    slots.append({
                        'start': fields.Datetime.to_string(start_utc),
                        'label': slot_start.strftime('%H:%M'),
                    })
                slot_start += duration
        return slots

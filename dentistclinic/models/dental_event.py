from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime


class DentalEvent(models.Model):
    """Yurtdışı danışma günü / Dental Event.

    Odoo Etkinlik modülü yerine bilinçli olarak sade tutuldu: tarih, yer, hekimler,
    kontenjan ve başvurular. Başvurular dental.event.request kayıtlarıdır.
    """
    _name = 'dental.event'
    _description = 'Dental Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_begin desc, id desc'

    name = fields.Char(string='Etkinlik Adı', required=True, translate=True, tracking=True,
                       help='Web sitesinde görünür. Örn. "Consultation Day in London"')
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('open', 'Başvuruya Açık'),
        ('closed', 'Başvuru Kapandı'),
        ('done', 'Tamamlandı'),
        ('cancelled', 'İptal'),
    ], string='Durum', default='draft', required=True, tracking=True,
        help='Web sitesinde yalnızca "Başvuruya Açık" ve henüz başlamamış etkinlikler listelenir.')
    date_begin = fields.Datetime(string='Başlangıç', required=True, tracking=True)
    date_end = fields.Datetime(string='Bitiş', required=True, tracking=True)
    date_tz = fields.Selection(
        _tz_get, string='Saat Dilimi', required=True,
        default=lambda self: self.env.user.tz or 'Europe/Istanbul',
        help='Sitede tarih ve saat bu saat diliminde gösterilir (etkinliğin yapıldığı yer).')
    country_id = fields.Many2one('res.country', string='Ülke', required=True, tracking=True)
    city = fields.Char(string='Şehir', required=True, tracking=True)
    venue = fields.Char(string='Mekan', translate=True, help='Örn. otel veya salon adı.')
    address = fields.Char(string='Adres')
    description = fields.Text(string='Açıklama', translate=True,
                              help='Sitedeki etkinlik kartında görünen kısa metin.')
    doctor_ids = fields.Many2many(
        'hr.employee', string='Katılacak Hekimler', domain=[('is_dentist', '=', True)])
    seats_max = fields.Integer(string='Kontenjan', help='0 = sınırsız.')
    seats_taken = fields.Integer(string='Başvuru', compute='_compute_seats')
    seats_available = fields.Integer(string='Boş Yer', compute='_compute_seats')
    is_full = fields.Boolean(string='Dolu', compute='_compute_seats')
    request_ids = fields.One2many('dental.event.request', 'event_id', string='Başvurular')
    agency_id = fields.Many2one(
        'res.partner', string='İş Birliği Yapılan Acente',
        domain=[('is_health_tourism_agency', '=', True)],
        help='Etkinliği birlikte düzenlediğiniz acente. Başvurulara otomatik aktarılır.')
    company_id = fields.Many2one(
        'res.company', string='Klinik/Şube', required=True,
        default=lambda self: self.env.company)
    color = fields.Integer(string='Renk')

    @api.depends('seats_max', 'request_ids.state')
    def _compute_seats(self):
        counts = {
            event.id: count
            for event, count in self.env['dental.event.request']._read_group(
                [('event_id', 'in', self.ids), ('state', '!=', 'closed')],
                ['event_id'], ['__count'])
        }
        for event in self:
            event.seats_taken = counts.get(event.id, 0)
            event.seats_available = max(event.seats_max - event.seats_taken, 0) if event.seats_max else 0
            event.is_full = bool(event.seats_max) and event.seats_taken >= event.seats_max

    @api.constrains('date_begin', 'date_end')
    def _check_dates(self):
        for event in self:
            if event.date_end < event.date_begin:
                raise ValidationError(self.env._('Bitiş tarihi başlangıçtan önce olamaz.'))

    @api.constrains('seats_max')
    def _check_seats_max(self):
        if any(event.seats_max < 0 for event in self):
            raise ValidationError(self.env._('Kontenjan negatif olamaz.'))

    def action_open(self):
        self.write({'state': 'open'})

    def action_close_registration(self):
        self.write({'state': 'closed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_requests(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dentistclinic.action_dental_event_request')
        action.update({
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id, 'search_default_open': 0},
        })
        return action

    @api.model
    def _website_domain(self, company):
        return [
            ('state', '=', 'open'),
            ('company_id', '=', company.id),
            ('date_begin', '>', fields.Datetime.now()),
        ]

    def _registration_open(self):
        self.ensure_one()
        return self.state == 'open' and self.date_begin > fields.Datetime.now() and not self.is_full

    def _website_date_label(self):
        """Etkinliğin kendi saat diliminde, ziyaretçinin dilinde tarih/saat."""
        self.ensure_one()

        def fmt(value, pattern):
            return format_datetime(self.env, value, tz=self.date_tz, dt_format=pattern)

        start = fmt(self.date_begin, 'd MMMM y, HH:mm')
        if fmt(self.date_begin, 'y-MM-dd') == fmt(self.date_end, 'y-MM-dd'):
            return '%s – %s' % (start, fmt(self.date_end, 'HH:mm'))
        return '%s – %s' % (start, fmt(self.date_end, 'd MMMM y, HH:mm'))

    def _website_card(self):
        """Website'e açılan güvenli alan seti."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'country': self.country_id.name,
            'venue': self.venue or '',
            'address': self.address or '',
            'date_label': self._website_date_label(),
            'description': self.description or '',
            'doctors': [
                ('%s %s' % (doctor.dental_title, doctor.name)) if doctor.dental_title else doctor.name
                for doctor in self.doctor_ids
            ],
            'seats_available': self.seats_available if self.seats_max else None,
            'is_full': self.is_full,
        }

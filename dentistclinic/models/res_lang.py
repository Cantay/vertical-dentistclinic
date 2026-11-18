from odoo import models

# Language codes without a usable country part ("ar_001", "es_419"…).
FLAG_OVERRIDES = {
    'ar_001': 'sa',
    'es_419': 'mx',
    'sr@latin': 'rs',
}


class ResLang(models.Model):
    _inherit = 'res.lang'

    def _dental_native_name(self):
        """Autonym for the website: "Turkish / Türkçe" -> "Türkçe", "English (UK)" -> "English"."""
        self.ensure_one()
        name = self.name.split(' / ')[-1].split(' (')[0].strip()
        return name[:1].upper() + name[1:]

    def _dental_flag_url(self):
        self.ensure_one()
        if self.flag_image:
            return self.flag_image_url
        country = FLAG_OVERRIDES.get(self.code)
        if country:
            return '/base/static/img/country_flags/%s.png' % country
        return self.flag_image_url

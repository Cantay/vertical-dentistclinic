from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    dental_is_procedure = fields.Boolean(
        string='Diş Tedavisi', help='Tedavi planı satırlarında seçilebilir.')
    dental_dentition = fields.Selection([
        ('all', 'Tüm Dişler'),
        ('permanent', 'Daimi Dişler'),
        ('primary', 'Süt Dişleri'),
    ], string='Uygulanan Dişler', default='all',
        help='Tedavi satırında seçilen dişe göre işlem listesi bu alana göre süzülür.')
    dental_per_tooth = fields.Boolean(
        string='Diş Bazında', help='İşlem tek bir dişe uygulanır (diş numarası girilmelidir).')
    # Fixed tourist prices; list_price is the company-currency (TRY) price.
    dental_price_eur = fields.Float(string='Fiyat (EUR)', digits='Product Price')
    dental_price_gbp = fields.Float(string='Fiyat (GBP)', digits='Product Price')
    dental_price_usd = fields.Float(string='Fiyat (USD)', digits='Product Price')
    dental_duration = fields.Float(
        string='Varsayılan Süre', default=0.5,
        help='Tedavi satırında planlanan randevunun varsayılan süresi (saat).')

    def _dental_price(self, currency, date=None):
        """(price, converted) in `currency`: the fixed price of that currency when
        set, else the company-currency price converted at the current rate."""
        self.ensure_one()
        company = self.env.company
        fixed = {'EUR': self.dental_price_eur, 'GBP': self.dental_price_gbp, 'USD': self.dental_price_usd}
        if currency == company.currency_id:
            return self.list_price, False
        if fixed.get(currency.name):
            return fixed[currency.name], False
        price = company.currency_id._convert(
            self.list_price, currency, company, date or fields.Date.context_today(self))
        return price, bool(self.list_price)

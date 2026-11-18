# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Diş Kliniği Yönetimi',
    'version': '18.0.4.11.0',
    'category': 'Industries',
    'summary': 'Diş kliniği hasta, randevu, tedavi planı, laboratuvar, onam, sağlık turizmi ve WhatsApp yönetimi',
    'description': """Diş klinikleri için uçtan uca yönetim modülü.

Temel Operasyon:
- Hasta kartı (uluslararası hasta alanları dahil), randevu, diş haritası (odontogram)
- Tedavi planı/satırları, sarf malzeme ve stok takibi
- Çok şubeli klinikler için Odoo'nun yerleşik şirket (branch) yapısını kullanır

Hasta Deneyimi ve Otomasyon:
- Website üzerinden online randevu talep formu
- Dijital onam formu (token tabanlı güvenli hasta onayı)
- Laboratuvar (kuron, protez vb.) talebi takibi
- Randevu/kontrol hatırlatmaları: e-posta, SMS, WhatsApp
- Şube bazlı karşılaştırmalı dashboard

Sağlık Turizmi:
- Yurtdışı hasta için özel CRM pipeline (lead'den tamamlanmaya kadar)
- Acente/komisyon takibi, acente portal erişimi
- Seyahat/konaklama bilgisi takibi

Mevcut satış, fatura ve e-fatura akışlarına dokunmadan bunların üzerine
ince bir dikey katman olarak çalışır. Tüm özellikler Ayarlar ekranından
açılıp kapatılabilir.""",
    'author': 'Odoo Custom',
    'depends': [
        'base',
        'mail',
        'calendar',
        'hr',
        'sale',
        'stock',
        'sms',
        'website',
        'mail_gateway',
        'mail_gateway_whatsapp',
        'crm',
        'portal',
    ],
    'data': [
        'security/dentistclinic_security.xml',
        'security/ir.model.access.csv',
        'data/dentistclinic_data.xml',
        'data/dentistclinic_mail_template.xml',
        'data/dentistclinic_cron.xml',
        'data/crm_stage_data.xml',
        'data/dental_procedure_data.xml',
        'data/dental_currency_data.xml',
        'report/dental_quote_report.xml',
        'views/res_partner_views.xml',
        'views/hr_employee_views.xml',
        'views/dental_team_views.xml',
        'views/website_team_templates.xml',
        'views/dental_appointment_views.xml',
        'views/dental_treatment_plan_views.xml',
        'views/product_views.xml',
        'views/dental_case_views.xml',
        'views/dental_consent_views.xml',
        'views/dental_lab_order_views.xml',
        'views/dental_travel_info_views.xml',
        'views/dental_commission_views.xml',
        'views/dental_event_views.xml',
        'views/dental_event_request_views.xml',
        'views/crm_lead_views.xml',
        'views/portal_consent_templates.xml',
        'views/dentistclinic_dashboard_action.xml',
        'wizard/res_config_settings_views.xml',
        'views/menus.xml',
        'views/snippets/dentistclinic_snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'dentistclinic/static/src/scss/dentistclinic_snippets.scss',
            'dentistclinic/static/src/js/dentistclinic_appointment_form.js',
            'dentistclinic/static/src/js/dentistclinic_booking_wizard.js',
            'dentistclinic/static/src/js/dentistclinic_team.js',
            'dentistclinic/static/src/js/dentistclinic_events.js',
            'dentistclinic/static/src/js/dentistclinic_event_request.js',
        ],
        'web.assets_backend': [
            'dentistclinic/static/src/dashboard/dentistclinic_dashboard.scss',
            'dentistclinic/static/src/dashboard/dentistclinic_dashboard.js',
            'dentistclinic/static/src/dashboard/dentistclinic_dashboard.xml',
            'dentistclinic/static/src/odontogram/odontogram_field.scss',
            'dentistclinic/static/src/odontogram/odontogram_field.js',
            'dentistclinic/static/src/odontogram/odontogram_field.xml',
            'dentistclinic/static/src/quick_price/quick_price.scss',
            'dentistclinic/static/src/quick_price/quick_price.js',
            'dentistclinic/static/src/quick_price/quick_price.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}

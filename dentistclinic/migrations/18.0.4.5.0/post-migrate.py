"""Move the free-text spoken languages (dental_languages) to dental_language_ids.

Each comma-separated entry in any stored translation is matched against a
table of Turkish / English language names; unknown entries are logged and
left in the old text field.
"""
import logging

_logger = logging.getLogger(__name__)

NAME_TO_CODE = {
    'türkçe': 'tr_TR', 'turkish': 'tr_TR',
    'ingilizce': 'en_GB', 'english': 'en_GB',
    'almanca': 'de_DE', 'german': 'de_DE', 'deutsch': 'de_DE',
    'rusça': 'ru_RU', 'russian': 'ru_RU',
    'arapça': 'ar_001', 'arabic': 'ar_001',
    'fransızca': 'fr_FR', 'french': 'fr_FR',
    'felemenkçe': 'nl_NL', 'hollandaca': 'nl_NL', 'dutch': 'nl_NL',
    'italyanca': 'it_IT', 'italian': 'it_IT',
    'ispanyolca': 'es_ES', 'i̇spanyolca': 'es_ES', 'spanish': 'es_ES',
    'farsça': 'fa_IR', 'persian': 'fa_IR',
    'azerice': 'az_AZ', 'azerbaijani': 'az_AZ',
    'ukraynaca': 'uk_UA', 'ukrainian': 'uk_UA',
    'lehçe': 'pl_PL', 'polish': 'pl_PL',
    'romence': 'ro_RO', 'romanian': 'ro_RO',
    'bulgarca': 'bg_BG', 'bulgarian': 'bg_BG',
    'yunanca': 'el_GR', 'greek': 'el_GR',
    'isveççe': 'sv_SE', 'swedish': 'sv_SE',
}


def _norm(text):
    return text.strip().replace('I', 'ı').replace('İ', 'i').lower()


def migrate(cr, version):
    cr.execute("""
        SELECT data_type FROM information_schema.columns
         WHERE table_name = 'hr_employee' AND column_name = 'dental_languages'
    """)
    row = cr.fetchone()
    if not row:
        return
    if row[0] == 'jsonb':
        cr.execute("SELECT id, dental_languages FROM hr_employee WHERE dental_languages IS NOT NULL")
        rows = [(emp_id, ', '.join(v for v in (values or {}).values() if v)) for emp_id, values in cr.fetchall()]
    else:
        cr.execute("SELECT id, dental_languages FROM hr_employee WHERE dental_languages IS NOT NULL")
        rows = cr.fetchall()

    cr.execute("SELECT code, id FROM res_lang")
    lang_ids = dict(cr.fetchall())
    for emp_id, text in rows:
        codes, unknown = [], []
        for part in (text or '').split(','):
            if not part.strip():
                continue
            code = NAME_TO_CODE.get(_norm(part))
            if code and code in lang_ids:
                if code not in codes:
                    codes.append(code)
            else:
                unknown.append(part.strip())
        for code in codes:
            cr.execute("""
                INSERT INTO hr_employee_dental_lang_rel (employee_id, lang_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
            """, [emp_id, lang_ids[code]])
        if unknown:
            _logger.warning("Employee %s: spoken languages not recognised, kept in the old text field: %s",
                            emp_id, ', '.join(unknown))

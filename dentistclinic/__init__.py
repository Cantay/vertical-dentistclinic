from . import models
from . import controllers
from . import wizard


def post_init_hook(env):
    """Modül kurulduktan/güncellendikten sonra, res.company alanlarının
    varsayılan/mevcut değerlerine göre özellik gruplarını senkronize eder.

    write()/create() override'ı sadece gerçek bir ORM write çağrısında
    tetiklenir; bu alanlar migration'da doğrudan ALTER TABLE ile
    oluşturulduğundan (varsayılan değerleriyle) override hiç çalışmamış
    olur. Bu hook, kurulum sonrası durumu zorla tutarlı hale getirir.
    """
    companies = env['res.company'].search([])
    companies._sync_feature_groups(companies._FEATURE_GROUP_XMLIDS.keys())

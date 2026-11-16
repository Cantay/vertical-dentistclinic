# Dentsoft → Odoo "Diş Kliniği" Dikey Modülü — Analiz ve Planlama

Tarih: 2026-11-12
Durum: Taslak / planlama aşaması — henüz kod yok

## 1. Amaç

`website_dentistclinic` / `dentistclinic` adıyla geliştirilecek dikey modülün,
Türkiye pazarında diş kliniklerinin kullandığı DentSoft (dentsoft.com.tr)
yazılımının temel yeteneklerini Odoo 18 Community üzerinde karşılamasını
sağlamak. Hedef; var olan bir SaaS'ı birebir klonlamak değil, DentSoft'un
sunduğu iş akışlarını Odoo'nun mevcut güçlü modülleri (stock, account, hr,
sms, mail, website, calendar) üzerine **ince bir dikey katman** olarak inşa
etmek.

Kurulum notu: Bu ortamda Odoo Enterprise kaldırılmış durumda
(`oca/server-brand/remove_odoo_enterprise`), yani `appointment`, `sign`,
`helpdesk` gibi Enterprise-only modüller **mevcut değil**. Planlama bunu
hesaba katarak Community modülleri + özel geliştirme üzerinden ilerliyor.

## 2. DentSoft Özellik Envanteri (kaynak: dentsoft.com.tr)

| Kategori | DentSoft Özelliği |
|---|---|
| Hasta Yönetimi | Hasta kartı, tedavi geçmişi, ödeme geçmişi, hasta notları, eski yazılımdan veri aktarımı |
| Randevu | Randevu modülü, online randevu (web widget + WordPress eklentisi), randevu/tedavi/kontrol hatırlatmaları |
| Klinik/Tedavi | Tedavi planlama, Vaka (Case) modülü, Hekim (Physician) modülü, Laboratuvar modülü, Dijital Onam + Dijital Arşiv |
| Finans | Finans modülü, entegre muhasebe/faturalandırma, e-Fatura/e-Arşiv/e-SMM, Sanal POS, Online Tahsilat, İYS otomasyonu |
| Stok | Stok modülü, malzeme/ekipman takibi, otomatik sipariş tetikleme, maliyet kontrolü |
| İK/Personel | İK modülü, mesai giriş/çıkış (mobil), görev/iş yükü dengeleme, Akademi (eğitim videoları) modülü |
| Raporlama | Rapor modülü, Dashboard modülü, personel performansı/hasta yoğunluğu/finansal analiz, hasta memnuniyeti anketi |
| Çok Şube | Şubeli klinik desteği — tek merkezden yönetim |
| İletişim | Sanal santral entegrasyonu, SMS (26 başlık), WhatsApp/SMS/E-posta bildirimleri, canlı destek |
| Entegrasyon | ÜTS, MBYS-USS (sağlık turizmi), E-Reçete, CRM entegrasyonu, Recall (tedavi sonrası takip), E-Nabız, zaman damgası (KamuSM/OpenSSL) |
| Bulut/Güvenlik | Private cloud, otomatik yedekleme, KVKK/ISO 27001/ISO 15504 uyumu, kullanıcı güvenlik takibi |
| Mobil | iOS/Android "DentSoft İşletme" uygulaması — randevu, stok, mesai takibi |
| Paketleme | 3 kademeli paket: Economic / Standard / Management (€6 / €12 / €18 kişi-ay) |

## 3. Odoo Native Karşılık Haritası

| DentSoft Modülü | Odoo Karşılığı (Community) | Durum |
|---|---|---|
| Hasta Modülü | `res.partner` (hasta = kişi partner, kategori/tag "Hasta") + yeni alanlar (TC no, doğum tarihi, alerji, anamnez) | Genişletme gerekli |
| Randevu Modülü | `calendar.event` tabanlı özel "Diş Hekimliği Randevusu" modeli (Enterprise `appointment` yok → sıfırdan hafif bir randevu modeli + takvim görünümü) | Yeni geliştirme |
| Online Randevu Widget | `website_form` + özel controller (public randevu formu) | Yeni geliştirme |
| Vaka/Tedavi Planı | Yeni model: `dental.treatment.plan` + `dental.treatment.line`, `sale.order` ile ilişkili (tedavi = sipariş satırı) | Yeni geliştirme |
| Diş Haritası (Odontogram) | Yok — DentSoft'ta da haritada doğrudan görünmüyor ama sektör standardı; UI widget (SVG/js) olarak eklenecek | Yeni geliştirme (opsiyonel, faz 2) |
| Hekim Modülü | `hr.employee` + `res.users` (hekim = çalışan), iş yükü raporu = `hr`/`calendar` üzerinden pivot | Genişletme |
| Laboratuvar Modülü | `purchase.order` / `project.task` ile dış lab taleplerinin takibi | Genişletme / hafif yeni model |
| Dijital Onam | `sign` Enterprise'da yok → PDF şablon + e-posta/SMS onay linki ile basit "onam kaydı" modeli | Yeni geliştirme (sign olmadan) |
| Finans/Faturalama | `account` (e-Fatura/e-Arşiv için mevcut TR yerelleştirme — `l10n_tr` + GİB entegrasyon modülleri kontrol edilmeli) | Mevcut, entegrasyon kontrolü |
| Sanal POS / Online Tahsilat | `payment` modülleri (iyzico, Sipay vb. provider) | Mevcut altyapı, provider seçimi |
| Stok Modülü | `stock` (malzeme/sarf takibi), `stock.warehouse` klinik bazlı | Mevcut, konfigürasyon |
| İK Modülü | `hr`, `hr_attendance` (mesai giriş/çıkış) | Mevcut |
| Akademi Modülü | `website_slides` (eLearning) | Mevcut, opsiyonel |
| Rapor/Dashboard | Odoo native pivot/graph view + `spreadsheet_dashboard` (Enterprise'da) yoksa custom dashboard view | Kısmen mevcut, custom gerekebilir |
| Çok Şube | `res.company` şube hiyerarşisi (`parent_id`/`child_ids` — native "Branches") + multi-company record rule'lar | Mevcut, konfigürasyon (ek model gerekmiyor) |
| SMS/WhatsApp Bildirim | `sms` modülü mevcut; WhatsApp için `whatsapp` Enterprise yok → üçüncü parti API entegrasyonu (NetGSM, vb.) | Mevcut (SMS) + yeni entegrasyon (WhatsApp) |
| Recall (tedavi sonrası takip) | `calendar`/`sms` üzerine otomasyon kuralı (cron + mail/sms template) | Yeni geliştirme (otomasyon) |
| CRM Entegrasyonu | `crm` modülü mevcut — hasta adayı/lead takibi için kullanılabilir | Mevcut |
| ÜTS/MBYS/E-Nabız/E-Reçete | Sağlık Bakanlığı sistemleri — resmi entegrasyon gerektirir, kapsam dışı/faz 3 | Araştırma gerekli, büyük efor |

## 4. Önerilen Modül Mimarisi

```
vertical-dentistclinic/
├── dentistclinic/                 # Çekirdek modül (bağımlılık: base, mail, calendar, hr, account, stock)
│   ├── models/
│   │   ├── res_partner.py         # Hasta alanları (TC no, doğum tarihi, anamnez, alerji, sigorta)
│   │   ├── dental_appointment.py  # Randevu modeli (calendar.event mixin)
│   │   ├── dental_treatment.py    # Tedavi planı / satırları
│   │   ├── dental_case.py         # Vaka takibi
│   │   ├── dental_consent.py      # Dijital onam kaydı
│   │   └── dental_recall.py       # Tedavi sonrası takip otomasyonu
│   ├── wizard/
│   ├── report/                    # Tedavi planı / fatura PDF şablonları
│   ├── security/
│   └── views/
├── website_dentistclinic/         # Public online randevu formu (website_form bağımlılığı)
├── dentistclinic_odontogram/      # (Faz 2, opsiyonel) Diş haritası widget'ı
└── dentistclinic_whatsapp/        # (Faz 2) WhatsApp/SMS üçüncü parti entegrasyon köprüsü
```

## 5. Fazlandırma Önerisi

**Faz 1 — Temel Klinik Operasyonu (MVP)**
- Hasta kartı genişletmesi (anamnez, alerji, TC no, sigorta bilgisi)
- Randevu modeli + takvim görünümü + SMS/e-posta hatırlatma (cron)
- Tedavi planı/vaka takibi, sale.order ile ilişki
- Temel stok/malzeme tüketimi (stock entegrasyonu)
- Basit finans: tedavi → fatura akışı (account entegrasyonu)

**Faz 2 — Hasta Deneyimi ve Otomasyon**
- Website üzerinden online randevu formu
- Recall otomasyonu (kontrol hatırlatma cron+şablon)
- Dijital onam formu (PDF + e-posta/SMS onay linki)
- Laboratuvar talebi takibi (purchase/project tabanlı)
- Dashboard/raporlama (pivot + graph view seti)

**Faz 3 — İleri Entegrasyonlar (opsiyonel, yüksek efor)**
- Diş haritası (odontogram) widget'ı
- WhatsApp Business API entegrasyonu
- Sağlık Bakanlığı sistemleri (ÜTS, MBYS-USS, E-Nabız, E-Reçete) — resmi API/izin süreci gerektirir, ayrı fizibilite çalışması önerilir
- Çok şube konsolide raporlama

## 6. Alınan Kararlar (2026-11-12)

1. **Diş haritası (odontogram)**: MVP'ye dahil edilmeyecek, Faz 3'e bırakıldı. MVP'de tedavi satırlarında serbest/seçmeli "diş numarası" alanı yeterli.
2. **Çok şube**: MVP'den itibaren veri modeline dahil edilecek — Odoo'nun yerleşik `res.company` şube hiyerarşisi (`parent_id`/`child_ids`, native olarak "Branches" adını taşır) kullanılacak. Ayrı bir `dental.clinic` modeli **açılmayacak**; tüm ana modellerde klinik/şube ayrımı standart `company_id` alanı (multi-company) ile yapılacak. Bu sayede Odoo'nun hazır multi-company record rule'ları, kullanıcı-şirket erişim kısıtları ve şirket bazlı raporlama otomatik olarak devreye girer.
3. **E-Fatura/Ödeme entegrasyonu**: Kullanıcının zaten çalışan bir e-fatura entegrasyonu mevcut — bu nedenle MVP kapsamında finans/e-fatura/sanal POS tarafı **ele alınmayacak**, mevcut entegrasyonla uyumlu çalışacak şekilde sadece `account.move` ile standart ilişki kurulacak. Sağlayıcı seçimi konusu kapatıldı.

## 7. Faz 1 (MVP) Veri Modeli Detayı

Çok şube kararı doğrultusunda, aşağıdaki modellerin tamamında klinik/şube
ayrımı **standart `company_id` alanı** (`res.company`, `Many2one`) ile
yapılır. Bir kliniğin fiziksel şubeleri, Odoo'nun yerleşik şirket
hiyerarşisinde `parent_id` ile ana şirkete bağlı alt şirket (şube) olarak
tanımlanır — ayrı bir `dental.clinic` modeline gerek yoktur. `company_id`
alanı her modelde Odoo'nun standart multi-company mekanizmasıyla (varsayılan
değer, record rule, kullanıcı izinli şirketler) otomatik yönetilir.

### 7.1 `res.partner` (hasta) — genişletme
- `is_dental_patient` (Boolean, ilgili kategori otomatik atanır)
- `identification_no` (Char, TC Kimlik No, zorunlu değil ama format validasyonu)
- `birth_date` (Date)
- `blood_type` (Selection)
- `allergies` (Text)
- `anamnesis` (Text) — genel sağlık geçmişi notu
- `referral_source` (Selection/Many2one) — nereden geldi (CRM lead bağlantısı için)
- `company_id` (Many2one `res.company`) — hastanın kayıtlı olduğu klinik/şube (standart multi-company alanı)
- `treatment_plan_ids` (One2many → `dental.treatment.plan`)
- `appointment_ids` (One2many → `dental.appointment`)

### 7.2 `dental.appointment` (yeni, `calendar.event` ile ilişkili/mixin)
- `patient_id` (Many2one `res.partner`, zorunlu)
- `doctor_id` (Many2one `hr.employee`, domain: diş hekimi rolü)
- `company_id` (Many2one `res.company`, zorunlu, standart multi-company alanı)
- `calendar_event_id` (Many2one `calendar.event`) — gerçek takvim kaydı
- `appointment_type` (Selection: muayene/kontrol/tedavi/acil)
- `state` (Selection: taslak/onaylı/geldi/gelmedi/iptal)
- `reminder_sent` (Boolean) — SMS/e-posta hatırlatma cron'u için
- `treatment_plan_id` (Many2one `dental.treatment.plan`, opsiyonel)

### 7.3 `dental.treatment.plan` (yeni)
- `patient_id`, `company_id`, `doctor_id`
- `name` / `sequence` (plan kodu)
- `state` (Selection: taslak/onaylandı/devam ediyor/tamamlandı/iptal)
- `line_ids` (One2many → `dental.treatment.line`)
- `sale_order_id` (Many2one `sale.order`) — ücretlendirme/fatura akışı için
- `notes`

### 7.4 `dental.treatment.line` (yeni)
- `plan_id` (Many2one `dental.treatment.plan`)
- `tooth_number` (Char/Selection, FDI notasyonu — serbest alan, Faz 3'teki görsel haritaya hazırlık)
- `procedure_id` (Many2one `product.product`, hizmet/prosedür kataloğu)
- `state` (Selection: planlandı/uygulandı/fatura edildi)
- `doctor_id`
- `appointment_id` (Many2one `dental.appointment`, hangi randevuda yapıldığı)
- `sale_order_line_id` (Many2one `sale.order.line`)
- `consumed_product_ids` (One2many veya `stock.move` ilişkisi — sarf malzeme tüketimi)

### 7.5 `dental.case` (Vaka — opsiyonel Faz 1 sonu / Faz 1.5)
- `patient_id`, `company_id`, `doctor_id`
- `treatment_plan_id`
- `description`, `state`
- DentSoft'taki "vaka sunumu" ihtiyacı başlangıçta `treatment.plan` üzerinden karşılanabilir; ayrı model olarak açılması gerekip gerekmediği Faz 1 sonunda değerlendirilecek.

### 7.6 Stok/malzeme entegrasyonu
- Yeni model açılmaz; her klinik/şube (`res.company`) kendi `stock.warehouse`'una sahip olur (Odoo'da şirket başına otomatik ana depo zaten oluşturulur), sarf malzeme tüketimi `dental.treatment.line` üzerinden tetiklenen `stock.move` kayıtlarıyla yapılır.

### 7.7 Finans entegrasyonu (sınırlı kapsam)
- `dental.treatment.plan.sale_order_id` → mevcut `sale.order`/`account.move` akışına bağlanır.
- Mevcut e-fatura entegrasyonuna dokunulmaz; sadece standart Odoo satış→fatura akışı kullanılır.

### 7.8 Bildirim/Hatırlatma
- Cron (`ir.cron`) + `mail.template`/`sms.template`: randevudan N saat önce hatırlatma, tedavi sonrası recall.
- Faz 1'de sadece SMS (mevcut `sms` modülü) ve e-posta; WhatsApp Faz 3'e bırakıldı.

## 8. Güncellenmiş Fazlandırma

**Faz 1 — Temel Klinik Operasyonu (MVP, çok şube destekli)**
- Hasta kartı genişletmesi + standart `company_id` (şube) alanı
- `dental.appointment` + takvim görünümü + SMS/e-posta hatırlatma cron'u
- `dental.treatment.plan` / `dental.treatment.line`, sale.order ilişkisi
- Stok/malzeme tüketimi (mevcut `stock` modülü, şirket/şube bazlı warehouse)
- Satış→fatura akışı (mevcut e-fatura entegrasyonuna dokunmadan)
- Şube (multi-company) bazlı temel raporlar (pivot/graph)

**Faz 2 — Hasta Deneyimi ve Otomasyon**
- Website üzerinden online randevu formu
- Recall otomasyonu (kontrol hatırlatma cron+şablon)
- Dijital onam formu (PDF + e-posta/SMS onay linki)
- Laboratuvar talebi takibi (purchase/project tabanlı)
- Dashboard/raporlama (pivot + graph view seti, şube karşılaştırmalı)

**Faz 3 — İleri Entegrasyonlar**
- [x] Diş haritası (odontogram) widget'ı — `dental_odontogram` field widget, `dental.treatment.plan` formunda
- [x] Çok şube konsolide raporlama — dashboard'a şube filtresi + karşılaştırma tablosu
- [x] WhatsApp Business API entegrasyonu — `oca/social/mail_gateway_whatsapp` üzerinden, `dental.whatsapp.mixin`
- [x] Sağlık Bakanlığı sistemleri (ÜTS, MBYS, E-Nabız, E-Reçete) — fizibilite araştırması tamamlandı (bkz. §10), **kod geliştirmesi yapılmadı**

## 10. Sağlık Bakanlığı Sistemleri — Fizibilite Araştırması (2026-11-12)

Faz 3'ün son kalemi için dört resmi sistem araştırıldı. Sonuç: **hiçbiri MVP/Faz 1-2 işleyişini engellemiyor**, hepsi "varsa iyi olur" seviyesinde ek entegrasyon; her biri ayrı bir resmi başvuru/yetkilendirme süreci gerektiriyor ve bu süreçler Odoo geliştirmesinden bağımsız, klinik/işletme düzeyinde yürütülmesi gereken idari işler.

### 10.1 ÜTS (Ürün Takip Sistemi)
- **Ne işe yarar**: TİTCK'nin tıbbi cihaz (implant, kuron materyali vb.) takip sistemi. Üretici/ithalatçı/bayi zaten ÜTS'ye kayıtlı cihazları satıyor; klinik tarafında asıl yükümlülük hastaya takılan cihazın **lot/seri numarasının hasta kaydına işlenmesi ve gerektiğinde geri çağırma (recall) durumunda izlenebilmesi**.
- **Entegrasyon şekli**: TİTCK, üretim/ithalat/kullanım/dağıtım bildirimleri için bir web servis (ÜTS entegrasyon API'si) sunuyor; bu genellikle cihaz üreticisi/distribütörü tarafından kullanılıyor, klinik tarafında zorunlu API entegrasyonu değil — klinik sadece ÜTS portalından karekod okutarak "kullanım bildirimi" yapabiliyor (manuel, portal üzerinden).
- **Odoo'daki karşılığı**: `dental.treatment.line`'a eklenecek bir `device_lot` / `uts_barcode` alanı + lab/implant kaydı — bu basit bir alan eklemesi, ÜTS'ye otomatik bildirim göndermek **opsiyonel ve ekstra efor** (TİTCK'den ayrı bir entegratör yetkisi/API anahtarı gerekir).
- **Öncelik değerlendirmesi**: Düşük-orta. Sadece implant/kemik grefti gibi tıbbi cihaz kullanan klinikler için anlamlı; her diş kliniği için zorunlu değil.

### 10.2 MBYS (Sağlık Bilgi Yönetim Sistemleri Yönetmeliği kapsamı)
- **Ne işe yarar**: 2022'de yürürlüğe giren "Sağlık Bilgi Yönetim Sistemleri Hakkında Yönetmelik" kapsamında, serbest hekimler/özel sağlık kuruluşları hasta muayene/tedavi bilgilerini Sağlık Bakanlığı'nın merkezi sistemine (MBYS/USS) bildirmekle yükümlü.
- **Entegrasyon şekli**: Sağlık Bilgi Sistemleri Genel Müdürlüğü (SBSGM), "SBYS" (Sağlık Bilgi Yönetim Sistemi) yazılımı sağlayıcılarının bir **kayıt/sertifikasyon sürecinden** geçmesini istiyor — yazılımın SBSGM'ye resmi başvuru yapıp onaylanması, ardından gerçek zamanlı veri gönderimi için webservis entegrasyonu gerekiyor.
- **Odoo'daki karşılığı**: Bu bir **yazılım sertifikasyonu** süreci, basit bir API çağrısı değil. DentSoft'un "MBYS-USS" entegrasyonu övünmesi, onların bu sertifikasyonu zaten tamamlamış olmasından geliyor.
- **Öncelik değerlendirmesi**: Yüksek efor, resmi süreç. Kliniğin yasal yükümlülüğü varsa (büyük ihtimalle var — yönetmelik tüm özel sağlık kuruluşlarını kapsıyor), bu süreç Odoo'dan bağımsız olarak **işletme/klinik sahibi tarafından SBSGM ile doğrudan** başlatılmalı; Odoo tarafı ancak sertifikasyon sonrası bir webservis entegratörü yazılabilir.

### 10.3 E-Nabız
- **Ne işe yarar**: Hastaların kendi sağlık kayıtlarını görebildiği merkezi platform; sağlık kuruluşları hasta muayene/tetkik/reçete verilerini buraya aktarır.
- **Entegrasyon şekli**: E-Nabız veri gönderimi aslında MBYS/SBYS sertifikasyonunun bir parçası — ayrı bir API değil, SBYS onaylı bir sistem otomatik olarak E-Nabız'a veri besler. Yani §10.2'deki sertifikasyon tamamlanırsa E-Nabız entegrasyonu da büyük ölçüde beraberinde gelir.
- **Öncelik değerlendirmesi**: §10.2 ile birleşik, ayrı bir iş kalemi değil.

### 10.4 E-Reçete (MEDULA)
- **Ne işe yarar**: Hekimin elektronik reçete yazıp SGK'nın MEDULA sistemine kaydetmesi, hastanın eczaneden ilacı bu reçeteyle alması.
- **Entegrasyon şekli**: SGK, "Medula Eczane Reçete ve Rapor Web Servisleri" adıyla resmi bir webservis sunuyor; diş hekimleri "beyaz reçete" yazma yetkisine sahip ve bu webservis üzerinden MEDULA'ya kayıt yapılabiliyor. Bağlanabilmek için SGK ile sağlık tesisi düzeyinde **webservis kullanıcı yetkilendirmesi** gerekiyor.
- **Odoo'daki karşılığı**: Teknik olarak en somut ve ulaşılabilir olan — SGK webservis dokümantasyonu üzerinden `dental.treatment.plan`/randevu akışına bir "E-Reçete Oluştur" entegrasyonu eklenebilir, ama bunun için önce klinik/hekim bazında SGK yetkilendirmesi (kullanıcı adı/şifre veya sertifika) gerekiyor.
- **Öncelik değerlendirmesi**: Orta efor, ama diş kliniğinde reçete yazma ihtiyacı (antibiyotik, ağrı kesici vb.) sınırlı sayıda senaryoda oluyor — yüksek kullanım sıklığı olmayan bir özellik için orta-yüksek efor yatırımı gerekiyor.

### 10.5 Sonuç ve Öneri
1. Bu dört sistemden **hiçbiri** klinik günlük operasyonunu (Faz 1-2'de kurulanları) engellemiyor; hepsi ek/tamamlayıcı.
2. **MBYS/E-Nabız sertifikasyonu** yasal yükümlülük olabileceğinden önceliklidir, ama bu Odoo geliştirmesi değil — klinik sahibinin SBSGM ile doğrudan yürüteceği bir idari süreç. Sertifikasyon tamamlandığında Odoo tarafı için ayrı bir teknik entegrasyon projesi (yeni faz) açılması önerilir.
3. **ÜTS** sadece implant vb. tıbbi cihaz kullanan klinikler için anlamlı; `dental.treatment.line`'a basit bir `device_lot` alanı eklemek (ÜTS'ye otomatik bildirim olmadan, sadece iç kayıt amaçlı) düşük efor + yüksek fayda sağlar, istenirse ayrı bir mini görev olarak hemen yapılabilir.
4. **E-Reçete**, SGK yetkilendirmesi sağlandıktan sonra teknik olarak en ulaşılabilir entegrasyon, ama kullanım sıklığı düşük olduğu için ROI'si diğer fazlara göre düşük.
5. **Genel öneri**: Bu dört kalem şimdilik **kapsam dışı/beklemede** tutulsun; klinik sahibi SBSGM/SGK sertifikasyon süreçlerini başlatırsa, o aşamada ayrı bir "Faz 4 — Resmi Sistem Entegrasyonları" olarak ele alınsın.

## 11. Faz 4 — Yurtdışı Hasta (Sağlık Turizmi) Süreci (planlama, 2026-11-12)

### 11.1 Sektör bağlamı
Türkiye'de dental turizm büyük hacimli bir iş kolu (2024'te ~500.000 uluslararası
hasta, ~800M USD gelir). Yurtdışı hasta kabul eden kliniklerin **USTYB
(Uluslararası Sağlık Turizmi Yetki Belgesi)** sahibi olması yasal zorunluluk;
hastaları yönlendiren turizm acenteleri için de **TÜRSAB** belgesi gerekiyor.
Bu belgelendirme süreçleri Odoo'dan bağımsız, klinik/işletme düzeyinde
yürütülen idari işler — modül tarafında varsayım, kliniğin bu yetkiye zaten
sahip olduğudur.

Tipik yurtdışı hasta yolculuğu 4 aşamadan oluşur:
1. **Uzaktan ön değerlendirme**: Hasta (veya onu yönlendiren acente) fotoğraf/
   röntgen gönderir, klinik uzaktan ön teklif ve tedavi planı taslağı hazırlar.
2. **Seyahat ve geliş**: Uçuş, konaklama, transfer koordinasyonu; hasta
   Türkiye'ye gelir.
3. **Klinik uygulama**: Yerel hastayla aynı tedavi planı/randevu akışı
   (Faz 1-3'te kurulan sistem) işler.
4. **Tedavi sonrası uzaktan takip**: Hasta ülkesine döner, iyileşme takibi ve
   kontrol hatırlatmaları farklı saat dilimi/dil üzerinden yürütülür.

### 11.2 Mevcut altyapı ile ilişki
Faz 1'de eklenen `res.partner` alanları (`is_international_patient`,
`nationality_id`, `passport_no`, `lang`, `country_id`) bu sürecin temelini
zaten atmış durumda. Faz 4, bunun üzerine 3 yeni parça ekliyor:

### 11.3 Yeni model: `dental.treatment.plan` öncesi "Ön Teklif" aşaması
- **Sorun**: Şu an `dental.treatment.plan` doğrudan somut bir tedavi planı;
  yurtdışı hastada ise hasta henüz Türkiye'ye gelmeden, sadece fotoğraf/röntgen
  üzerinden **bağlayıcı olmayan bir ön teklif** hazırlanıyor.
- **Çözüm**: `dental.treatment.plan.state`'e yeni bir ilk durum eklenmesi
  yeterli olabilir (`'quote'` — "Ön Teklif", `confirmed`'den önce) — ayrı bir
  model açmaya gerek yok, mevcut `state` seçimine bir adım eklenir.
  - `is_remote_quote` (Boolean) — hasta henüz klinikte değilken hazırlanan
    planları işaretlemek için.
  - Hasta tarafından gönderilen fotoğraf/rönteken `ir.attachment` üzerinden
    plana eklenir (ekstra model gerekmiyor, Odoo'nun native attachment
    sistemi kullanılır).

### 11.4 Yeni model: `dental.travel.info` (Seyahat/Konaklama Bilgisi)
- `patient_id`, `treatment_plan_id` (opsiyonel bağlantı)
- `arrival_date`, `departure_date` (Datetime)
- `flight_number_arrival`, `flight_number_departure` (Char)
- `hotel_name`, `hotel_address` (Char/Text)
- `needs_transfer` (Boolean), `transfer_notes` (Text)
- `needs_translator` (Boolean), `translator_language` (Many2one `res.lang`
  veya Selection)
- Bu bilgiler klinik tarafından mı yoksa acente tarafından mı sağlanıyor
  olursa olsun tek bir yerde görünür olur; randevu planlamasında hastanın
  Türkiye'de kaldığı tarih aralığı dikkate alınarak randevular bu pencereye
  sığdırılabilir (ileri aşamada, randevu formunda uyarı/doğrulama olarak).

### 11.5 Acente / Yönlendiren Kurum, CRM Pipeline ve Komisyon Takibi

**CRM Pipeline (sağlık turizmine özel aşamalar)**: Mevcut `crm.lead` modülü
üzerinde, sağlık turizmi hastaları için ayrı bir satış takımı/pipeline
(`crm.team` + özel `crm.stage` seti) tanımlanır:

1. **Lead** — Acente/hasta ilk iletişime geçti (website formu, acente,
   sosyal medya).
2. **Ön Değerlendirme** — Hasta fotoğraf/röntgen gönderdi, hekim inceliyor.
3. **Teklif Gönderildi** — Ön teklif (bkz. §11.3, `dental.treatment.plan`
   `state='quote'`) hastaya/acenteye iletildi.
4. **Onaylandı** — Hasta teklifi kabul etti, tedavi planı `confirmed`
   durumuna geçti.
5. **Seyahat Planlandı** — `dental.travel.info` kaydı oluşturuldu, uçuş/otel
   bilgisi girildi.
6. **Klinikte** — Hasta Türkiye'ye geldi, tedavi planı `in_progress`.
7. **Tamamlandı** — Tedavi planı `done`; lead otomatik "Won" (kazanıldı)
   olarak kapanır.
8. **Kaybedildi** — Herhangi bir aşamada hasta vazgeçti/başka klinik seçti.

Bu aşamalar `crm.lead`'in standart `stage_id` alanı üzerinden Kanban
görünümünde takip edilir; `dental.treatment.plan.state` değişimleri
(onaylandı/klinikte/tamamlandı) ilgili lead'in aşamasını otomatik günceller
(lead ↔ treatment plan arasında `Many2one`/`One2many` bağlantısı ile).

**Acente modeli**: Acente/yönlendiren kurum bir `res.partner` (şirket,
`is_company=True`, kategori "Sağlık Turizmi Acentesi"). `crm.lead.source_id`
veya özel bir `agency_id` (Many2one `res.partner`) ile lead'e bağlanır.

**Komisyon takibi**:
- `res.partner`'da (hasta) `referring_agency_id` (Many2one `res.partner`,
  domain: acente kategorisi).
- `dental.treatment.plan`'da `commission_rate` (Float, %) — acente bazında
  varsayılan oran `res.partner.commission_rate` üzerinden önerilir, plan
  bazında override edilebilir.
- **Komisyon tetik kararı**: Komisyon tutarı **fatura kesildiğinde**
  (`account.move` durumu `posted` olduğunda) gerçek fatura tutarı üzerinden
  hesaplanır — teklif/plan onayı anında değil. Bu, iptal/indirim gibi
  değişikliklerin zaten faturaya yansımış olmasını garanti eder, komisyon
  her zaman gerçek tahsilat tutarına dayanır.
  - `dental.commission` (yeni, hafif model): `agency_id`, `treatment_plan_id`,
    `invoice_id` (Many2one `account.move`), `amount` (Monetary, hesaplanan),
    `state` (`'pending'` → `'invoiced'` → `'paid'`).
  - `account.move`'un `button_post` (faturayı onayla) akışına bir `_compute`/
    otomasyon kancası eklenir: fatura onaylandığında, ilişkili tedavi
    planının acentesi varsa `dental.commission` kaydı otomatik oluşturulur.
  - Acenteye ödeme, bu `dental.commission` kaydından tetiklenen bir
    `account.move` (gider faturası/ödeme) ile yapılır — standart muhasebe
    akışı, yeni bir finans modeli gerekmez.
- `referral_source` seçimine `'agency'` (Sağlık Turizmi Acentesi) eklenir.

### 11.9 Acente Portal Erişimi (Hibrit)

İki tamamlayıcı erişim yöntemi birlikte kurulur:

1. **Kalıcı portal hesabı** (ana yöntem, sürekli takip için): Acente için
   gerçek bir Odoo portal kullanıcısı (`res.users`, `base.group_portal`)
   açılır. Acente giriş yapıp:
   - Kendi yönlendirdiği hastaların lead/tedavi aşamasını (§11.5'teki pipeline)
   - Kendi komisyon durumunu (`dental.commission` kayıtları — bekliyor/
     faturalandı/ödendi)
   görebilir. Erişim, standart Odoo `ir.rule` ile `agency_id = env.user.partner_id`
   filtresiyle kısıtlanır — acente sadece kendi hastalarını görür, başka
   acentenin verisine erişemez.
2. **Token tabanlı tekil paylaşım** (hızlı/geçici paylaşım için, onam formu
   ile aynı desen — `dentistclinic.dental_consent`'teki `secrets.token_urlsafe`
   yaklaşımı tekrar kullanılır): Henüz portal hesabı açılmamış bir acenteye
   veya hastanın kendisine, belirli bir teklifin/tedavi planının özetini
   gösteren tek seferlik bir link gönderilebilir. Bu, kalıcı hesap açmanın
   gerekli olmadığı tek seferlik paylaşımlar için (örn. ilk teklif onayı)
   kullanılır; sürekli takip ihtiyacı doğduğunda acenteye kalıcı portal
   hesabı açılması önerilir.

### 11.6 Tedavi Sonrası Uzaktan Takip (Recall'un yurtdışı hasta için uyarlanması)
- Mevcut `_cron_send_recall_reminders` (Faz 2) zaten `patient_id.lang`'a göre
  e-posta/SMS/WhatsApp şablonu render edebilir durumda (Odoo'nun `mail.template`
  dil render mekanizması `lang` alanını otomatik kullanır) — **ekstra kod
  gerekmez**, sadece her dil için ayrı şablon çevirisi (`mail.template`
  içinde "Çeviriler" sekmesi) girilmesi yeterli.
- Yurtdışı hasta için saat dilimi: `res.partner.tz` alanı (native Odoo alanı)
  zaten mevcut — cron gönderim saatini hastanın saat dilimine göre
  ayarlamak istenirse `tz` baz alınarak hatırlatma saati hesaplanabilir
  (basit bir iyileştirme, mevcut cron'a opsiyonel eklenebilir).
- WhatsApp kanalı (Faz 3'te kurulan) yurtdışı hasta için SMS'ten daha
  güvenilir bir kanal — SMS uluslararası numaralarda maliyetli/sorunlu
  olabilir, WhatsApp bu riski taşımaz.

### 11.7 Önerilen Modül Yapısı
İki yeni hafif model açılıyor (`dental.travel.info`, `dental.commission`),
geri kalanı mevcut `dental.treatment.plan`, `res.partner`, `crm.lead`,
`account.move` üzerine ince eklemeler:

```
dentistclinic/
├── models/
│   ├── dental_treatment_plan.py   # +state='quote', is_remote_quote, crm_lead_id
│   ├── res_partner.py             # +referring_agency_id, commission_rate (acente varsayılanı)
│   ├── dental_travel_info.py      # YENİ: seyahat/konaklama modeli
│   ├── dental_commission.py       # YENİ: acente komisyon kaydı (fatura tetikli)
│   ├── crm_lead.py                # +dental.treatment.plan ile ilişki, pipeline otomasyonu
│   └── account_move.py            # +button_post sonrası komisyon kaydı tetikleme
├── data/
│   └── crm_stage_data.xml         # YENİ: 8 aşamalı sağlık turizmi CRM stage seti + crm.team
└── security/
    └── (acente portal ir.rule: agency_id = env.user.partner_id)
```

### 11.8 Alınan Kararlar (2026-11-12)
1. **Acente portalı**: Hibrit — kalıcı Odoo portal hesabı (sürekli takip,
   kendi hasta/komisyon listesi) **+** token tabanlı tekil paylaşım linki
   (hızlı/geçici teklif paylaşımı). Detay: §11.9.
2. **Komisyon ödeme otomasyonu**: Otomatik hesaplama, **fatura kesildiğinde**
   (`account.move` `posted` durumuna geçtiğinde) tetiklenir. `dental.commission`
   kaydı otomatik oluşur; acenteye ödeme bu kayıttan tetiklenen standart
   muhasebe akışıyla (gider faturası/ödeme) yapılır. Detay: §11.5.
3. **CRM entegrasyonu derinliği**: Sağlık turizmine özel 8 aşamalı pipeline
   (Lead → Ön Değerlendirme → Teklif Gönderildi → Onaylandı → Seyahat
   Planlandı → Klinikte → Tamamlandı → Kaybedildi), ayrı `crm.team` ve
   `crm.stage` seti ile. Detay: §11.5.

## 12. Kaynaklar

- https://dentsoft.com.tr/
- https://dentsoft.com.tr/help
- https://dentsoft.com.tr/solutions
- https://dentsoft.com.tr/en/pricing
- https://dentsoft.com.tr/kliniklerde-verimlilik-artisi-dentsoftun-yonetim-araclari
- https://dentsoft.com.tr/dentsoft-ile-hasta-memnuniyetini-artirmanin-yollari
- https://www.alomaliye.com/2022/08/25/saglik-bilgi-yonetim-sistemleri-hakkinda-yonetmelik/ (MBYS/SBYS yönetmeliği)
- https://sbsgm.saglik.gov.tr/ (Sağlık Bilgi Sistemleri Genel Müdürlüğü)
- https://www.enabiz.gov.tr/document/KILAVUZ_DE.pdf (E-Nabız entegrasyon kılavuzu)
- https://mdpgroup.com/blog/urun-takip-sistemi-nedir/ (ÜTS genel bilgi)
- https://www.saglikaktuel.com/d/file/sagliktesisireceteveraporwebservisleri.20210730151145.pdf (MEDULA e-reçete webservis kılavuzu)
- https://www.kommo.com/tr/vakalar/saglik-turizmi-icin-crm/ (sağlık turizmi CRM süreçleri)

# Kullanıcı Kılavuzu — govrico

> Son kullanıcılar için rehber: Uyum Yetkilisi, Risk Yöneticisi, Tesis Yöneticisi, Tesis Güvenlik Yetkilisi, Dış Denetçi.

---

## İçindekiler

- [1. Erişim ve gezinme](#1-erişim-ve-gezinme)
- [2. Kontrol Paneli](#2-kontrol-paneli)
- [3. Kontrol Yönetimi (M03)](#3-kontrol-yönetimi-m03)
- [4. BT ve OT Varlıkları (M04)](#4-bt-ve-ot-varlıkları-m04)
- [5. İş Etki Analizi (M05)](#5-iş-etki-analizi-m05)
- [6. Risk Değerlendirmesi (M06)](#6-risk-değerlendirmesi-m06)
- [7. Belgeler ve Kanıtlar (M07)](#7-belgeler-ve-kanıtlar-m07)
- [8. Olay Yönetimi (M09)](#8-olay-yönetimi-m09)
- [9. PDCA (M11)](#9-pdca-m11)
- [10. Alınan Dersler (M12)](#10-alınan-dersler-m12)
- [11. Yönetim Gözden Geçirmesi (M13)](#11-yönetim-gözden-geçirmesi-m13)
- [12. Denetim Hazırlığı (M17)](#12-denetim-hazırlığı-m17)
- [13. Tedarikçiler (M14)](#13-tedarikçiler-m14)
- [14. Eğitim (M15)](#14-eğitim-m15)
- [15. İş Sürekliliği (M16)](#15-iş-sürekliliği-m16)
- [16. Etkinlik Takvimi (Vade Takvimi)](#16-etkinlik-takvimi-vade-takvimi)
- [17. Zorunlu Belgeler](#17-zorunlu-belgeler)
- [18. E-posta Bildirimleri](#18-e-posta-bildirimleri)
- [19. Yönetişim (M00)](#19-yönetişim-m00)
- [20. Ayarlar (yalnızca Yönetici)](#20-ayarlar-yalnızca-yönetici)
- [Roller ve yapabilecekleriniz](#roller-ve-yapabilecekleriniz)
- [AI Engine — Yapay Zeka Önerileri (M20)](#ai-engine--yapay-zeka-önerileri-m20)
- [Raporlama ve dışa aktarma (M18)](#raporlama-ve-dışa-aktarma-m18)
- [Operasyon Merkezi (M21)](#operasyon-merkezi-m21)
- [OSINT Monitor](#osint-monitor)
- [Ek: Sık sorulan sorular](#ek-sık-sorulan-sorular)

---

## 1. Erişim ve gezinme

### E-posta ve parola ile giriş

[Ekran görüntüsü: giriş sayfası]

1. Tarayıcıyı açın ve `https://grc.azienda.com` adresine gidin
2. İlk alana **kurumsal e-posta adresinizi** girin
3. İkinci alana **parolanızı** girin (en az 12 karakter)
4. **Giriş Yap** düğmesine tıklayın
5. İlk girişte e-posta ile aldığınız geçici parolayı değiştirmeniz istenecektir

Kurumsal SSO kullanıyorsanız **Kurumsal hesapla giriş yap** düğmesine tıklayın ve etki alanı hesabı kimlik bilgilerinizi girin.

> Oturum, 30 dakika hareketsizlik sonrasında aktif kalır. Süre dolduğunda parola yeniden girilmesi istenir. Oturum belirteci, aktif kullanım sırasında otomatik olarak yenilenir.

Parolayı sıfırlamak için: giriş sayfasında **Parolamı Unuttum** seçeneğine tıklayın ve e-posta adresinizi girin. 15 dakika geçerli bir bağlantı alacaksınız.

### Sol üstte tesis (plant) seçimi

[Ekran görüntüsü: üst çubukta plant seçici]

Girişin hemen ardından, sol üstte logonun yanında **tesis seçici** bulunur. Birden fazla tesise veya iş birimine erişiminiz varsa:

1. Mevcut tesisin adına (ya da ilk girişte "Tesis Seç" seçeneğine) tıklayın
2. Kapsamınızdaki tüm tesislerin yer aldığı bir açılır menü belirir
3. Görüntülemek istediğiniz tesise tıklayın — sayfa anında güncellenir

**Tüm tesisler** seçeneği, tüm tesislerin toplu görünümünü gösterir. Bu seçenek yalnızca Uyum Yetkilisi ve çok tesisli erişim rollerine sahip kullanıcılar için mevcuttur.

Tüm işlemler (varlık oluşturma, olay açma, kontrol değerlendirme) o an seçili olan tesisle ilişkilendirilir.

### Sağ üstte dil değişikliği (IT/EN)

[Ekran görüntüsü: üst çubukta dil menüsü]

1. Sağ üstteki dil simgesine (veya mevcut dil koduna) tıklayın
2. İstediğiniz dili seçin: **Italiano**, **English**, **Français**, **Polski**, **Türkçe**
3. Arayüz, sayfayı yeniden yüklemeden anında güncellenir

Seçilen dil tüm arayüze uygulanır. Oluşturulan raporlar ve dışa aktarımlar, oluşturma anında etkin olan dili kullanır.

### Yan menü: ana bölümler ve içerikleri

[Ekran görüntüsü: genişletilmiş menüyle kenar çubuğu]

Sol taraftaki yan menü, yalnızca rolünüze göre erişilebilen bölümleri gösterir. Ana öğeler şunlardır:

| Grup | Öğeler |
|--------|------|
| **Ana** | Dashboard · Operasyon Merkezi (M21)¹ · Reporting (M18) · Operasyonel KPI'lar · Görevler (M08) · Kontrol Listeleri |
| **Compliance** | Kontroller (M03) · Gap Analysis · Belgeler (M07) · Audit Prep (M17) |
| **Risk ve süreklilik** | BIA (M05) · Risk (M06) · IT/OT Varlıkları (M04) · BCP (M16) |
| **Operasyonlar** | Olaylar (M09) · Lessons (M12) · Tedarikçiler (M14) · Eğitim (M15) · PDCA (M11) |
| **Planlama** | Activity Schedule · Zorunlu Belgeler · Son tarih politikası² · Liste Şablonları³ |
| **Organizasyon ve gözden geçirme** | Governance (M00) · Güvenlik hedefleri · Yönetim gözden geçirmesi (M13)⁴ · Siteler (M01)² · Kullanıcılar (M02)⁵ · Yetkinlikler⁶ · Audit Trail (M10)⁷ · MFA Kimlik Doğrulama |
| **Güvenlik**⁸ | OSINT Monitor |
| **Ayarlar**⁵ | E-posta ayarları · Bildirim kuralları · Govrico AI · Yedekleme & Geri Yükleme |

Yalnızca bazı rollere açık öğeler:

1. Super Admin, Compliance Officer, Risk Manager, Internal Auditor, Plant Manager
2. Super Admin, Compliance Officer
3. Super Admin, Compliance Officer, CISO, Risk Manager
4. Super Admin, Compliance Officer, Risk Manager
5. Super Admin
6. Super Admin, Compliance Officer, CISO
7. Super Admin, Internal Auditor, External Auditor
8. Super Admin, CISO, Compliance Officer

Üstteki **«** düğmesi menüyü yalnızca simgelere indirir (öğenin adı fareyle üzerine gelince görünür), **»** ise yeniden açar. Seçiminiz oturumlar arasında hatırlanır.

### Her sayfada bağlamsal yardım için ? simgesi

[Ekran görüntüsü: sayfa başlığının yanındaki ? düğmesi]

Hemen hemen tüm işletimsel sayfalarda modül başlığının yanında küçük bir **`?`** düğmesi bulunur. Tıklandığında, şunları içeren bir yan panel açılır:

- Modülün ne yaptığına ilişkin kısa bir açıklama
- İzlenecek tipik adımlar
- Diğer modüllerle bağlantılar (ör. hangi görevlerin veya PDCA'ların otomatik olarak oluşturulduğu)
- Önerilen ön koşulların listesi ("Başlamadan önce")

Yardım panelini, daha az sık kullandığınız modüllerde yön bulmak veya sistemi yeni meslektaşlarınıza tanıtırken kullanın.

### Alt çubuktaki Kullanıcı Kılavuzu ve Teknik Kılavuz düğmeleri

[Ekran görüntüsü: kılavuz düğmelerini içeren alt çubuk]

Her sayfanın altında, alt çubukta iki sabit düğme bulunur:

- **Kullanıcı Kılavuzu** (kitap simgesi): bu kılavuzu yeni bir sekmede açar
- **Teknik Kılavuz** (İngiliz anahtarı simgesi): mimari ayrıntılarla birlikte teknik kılavuzu açar; yalnızca yönetim erişimine sahip profiller tarafından görülebilir

Her iki düğme de bulunduğunuz modülden bağımsız olarak her zaman görünür.

---

## 2. Kontrol Paneli

[Ekran görüntüsü: ana kontrol paneli]

Kontrol paneli, giriş yaptıktan sonra gördüğünüz ilk sayfadır. İçerik, rolünüze ve seçili tesise göre kişiselleştirilmiştir.

### Ana KPI'lar ne gösterir

Kontrol panelinin üst kısmında 4 ana KPI kutusu bulunur:

| KPI | Ne ölçer |
|-----|----------|
| **Uyum %** | Seçili çerçeve için aktif kontrollerin toplamına oranla "uyumlu" veya "geçerli kanıta sahip kısmi" durumundaki kontrollerin yüzdesi |
| **Açık Riskler** | "Açık" durumundaki risk değerlendirmelerinin sayısı (kabul edilmemiş ve kapatılmamış). Sayı, kırmızı renkle kritik risklerin (skor > 14) sayısını da içerir |
| **Olaylar** | Seçili tesiste açık olaylar. Kırmızı sayılar, aktif NIS2 zamanlayıcılarına sahip olayları gösterir |
| **Süresi Geçmiş Görevler** | Rolünüze (ya da CO iseniz kuruluşunuzun tamamına) atanmış, son tarihi geçmiş görevler |

### Renkleri nasıl yorumlamalı

Platform, tüm arayüzde tutarlı bir renk kuralı kullanır:

- **Yeşil**: her şey yolunda — uyumlu, tamamlandı, geçerli, zamanında
- **Sarı**: dikkat gerekiyor — kısmi, 30 gün içinde sona eriyor, devam ediyor
- **Kırmızı**: kritik — boşluk, süresi geçmiş, yüksek risk (skor > 14), NIS2 zamanlayıcısı sona eriyor
- **Gri**: değerlendirilmedi, Uygulanamaz (N/A), arşivlendi
- **Turuncu**: uyarı veya ihtar — dikkat gerektiriyor ancak henüz kritik değil

Bu renkler durum rozetlerine, ilerleme çubuklarına, ısı haritası göstergelerine ve kenar çubuğu simgelerine uygulanır.

### Yaklaşan son tarihler widget'ı

[Ekran görüntüsü: kontrol panelindeki son tarihler widget'ı]

"Yaklaşan Son Tarihler" widget'ı, sonraki 30 gündeki ilk 10 son tarihi gösterir. Her son tarih için şunları görürsünüz:

- Tür (belge, kanıt, görev, tedarikçi değerlendirmesi vb.)
- Öğenin adı
- Sarı (< 30 gün) veya kırmızı (< 7 gün) renkli son tarih

Bir son tarihe tıklayarak doğrudan ilgili öğenin sayfasına gidebilirsiniz.

### Boş rol uyarıları

Atanmış bir sahibi olmayan zorunlu normatif roller varsa (ör. BGYS yöneticisi atanmamış, VKY boş), kontrol panelinde turuncu renkli "Boş Roller" başlığı ve sayısı ile yönetişim sayfasına (M00) bağlantı görünür. Bu uyarılar uyum KPI'ını olumsuz etkiler.

### Kontrol panelinden doğrudan bir öğeye nasıl gidilir

Kontrol panelindeki her etkileşimli öğe tıklanabilir:

- Süresi geçmiş bir göreve tıklayarak görev kartını açın
- Isı haritasının bir kadranına tıklayarak o bölgedeki riskleri görün
- Bir uyum çubuğuna tıklayarak o çerçeve için filtrelenmiş kontrol kütüphanesine gidin
- Bir olaya tıklayarak olay kartını açın

---

## 3. Kontrol Yönetimi (M03)

[Ekran görüntüsü: kontrol kütüphanesi]

### Kontrol nasıl değerlendirilir

1. **Uyum → Kontrol kütüphanesi** bölümüne gidin
2. İlgilendiğiniz kontrolü bulmak için filtreleri (çerçeve, alan, durum, tesis) kullanın
3. Kartı açmak için kontrolün adına tıklayın
4. **Durum** alanında seçiciyi açmak için tıklayın ve uygun durumu seçin
5. **Değerlendirme Notları** alanına bağlam notu ekleyin (Boşluk ve N/A için zorunludur)
6. **Kanıt Ekle** düğmesiyle kanıtı bağlayın
7. **Kaydet**'e tıklayın

### Uyumlu, Kısmi, Boşluk, N/A arasındaki fark

| Durum | Ne zaman kullanılır |
|-------|---------------------|
| **Uyumlu** | Kontrol tam olarak karşılanıyor. Bunu kanıtlayan geçerli ve süresi dolmamış bir kanıtınız var |
| **Kısmi** | Kontrol yalnızca kısmen uygulandı. Tamamlamak için bir plan var ancak gereksinimler henüz tam olarak karşılanmadı |
| **Boşluk** | Kontrol uygulanmadı. Düzeltici bir eylem gerekli. Otomatik olarak görev oluşturur |
| **N/A** | Kontrol tesisinizin bağlamında geçerli değil. En az 20 karakter içeren yazılı bir gerekçe gerektirir. Gerekçe kaydedilir ve kontrol her yeniden açıldığında görünür. VDA ISA TISAX'ta "Note / Justification" sütununda görünür ve olgunluk düzeyi 0 olarak ayarlanır. TISAX L3 için iki rolün imzasını gerektirir ve 12 ay sonra sona erer |

> Süresi dolmuş kanıta sahip bir kontrol, Uyumlu olarak ayarlamış olsanız bile otomatik olarak "Kısmi"ye döner. Kanıtları güncel tutun.

### Kanıt nasıl yüklenir

1. Kontrol kartından **Kanıt Ekle**'ye tıklayın
2. **Dosya Seç**'e tıklayın ve bilgisayarınızdan dosyayı seçin (kabul edilen formatlar: PDF, DOCX, XLSX, PNG, JPG, ZIP — maksimum boyut 50 MB)
3. Doldurun:
   - **Kısa açıklama** (ör. "15/03/2026 tarihli güvenlik duvarı yapılandırma ekran görüntüsü")
   - **Son tarih** — sistem günlükleri, tarama raporları, sertifikalar için zorunludur. Son tarihi olmayan belgeler için boş bırakın
   - **Çerçeve / kapsanan kontroller** — bu kanıtın belgelediği tüm kontrolleri seçin
4. **Yükle**'ye tıklayın

Kanıt hemen kullanılabilir. Sistem, dosyanın MIME türünün beyan edilen uzantıyla eşleştiğini otomatik olarak doğrular.

### TISAX Implementation description nasıl doldurulur (rehberli görüşme)

VDA ISA İngilizce doldurulur: her TISAX kontrolü için denetçi, beyan edilen olgunluğun yanında gereksinimin **nasıl** uygulandığını okur. Kontrolün **Değerlendirme** sekmesinde «Implementation description (VDA ISA)» kutusu bulunur: metni doğrudan İngilizce yazabilir veya bir TISAX denetçisiyle görüşmeyi canlandıran rehberli görüşmeyi kullanabilirsiniz.

1. **Rehberli görüşme ile doldur (YZ)** düğmesine tıklayın
2. Denetçi kendi dilinizde **konu başına 2–4 soru** sorar (örneğin güvenlik politikası için: belgeler, onayları ve gözden geçirilmeleri, çalışanlara ve iş ortaklarına iletilmesi). Her soruda **denetçinin anlamak istediği**, **nelerden bahsetmeniz gerektiği** ve istenirse köşeli parantez içinde yer tutucular içeren **bir örnek** görünür: kendi durumunuza uyarlayın, kopyalamayın. «Bu sorunun VDA gereksinimleri» orijinal İngilizce gereksinimleri gösterir (L3 kontrollerinde genişletilen L2 kontrolünün gereksinimleri de)
3. Somut yanıt verin: hangi belgeler, sorumlu kim, nasıl işliyor, ne sıklıkla. Bir şey henüz uygulanmıyorsa «hayır» yazın. Kişi adları ve kişisel veriler gerekli değildir
4. **Denetçiyle doğrula** (en fazla **2 tur**): denetçi her gereksinim için karşılanıp karşılanmadığını veya kısmi olduğunu, yanıtların desteklediği **olgunluğu** (beyan edilenden düşükse uyarıyla), sahada isteyeceği **kanıtları** (kontrole zaten bağlı olanları belirterek) ve eksikler hakkında en fazla 3 **ek soruyu** belirtir. Ek soruları yanıtlayın ve gerekirse ikinci turu yapın. Turlar bittikten sonra doğrulama yeniden başlatılabilir: sorulara verilen yanıtlar korunur
5. **İngilizce taslak oluştur**: yapay zeka açıklamayı tüm görüşmeden, konu başına ve olguları tekrarlamadan, yalnızca yazdıklarınızı kullanarak yazar. Son doğrulamada hâlâ karşılanmayan zorunlu gereksinimler `[TO BE COMPLETED]` olarak işaretlenir. Kontrol için kendi dilinizde çevirisi gösterilir
6. **Bu taslağı kullan** metni açıklama alanına kopyalar: okuyun, gerekirse düzeltin ve **Açıklamayı kaydet** düğmesine basın

Yanıtlar **Yanıtları kaydet** ile kaydedilir (doğrulama ve taslak da kaydeder) ve sonraki yılın yeniden değerlendirmesi için kontrolde kalır. Görüşme başlatıldığı dilde kalır. Taslak hiçbir zaman kendiliğinden kaydedilmez: denetim izi, açıklamayı kimin kaydettiğini ve yapay zekadan gelip gelmediğini kaydeder. Yapay zeka yapılandırılmamışsa görüşme kullanılamaz ve kutu, açıklamayı elle yazmak için orijinal gereksinimleri gösterir. Operasyon Merkezi, açıklaması olmayan olgunluk ≥ 3 TISAX kontrollerini işaretler.

### ISO 27001 SOA, VDA ISA TISAX, NIS2 Matriksi nasıl indirilir

[Ekran görüntüsü: uyum dışa aktarma sayfası]

1. **Uyum → Kontrol kütüphanesi** bölümüne gidin
2. Sayfanın sağ üstündeki **Dışa Aktar** düğmesine (indirme simgesi) tıklayın
3. Dışa aktarma türünü seçin:
   - **ISO 27001 SOA** — tüm Ek A kontrolleri ve ilgili durumlarla birlikte Uygulanabilirlik Beyanı
   - **VDA ISA TISAX** — VDA Bilgi Güvenliği Değerlendirme Tablosu, yatay formatta (A4 yatay): her kontrol için olgunluk, durum, owner, **Implementation description**, **Reference documentation** (bağlı belgeler ve kanıtlar) ve Note / Justification. Açıklaması olmayan olgunluk ≥ 3 kontroller "Missing" olarak işaretlenir ve başlıkta sayılır. Açıklama, kontrolün **Değerlendirme** sekmesindeki «Implementation description (VDA ISA)» kutusunda doldurulur
   - **NIS2 Matriksi** — NIS2 uyum matrisi

> **Önemli not**: Dosyanın URL'sini tarayıcıdan kopyalayarak doğrudan açmayı denemeyin; her zaman sayfadaki "Dışa Aktar" düğmesini kullanın. İndirme işlemi aktif oturumun JWT belirtecini gerektirdiğinden platform dışında denendiğinde 401 hatasıyla başarısız olur.

### Çerçeveler arası boşluk analizi

1. **Uyum → Boşluk Analizi** bölümüne gidin
2. Karşılaştırılacak iki çerçeveyi seçin (ör. ISO 27001 vs TISAX L2)
3. Sistem, iki çerçeve arasındaki eşlenmiş kontrolleri gösteren ve şunları vurgulayan bir tablo sunar:
   - Her iki çerçevede de karşılanan kontroller (yeşil)
   - Yalnızca ikisinden birinde karşılanan kontroller (sarı)
   - Her ikisinde de boşluk olan kontroller (kırmızı)
4. Boşluk analizini Excel formatında dışa aktarabilirsiniz

### Çerçeveler arası (ve tesisler arası) durum yayma

**Yay** düğmesi, diğer çerçevelere eşlemeleri olan **Uyumlu** veya **N/A** durumundaki kontroller için kontrol listesinde, durum rozeti yanında görünür.

**Nasıl çalışır:**

| Eşleme türü | Yön | Örnek |
|-------------|-----|-------|
| `Eşdeğer` | Çift yönlü | ISO A.8.1 ≡ TISAX ISA-1.1 → her iki yönde de yayar |
| `Kapsar (covers)` | Yalnızca kaynak → hedef | ISO A, NIS2 art.21'i kapsar → ISO, NIS2'ye yayar; tersi değil |
| `Kısmi`, `İlişkili`, `Genişletir` | Yayılmaz | Ayrı değerlendirme gerektirir |

**Ne kopyalanır:**
- Durum (`compliant` veya `na`) aynı tesisin eşlenmiş kontrolüne
- N/A için: gerekçe de kopyalanır (kaynak kontrole atıfla)
- Güncellenen her kontrol için denetim izi kaydı oluşturulur

**Çok tesisli yayma:**
**"tüm tesisler"** onay kutusunu işaretlemek, yaymayı hedef kontrolün aktif örneğine sahip tüm tesislere genişletir. Bir organizasyonel politika birden fazla siteyle paylaşıldığında kullanın.

> `boşluk`, `kısmi` ve `değerlendirilmedi` durumları yayılamaz: her tesis bunları bağımsız olarak değerlendirmelidir.

---

## 4. BT ve OT Varlıkları (M04)

[Ekran görüntüsü: varlık envanteri]

### Varlık nasıl eklenir

**BT Varlığı:**

1. **Risk → Varlık envanteri → Yeni BT varlığı** bölümüne gidin
2. Zorunlu alanları doldurun:
   - **Ad / FQDN**: ana bilgisayar adı veya IP adresi
   - **İşletim sistemi** ve **sürüm**
   - **EOL tarihi**: sistem desteği sona erdiyse kritiklik otomatik olarak artırılır
   - **İnternet'e maruz**: kritik işaret — risk profilini artırır
   - **Kritiklik düzeyi**: 1'den 5'e (aşağıdaki tabloya bakın)
3. **Bağlantılı kritik süreçler** bölümünde, bu varlığa bağlı olan İEA (M05) süreçlerini seçin
4. **Kaydet**'e tıklayın

**OT Varlığı:**

1. **Risk → Varlık envanteri → Yeni OT varlığı** bölümüne gidin
2. BT varlığı ortak alanlarına ek olarak şunları doldurun:
   - **Purdue düzeyi** (0–5): OT ağ hiyerarşisindeki konum
   - **Kategori**: PLC, SCADA, HMI, RTU, sensör, diğer
   - **Güncellenebilir**: sistem yama yapılamıyorsa, gerekçeyi ve planlanan bakım penceresini belirtin
3. **Kaydet**'e tıklayın

### BT ve OT varlıkları arasındaki fark

| Özellik | BT Varlığı | OT Varlığı |
|---------|-----------|-----------|
| Örnekler | Sunucu, iş istasyonu, güvenlik duvarı, anahtar, uygulamalar | PLC, SCADA, HMI, RTU, endüstriyel sensörler |
| Tipik ağ | Kurumsal ağ, İnternet | Üretim ağı, saha veri yolu |
| Yama | Sık, otomatikleştirilebilir | Sınırlı, bakım pencereleri gerektirir |
| Kesinti etkisi | Veri kaybı, hizmet kullanılamazlığı | Üretim durması, fiziksel hasar, güvenlik riski |
| Risk değerlendirmesi | Maruziyet/CVE boyutları | Purdue/yamalanabilirlik/güvenlik boyutları |

### Kritiklik tablosu 1-5

Varlık oluşturma ve düzenleme formunda her düzey için açıklayıcı araç ipuçları içeren bir kritiklik rozeti bulunur. Referans olarak:

| Düzey | Etiket | Açıklama |
|-------|--------|----------|
| **1** | Düşük | Durma veya tehlikeye girme üretimi etkilemez. Özel bir süreklilik planı olmadan kabul edilebilir kayıp |
| **2** | Düşük-Orta | Etki, idari veya destek işlevleriyle sınırlıdır. 24 saat içinde geri yükleme |
| **3** | Orta | Operasyonel süreçler üzerinde etki. Süreklilik planı gerektirir. Ölçülebilir veri veya üretim kaybı |
| **4** | Yüksek | Durma, önemli ekonomik kayba, müşteriler üzerinde etkiye veya düzenleyici uyumsuzluğa yol açar. RTO < 4 saat |
| **5** | Kritik | Güvenlik etkisi, can riski veya fiziksel hasar ya da toplam üretim durması. RTO < 1 saat. Acil risk analizi gerektirir |

Farklı tesisler arasında tutarlılığı sağlamak için her zaman bu tabloyu kullanın.

### Harici değişiklik nasıl kaydedilir

Bir varlık önemli bir değişikliğe uğradığında (ürün yazılımı güncellemesi, yapılandırma değişikliği, ağ çevresi genişletme):

1. Varlık kartını açın
2. "Değişiklik geçmişi" bölümünde **Değişiklik Kaydet**'e tıklayın
3. Doldurun: değişiklik tarihi, açıklama, tür (yapılandırma / donanım / yazılım / ağ), tahmini etki
4. Kaydedin — değişiklik denetim izine kaydedilir ve varlık "Yeniden Değerlendirilecek" rozetini alır

### "Yeniden Değerlendirilecek" rozeti — ne zaman görünür ve ne yapılır

Turuncu **"Yeniden Değerlendirilecek"** rozeti varlık kartında şu durumlarda görünür:

- Harici bir değişiklik kaydedildiğinde
- Politika tarafından öngörülen periyodik gözden geçirme tarihi sona erdiğinde
- Varlığa bağlı bir riskin skoru önemli ölçüde değiştiğinde
- Varlık, işletim sisteminin EOL tarihine ulaştığında

Ne yapılır: varlık kartını açın, bilgilerin hâlâ doğru olduğunu doğrulayın (özellikle kritiklik, maruziyet ve bağlantılı kritik süreçler), ardından **Yeniden Değerlendirildi Olarak İşaretle**'ye tıklayın. Onaylamadan önce gerekirse alanları güncelleyin.

---

## 5. İş Etki Analizi (M05)

[Ekran görüntüsü: İEA süreçleri listesi]

### Kritik süreç nasıl oluşturulur

1. **Risk → İEA → Yeni süreç** bölümüne gidin
2. Doldurun:
   - **Sürecin adı**: ör. "Üretim siparişleri yönetimi"
   - **Açıklama**: sürecin ne yaptığı, kimler kullandığı
   - **Süreç sahibi**: sorumlu rolü seçin
   - **Departman / fonksiyon**: referans iş birimi
   - **Tesis**: referans tesis
3. Kaydedin — süreç **Taslak** durumuna girer

### MTPD, RTO, RPO — örneklerle basit açıklama

Bu üç parametre, sürecin kesintiye karşı toleransını tanımlar:

| Parametre | Tanım | Pratik örnek |
|-----------|-------|--------------|
| **MTPD** (Maksimum Tolere Edilebilir Kesinti Süresi) | Sürecin şirketin geri dönüşü olmayan zarara uğramasından önce ne kadar süre durabilir | Ör. "Sevkiyat süreci, önemli müşterileri kaybetmeden en fazla 48 saat durabiliyor" |
| **RTO** (Kurtarma Süresi Hedefi) | Bir kesintiden sonra süreci ne kadar sürede geri yüklememiz gerekiyor | Ör. "MES sistemi olaydan sonra 4 saat içinde çalışır duruma gelmeli" |
| **RPO** (Kurtarma Noktası Hedefi) | Kabul edilebilir zarara uğramadan geçmişteki hangi noktaya kadar veri kaybedebiliriz | Ör. "1 saatten fazla üretim verisi kaybedemeyiz" — dolayısıyla yedeklemeler en az saatte bir yapılmalı |

Sistem, bağlantılı İSP planının (M16) tutarlı olup olmadığını doğrulamak için RTO ve RPO kullanır: İSP, İEA'da beyan edilenden daha yüksek bir RTO öngörüyorsa uyarı görünür.

### Akış: taslak → doğrulama → onay

1. **Taslak**: süreç oluşturulmuş ancak henüz doğrulanmamış. Tüm alanları düzenleyebilirsiniz
2. **Doğrulama**: Risk Yöneticisi MTPD/RTO/RPO parametrelerini doğrular ve onaylar ya da değişiklik ister
3. **Onay**: Tesis Yöneticisi resmi onay verir. Süreç değiştirilemez hale gelir — değişiklik yapmak için yeni bir revizyon açılması gerekir

Aşamayı ilerletmek için: süreç kartından **Doğrulama İçin Gönder**'e (Taslak'tan) veya **Onay İçin Gönder**'e (Doğrulama'dan) tıklayın.

### Süreç bir varlığa nasıl bağlanır

1. İEA süreç kartını açın
2. **Bağımlı varlıklar** bölümünde **Varlık Ekle**'ye tıklayın
3. Envanterden (M04) varlığı arayın ve seçin
4. Bağımlılık türünü belirtin: **Kritik** (süreç bu varlık olmadan durur) veya **Destek** (performans düşüşü)
5. Kaydedin

Bağımlılık çift yönlüdür: varlık kendi kartında ona bağımlı olan süreçleri gösterecek ve sürecin kritikliği varlık üzerindeki risk hesaplamasını etkiler.

---

## 6. Risk Değerlendirmesi (M06)

[Ekran görüntüsü: risk değerlendirmesi listesi]

### Doğal risk ile kalıntı risk arasındaki fark

- **Doğal risk**: herhangi bir kontrol olmaksızın risk düzeyi. Varlık veya alan üzerindeki "ham" tehdidi temsil eder
- **Kalıntı risk**: mevcut kontroller uygulandıktan sonra risk düzeyi. Riski kabul etme veya işleme kararının dayandığı değerdir

Değerlendirme formunda önce doğal riski doldurursunuz, ardından sistem bağlantılı kontrollerin durumuna göre kalıntı riski otomatik olarak hesaplar. Kontroller henüz yeterli değilse kalıntı risk yüksek kalır.

### BT ve OT boyutları nasıl doldurulur

**BT risk değerlendirmesi boyutları (4 eksen):**

1. **Maruziyet**: varlık İnternet'te mi? DMZ'de mi? Yalıtılmış mı? (1 = tamamen yalıtılmış, 5 = korumasız İnternet'e maruz)
2. **CVE**: ilgili varlıkların maksimum CVE puanı nedir? (1 = bilinen güvenlik açığı yok, 5 = yamalanmamış kritik CVE)
3. **Sektör tehditleri**: otomotiv sektöründe bilinen aktif tehditler var mı? (1 = yok, 5 = belgelenmiş aktif kampanya)
4. **Kontrol boşlukları**: kaç ilgili kontrol boşluk veya değerlendirilmemiş durumda? (1 = tümü uyumlu, 5 = çoğunluğu boşlukta)

**OT risk değerlendirmesi boyutları (5 eksen):**

1. **Purdue + bağlantı**: sistem BT ağlarına veya İnternet'e bağlı mı? (1 = yalıtılmış düzey 0, 5 = İnternet'e bağlı)
2. **Yamalanabilirlik**: sistem güncellenebilir mi? Ne sıklıkla? (1 = düzenli yamalar, 5 = hiçbir zaman güncellenemiyor)
3. **Fiziksel / güvenlik etkisi**: bir kesinti veya değişiklik fiziksel hasara ya da iş güvenliği sorunlarına yol açabilir mi? (1 = fiziksel etki yok, 5 = kişilerin güvenliğine risk)
4. **Segmentasyon**: OT bölgesi BT'den ve İnternet'ten yeterince ayrılmış mı? (1 = tamamen yalıtılmış, 5 = düz ağ)
5. **Anomali tespiti**: anormal davranışlar için bir tespit sistemi var mı? (1 = aktif özel IDS/ICS, 5 = hiçbir görünürlük yok)

### Kritik eşik (skor > 14) ve oluşturulan otomatik görevler

**Kalıntı risk 14'ü aştığında** (5x5 ısı haritasının kırmızı kadranları):

- Risk Yöneticisi ve Tesis Yöneticisi anında bildirim alır
- 15 günlük son tarihle otomatik olarak risk işlem planlama görevi oluşturulur
- Görev 15 gün içinde tamamlanmazsa Uyum Yetkilisi'ne eskalasyon başlar
- Risk, kontrol panelinde ve ısı haritasında kırmızı olarak vurgulanır

### Riskin resmi olarak kabul edilmesi

Kalıntı risk biliniyorsa ancak kabul edilmesine karar verilirse (ör. işlem maliyeti beklenen etkiden fazla):

1. Risk kartından **Riski Kabul Et**'e tıklayın
2. Resmi kabul formunu doldurun:
   - Gerekçe (zorunlu, en az 50 karakter)
   - Gözden geçirme tarihi (zorunlu — risk periyodik olarak yeniden değerlendirilmelidir)
   - Yetkili sorumlunun dijital imzası
3. Kaydedin — risk "Kabul Edildi" durumuna geçer ve gözden geçirme tarihine kadar uyarı oluşturmaz

### Isı haritası ve yorumlama

[Ekran görüntüsü: 5x5 ısı haritası]

Isı haritası, riskleri Olasılık x Etki 5x5 ızgarasında gösterir:

- **Yeşil** (skor 1-7): kabul edilebilir risk — periyodik izleme
- **Sarı** (skor 8-14): orta risk — 90 gün içinde azaltma planı
- **Kırmızı** (skor 15-25): yüksek risk — otomatik eskalasyon, 15 gün içinde plan

Onu oluşturan risklerin listesini görmek için bir kadrana tıklayın. Farklı tesisler arasındaki risk dağılımını karşılaştırmak için tesis filtresini kullanın.

---

## 7. Belgeler ve Kanıtlar (M07)

[Ekran görüntüsü: belge yönetimi]

### Belge ve Kanıt arasındaki fark

| Özellik | Belge | Kanıt |
|---------|-------|-------|
| Neyi temsil eder | Politika, prosedür, operasyonel talimat | Ekran görüntüsü, günlük, tarama raporu, sertifikalar |
| Zorunlu iş akışı | Evet — hazırlama, gözden geçirme, onay | Hayır — doğrudan yükleme |
| Sürüm yönetimi | Evet — her sürüm onaydan sonra değiştirilemez | Hayır |
| Son tarih | Yalnızca açıkça yapılandırılmışsa | Günlükler, taramalar, sertifikalar için zorunlu |
| Ana kullanım | Bir sürecin var olduğunu ve yönetildiğini kanıtlamak | Bir kontrolün aktif ve işlevsel olduğunu kanıtlamak |

### Belge onay iş akışı (3 düzey)

Belge, sırayla 3 zorunlu aşamadan geçer:

1. **Hazırlama** (belge sahibi): PDF dosyasını yükleyin, meta verileri doldurun (başlık, kod, çerçeve, sahip, gözden geçiren, onaylayan), taslak olarak kaydedin. Belge yalnızca bu aşamada düzenlenebilir
2. **Gözden geçirme** (atanmış gözden geçiren): belgeyi okur, yapılandırılmış notlar ekleyebilir veya onaylayabilir. Reddederse, kalıcı değişiklik günlüğünün bir parçası olan bir yorum yazması gerekir
3. **Yönetim onayı** (Tesis Yöneticisi veya BGYS Yöneticisi): resmi onay verir. Onaydan sonra belge değiştirilemez — değiştirmek için **Yeni Revizyon** düğmesini kullanarak yeni bir revizyon açmanız gerekir

### Kanıt bir kontrole nasıl bağlanır

Yöntem 1 — kontrol kartından:
1. Kontrol kartına gidin (Uyum → Kontrol kütüphanesi → kontrol seçin)
2. "Bağlantılı kanıtlar" bölümünde **Kanıt Ekle**'ye tıklayın
3. Dosyayı yükleyin veya arşivinizdeki mevcut bir kanıtı seçin
4. Kaydedin

Yöntem 2 — kanıt kartından:
1. Kanıtı **Uyum → Kanıtlar → Yeni kanıt** aracılığıyla yükleyin
2. **Kapsanan kontroller** alanında bu kanıtın belgelediği bir veya daha fazla kontrolü seçin
3. Kaydedin

Bir kanıt, farklı çerçevelerden bile birden fazla kontrolü aynı anda kapsayabilir.

### Kanıt son tarihleri ve renkli rozetler

Son tarihi olan kanıtlar, kontrol kartında ve kanıt listesinde renkli bir rozet gösterir:

| Rozet | Anlam |
|-------|-------|
| **Yeşil** | Geçerli kanıt — 30 günden fazla süre kaldı |
| **Sarı** | Sona eriyor — 30 günden az kaldı |
| **Kırmızı** | Süresi dolmuş — son tarih geçti. Bağlantılı kontrol otomatik olarak "Kısmi"ye düşer |
| **Gri** | Son tarih belirlenmemiş |

Sistem, son tarihten 30 gün önce e-posta hatırlatması ve son tarihin gelmesiyle birlikte uyarı gönderir.

### Belge sürüm yönetimi

Onaylanan her belge bir sürüm numarası alır (ör. v1.0, v1.1, v2.0). Tüm sürümlerin eksiksiz geçmişi, belge kartındaki **Sürüm geçmişi** bölümünden erişilebilir. Her sürüm şunları kaydeder:

- Onay tarihi
- Onaylayanın adı
- Değişiklik günlüğü (gözden geçirenin notları)
- Bütünlüğü sağlamak için dosya karması

---

## 8. Olay Yönetimi (M09)

[Ekran görüntüsü: olay listesi]

### Olay nasıl açılır

1. **Operasyonlar → Olaylar → Yeni olay** bölümüne gidin
2. Zorunlu alanları doldurun:
   - **İlgili tesis**: NIS2 konu profilini otomatik olarak belirler
   - **Başlık**: özet açıklama (ör. "MES sistemine yetkisiz erişim — Kuzey tesisi")
   - **Açıklama**: ne olduğu, ne zaman tespit edildiği, nasıl keşfedildiği
   - **İlgili varlıklar**: envanterden seçin (M04)
   - **Başlangıç ciddiyeti**: Düşük / Orta / Yüksek / Kritik — istediğiniz zaman güncellenebilir
3. **Olay Oluştur**'a tıklayın

Oluşturmanın hemen ardından sistem, tesisin NIS2 konusu olup olmadığını değerlendirir ve evet ise olay kartının üst kısmında görünen ACN zamanlayıcılarını başlatır.

### NIS2 işareti ve 24 saatlik zamanlayıcı (ACN bildirimi)

[Ekran görüntüsü: NIS2 zamanlayıcılı olay kartı]

Tesis NIS2 konusu (temel veya önemli) olarak sınıflandırılmışsa, olay kartında üç geri sayım görünür:

- **T+24s — ACN erken uyarısı**: referans Otoritesine ön bildirim (yasal zorunluluk)
- **T+72s — Tam bildirim**: etki ve alınan tedbirlerle ayrıntılı bildirim
- **T+30g — Son rapor**: Kök Neden Analizi içeren kapanış raporu

Tesis NIS2 kapsamındaysa olay **değerlendirilecek** olarak başlar: BGYS Yöneticisi ya bildirim yükümlülüğünü **onaylamalı** — bu durumda T+24s ve T+72s son tarihleri ayarlanır — ya da gerekçeyle **dışlamalıdır**. Olay **30 dakikadan** uzun süre sınıflandırılmadan kalırsa, sistem BGYS Yöneticisine sınıflandırma için bir **hatırlatma uyarısı** gönderir (onun yerine karar vermez). Her karar denetim izine kaydedilir.

Kalan süre 2 saatin altına düştüğünde zamanlayıcılar kırmızı arka planla gösterilir.

### KNA (Kök Neden Analizi) doldurma

1. Olay kartında **Kök Neden Analizi** bölümüne gidin
2. Analiz yöntemini seçin:
   - **5 Neden**: "neden" sorusunun 5 düzeyiyle yönlendirmeli
   - **Ishikawa**: kategoriye göre neden-sonuç diyagramı (İnsanlar, Süreç, Teknoloji, Çevre)
   - **Serbest metin**: yapılandırılmamış anlatı
3. Kök nedeni, başarısız kontrolleri ve önerilen düzeltici eylemleri doldurun
4. **Onay İçin Gönder** aracılığıyla Risk Yöneticisi'ne onay için gönderin

Onaylanmış bir KNA olmadan olay kapatılamaz.

### Kapanış ve otomatik oluşturulan PDCA

KNA onaylandıktan sonra olayı **Olayı Kapat** düğmesiyle kapatabilirsiniz. Kapanış otomatik olarak şunları oluşturur:

- M12'de olay bilgilerini ve düzeltici eylemleri içeren **Alınan Ders**
- Düzeltici eylemler yapısal nitelikteyse (ör. prosedür değişikliği, yeni kontrol uygulaması) M11'de **PDCA** döngüsü
- Başarısız kontroller mevcut politikalar kapsamındaysa M07'deki bağlantılı belgeler üzerinde **gözden geçirme** tetikleyicisi

---

## 9. PDCA (M11)

[Ekran görüntüsü: PDCA döngüleri listesi]

### 4 aşama: PLAN, DO, CHECK, ACT

Her PDCA döngüsü, sürekli iyileştirme eylemini temsil eder. 4 aşama zorunlu bir sıra izler:

- **PLAN**: hedefi, yapılacak eylemleri ve gerekli kaynakları tanımlayın
- **DO**: planlanan eylemleri gerçekleştirin
- **CHECK**: ölçülebilir bir kanıt aracılığıyla sonuçların hedeflerle örtüşüp örtüşmediğini doğrulayın
- **ACT**: çalıştıysa çözümü standartlaştırın; aksi hâlde farklı bir yaklaşımla DO'ya dönün

### Her aşamayı ilerletmek için gerekenler

| Geçiş | Zorunlu koşul |
|-------|---------------|
| **PLAN → DO** | Gerçekleştirilecek eylemin açıklaması (en az 20 karakter). Plan, bağlam dışında da anlaşılır olmalı |
| **DO → CHECK** | Gerçekleştirilen eylemi belgeleyen kanıt (zorunlu): mevcut bir kanıt seçin veya döngüden çıkmadan aynı pencereden dosyayı yükleyin. Yüklenen dosya, döngünün tesisinde ve geçerlilik süresi olmadan döngünün kanıtı olur |
| **CHECK → ACT** | Doğrulama sonucu (açıklayıcı metin) + Seçilen sonuç: **tamam** / **kısmi** / **başarısız** |
| **ACT → KAPALI** | Standartlaştırma: benimsenen çözümün çoğaltılabilir olması için belgelenmesi (en az 20 karakter) |

### CHECK sonucu = başarısız ise ne olur

CHECK aşamasında sonuç **başarısız** ise (çözüm işe yaramadı):

1. Döngü ACT'e ilerlemez, otomatik olarak **DO** aşamasına döner
2. Döngünün günlüğüne başarısızlık tarihi kaydedilir
3. DO aşaması için yeni bir eylem planı doldurulması gerekir
4. Kaç iterasyonun gerektiğini izlemek için DO döngüsü sayacı artırılır

DO-CHECK iterasyonlarının sayısında sınır yoktur, ancak sistem 3'ten fazla iterasyona sahip döngüleri Uyum Yetkilisi'ne bildirir.

### Tesis veya organizasyon döngüsü

Oluştururken **Tesis** alanı döngünün neye uygulandığını belirtir:

- bir **tesis**: döngü yalnızca o tesisle ilgilidir ve o tesisin kullanıcıları tarafından yönetilir;
- **Organizasyon — tüm tesisler**: döngü tüm organizasyon için geçerlidir (ör. ortak bir prosedür veya herkes için bir farkındalık kampanyası). Kapsam otomatik olarak **Organizasyon** olur.

Organizasyon döngüleri tüm tesislerde görünür, ancak bunları yalnızca tüm organizasyona erişimi olan kullanıcılar açabilir ve ilerletebilir (aşama ilerletme, düzenleme, arşivleme, silme); diğerleri için **salt okunur** görünürler ve dosya incelenebilir. Listeyi bir tesise göre filtrelemek, orada da geçerli olan organizasyon döngülerini de gösterir; **Yalnızca organizasyon** seçeneği yalnızca bunları gösterir. Bir organizasyon döngüsünün DO aşamasında herhangi bir tesisten kanıt eklenebilir. Kapanışta oluşturulan alınan ders de organizasyon düzeyindedir ve CHECK sonucu başarısız ise yeni döngü organizasyon döngüsü olarak kalır.

### Olaylardan, bulgulardan, kritik risklerden otomatik oluşturulan PDCA döngüleri

PDCA döngüleri manuel olarak veya otomatik olarak şu kaynaklardan oluşturulur:

- **Kapatılan olaylar (M09)**: KNA'nın düzeltici eylemleri yapısal nitelikteyse — başlangıç aşaması PLAN
- **Denetim bulguları (M17)**: Majör NC ve Minör NC için — ciddiyete göre belirlenen son tarihle PLAN aşamasında başlangıç
- **Skor > 14 olan riskler (M06)**: işlem planı yapısal eylemler gerektirdiğinde — acil PLAN aşaması
- **Yönetim gözden geçirme kararları (M13)**: gözden geçirme tarafından onaylanan her eylem için — PLAN aşaması

Tüm otomatik oluşturma durumlarında PDCA döngüsü, kaynak varlığa (ör. "Olay #OLY-2026-042") ve politikadan kaynaklanan son tarihe atıfta bulunur.

---

## 10. Alınan Dersler (M12)

[Ekran görüntüsü: alınan dersler bilgi bankası]

### Manuel alınan ders nasıl oluşturulur

1. **Yönetişim → Alınan Dersler → Yeni** bölümüne gidin
2. Doldurun:
   - **Başlık**: olayın veya öğrenmenin özet açıklaması
   - **Olay açıklaması**: ne olduğu, bağlamı, önemi
   - **Kullanılan analiz yöntemi**: 5 Neden, Ishikawa, serbest metin
   - **Belirlenen kök neden**
   - **Etkilenen kontroller**: kütüphaneden ilgili kontrolleri seçin
   - **Kısa vadeli eylemler**: 30 gün içinde tamamlanacak eylemler
   - **Yapısal eylemler**: uzun vadeli eylemler (PDCA aracılığıyla yönetilecek)
3. **Onay İçin Gönder**'e tıklayın

Risk Yöneticisi veya Uyum Yetkilisi, alınan ders kuruluşun tamamına bilgi bankasında görünür hâle gelmeden önce onaylar.

### Kapatılan PDCA döngülerinden otomatik oluşturulan alınan dersler

Bir PDCA döngüsü olumlu sonuçla kapatıldığında, sistem otomatik olarak şunları içeren bir alınan ders oluşturur:

- PDCA'yı başlatan orijinal bağlam (olay, bulgu, risk)
- DO aşamalarında gerçekleştirilen eylemler
- CHECK aşamasında elde edilen sonuç
- ACT aşamasında belgelenen standartlaştırma

Otomatik alınan ders "Taslak" durumunda başlar ve onaydan önce gözden geçirilmek üzere PDCA döngüsünün sahibine görev olarak atanır.

PDCA döngüsü organizasyon düzeyindeyse alınan ders de organizasyon düzeyindedir: tüm tesisler görebilir, ancak yalnızca tüm organizasyona erişimi olan kullanıcılar yönetebilir.

### Bilgi bankasında arama

**Yönetişim → Alınan Dersler → Bilgi bankası** bölümüne gidin. Şunlara göre arayabilirsiniz:

- **Anahtar kelime**: başlık ve açıklama üzerinde metin araması
- **Çerçeve / kontrol**: etkilenen kontrollere göre filtrele
- **Olay türü**: olay, bulgu, risk, gönüllü iyileştirme
- **Tesis**: yalnızca tesisinizdeki alınan dersler veya tüm tesisler (çok tesisli erişiminiz varsa)
- **Dönem**: onay tarihi

Yalnızca onaylanmış alınan dersler gösterilir. Taslaklar yalnızca sahip ve gözden geçirenler tarafından görülebilir.

---

## 11. Yönetim Gözden Geçirmesi (M13)

[Ekran görüntüsü: yönetim gözden geçirmesi]

Modül, ISO/IEC 27001:2022 §9.3'ün gerektirdiği yönetimin gözden geçirmesi sürecine rehberlik eder ve arşivlenecek, denetçiye sunulacak tutanağı üretir.

### Gözden geçirme nasıl oluşturulur

1. **Yönetişim → Yönetim Gözden Geçirmesi → Yeni gözden geçirme** bölümüne gidin
2. Doldurun:
   - **Başlık**: ör. "Yönetimin gözden geçirmesi 2026"
   - **Tesis**: bir tesis veya tüm kuruluşun gözden geçirmesi için **org-wide** (veriler tüm tesisleri kapsar ve tutanak tesis bazında bir görünüm içerir)
   - **Toplantı tarihi**
   - **Organ**: gözden geçirmeyi yürüten yönetişim organı (bkz. [Yönetişim → Yönetişim organları](#19-yönetişim-m00)); yapılandırılmışsa yönetim kurulu önerilir. Davetliler, gözden geçirme tarihinde organın görevdeki üyeleridir; toplantıya organın başkanı başkanlık eder
   - Organ olmadan, M00 Governance'ta atanan CISO başkan olarak önerilir (tesisin CISO'su, yoksa kuruluşunki; o da yoksa ISMS Manager)
3. **Gözden geçirme oluştur**'a tıklayın: sistem zorunlu maddeleri içeren gündemi otomatik oluşturur

Ayrıntı görünümünden, onaya kadar **davetliler ve katılım** yönetilir: her biri için katıldı, katılmadı veya vekil aracılığıyla (vekilin adıyla), rolü ve başkanlık eden kişi — bu kişinin katılmış olması gerekir. Organ üyeleri, platform kullanıcıları ve hesabı olmayan **konuklar** (ör. bir danışman) ad ve unvanla eklenebilir. **Organdan yeniden yükle** görevdeki üyeleri yeniden yükler. Tutanakta ad ve unvan, sonradan değişse bile gözden geçirme tarihindeki haliyle kalır. Organ ve sonraki gözden geçirme tarihi de değiştirilebilir.

### Zorunlu gündem (ISO 27001 §9.3.2)

Her gözden geçirme, silinemeyen şu maddeleri içerir:

- a) Önceki yönetim gözden geçirmelerindeki eylemlerin durumu
- b) BGYS ile ilgili dış ve iç hususlardaki değişiklikler
- c) İlgili tarafların ihtiyaç ve beklentilerindeki değişiklikler
- d) Bilgi güvenliği performansı (uygunsuzluklar ve düzeltici faaliyetler, izleme ve ölçme, denetimler, hedefler)
- e) İlgili taraflardan geri bildirimler
- f) Risk değerlendirmesinin sonuçları ve risk işleme planının durumu
- g) Sürekli iyileştirme fırsatları

**Madde ekle** ile ek maddeler eklenebilir. Zorunlu bir maddenin ne tartışması ne de kararı varsa **toplantı kapatılamaz**: eksik maddeler vurgulanır.

### Veri anlık görüntüsü

Toplantı anındaki GRC verilerini dondurmak için **Veri anlık görüntüsü oluştur**'a tıklayın. Veriler, ilgili oldukları gündem maddelerinin içinde kısa listelerle gösterilir (en fazla 10 öğe, "… ve N tane daha" ile):

- **a)** önceki gözden geçirmelerin eylemleri: bir önceki gözden geçirmenin tüm eylemleri ile dönem içinde hâlâ açık olan veya kapatılan daha eski eylemler; gecikmiş olanlar vurgulanır
- **d)** çerçeve başına uyum ve açığı olan kontroller; eşik dışı operasyonel KPI'lar; son 12 ayın denetimleri, hazırlık düzeyi ve açık uygunsuzluklar (önce büyükler); açık ve NIS2 bildirilen olaylar; takılı kalmış PDCA döngüleri ve gecikmiş görevler; süresi dolmuş, gözden geçirilecek ve son gözden geçirmeden beri onaylanan belgeler
- **f)** kritik riskler (doğal → artık, işlem, sahip, plan olup olmadığı), resmi olarak kabul edilen riskler, BCP planı olmayan kritik süreçler
- **g)** denetimlerden çıkan iyileştirme fırsatları

Anlık görüntü onaya kadar yeniden oluşturulabilir; sonrasında tutanağın içeriği olduğu için sabit kalır.

### Toplantı nasıl yürütülür ve kararlar nasıl kaydedilir

1. **Toplantıyı başlat**'a tıklayın
2. Her madde için: maddeyi açın, verileri inceleyin, **tartışmayı** yazın ve kaydedin
3. **Karar ekle** ile gözden geçirmenin çıktılarını (§9.3.3) kaydedin: açıklama, **tür** (iyileştirme, BGYS değişikliği, kaynaklar, diğer), sorumlu ve son tarih
4. Kararın uygulanması gerekiyorsa şunları işaretleyin:
   - **Görev oluştur**: M08'de, kararın son tarihiyle **seçilen role atanmış** bir görev açar (BGYS değişiklikleri için yüksek öncelik)
   - **PDCA döngüsü aç**: M11'de bir PDCA döngüsü açar (tüm kuruluşun gözden geçirmesi için bir tesis veya yalnızca tüm organizasyona erişimi olanlara açık **Organizasyon (tüm tesisler)** seçeneğini seçin)
   Bağlı görevin durumu ve PDCA'nın aşaması karar üzerinde görünür
5. **Tamamlandı olarak işaretle**'ye tıklayın: sistem zorunlu maddeleri kontrol eder ve takvim politikasına göre **sonraki gözden geçirme tarihini** önerir. Planlanan toplantılar ve sonraki gözden geçirme **Takvim**'de görünür

### Yapay zekâ ile yönetici özeti

Yönetici özeti tutanağı açar: BGYS'nin genel değerlendirmesi, kritik konular, kararlar ve öncelikler.

- **Elle yaz** veya
- **Yapay zekâ ile taslak oluştur** (anlık görüntü gerekir; en iyisi gündemi doldurduktan sonra yapmaktır). Yapay zekâ motoruna toplu veriler ve tutanak metinleri gönderilir: kişi adları yer tutucularla değiştirilir ve metin standart anonimleştirmeden geçer (e-postalar, telefonlar, tesis adları). Taslak **yapay zekâ tarafından üretilmiş içerik** olarak işaretlenir ve gerekirse düzenledikten sonra **Tutanağa kabul et**'e tıklayana kadar **tutanağa girmez**; **Taslağı at** taslağı siler

Tutanakta özet, yapay zekâ desteğiyle (ve hangi modelle) hazırlanıp hazırlanmadığını, düzenlenip düzenlenmediğini ve kimin kabul ettiğini belirtir.

### Onay ve tutanak

1. Onayın iki biçimi vardır (ikisi de anlık görüntü ve tamamlanmış toplantı gerektirir):
   - **Uygulamada onayla**: **bağlı hesabı olan, organın görevdeki bir üyesi** (ör. bir yönetim kurulu üyesi) verebilir; yalnızca kendi organının gözden geçirmelerini görür ve onaylar, bunları düzenleyemez; tutanakta adı ve unvanı yer alır. Yönetişim (Compliance Officer) de onaylayabilir
   - **Organ kararını kaydet**: organ platform dışında karar aldıysa yönetişim **karar numarasını ve tarihini** (toplantıdan önce olamaz) ve isteğe bağlı olarak kanıt olarak **M07 belgesini** kaydeder; tutanakta “<organ> tarafından onaylandı — … tarihli … sayılı karar” ve kaydeden kişi yer alır

   Onaydan sonra toplantı verileri, davetliler, gündem, kararlar ve özet değiştirilemez; yalnızca kararların ilerleme durumu güncellenebilir
2. Tutanağı **PDF** veya **HTML** olarak indirin: gözden geçirme bilgileri, katılımcılar, yönetici özeti, dikkat edilecek noktalar, veriler/tartışma/kararlarla gündem, karar özeti, onay. İndirme denetim izine kaydedilir
   **Toplantı durumu** altında, Plant Registry'de tesisler için yüklenenler arasından PDF ve HTML'in sağ üst köşesindeki **tutanak logosu** seçilir (gözden geçirme tesisinin logosu önerilir). Onaydan sonra da değiştirilebilir
3. **Denetim paketi** (M03), gözden geçirmelerin özetini ve onaylanmış gözden geçirmelerin PDF tutanaklarını içerir

### Hedefli gözden geçirme

İki tam gözden geçirme arasında organ, belirli konular için toplanabilir; örneğin bir politikayı onaylamak veya küçük bir değişikliğe karar vermek için. Bu toplantılar için **Hedefli** türünde bir gözden geçirme oluşturun (oluşturma formunda seçilir, sonradan değiştirilemez).

1. Hedefli gözden geçirmede zorunlu §9.3.2 maddeleri, veri anlık görüntüsü, yönetici özeti ve yapay zekâ taslakları **yoktur** ve **periyodik gözden geçirme sayılmaz**: bir sonraki gözden geçirme tarihi son tam gözden geçirmede belirlenen tarih olarak kalır
2. **Karar verilecek belgeler**: **“Karar verilecek belgeleri ekle”**, kapsamdaki taslak, incelemede veya onay aşamasındaki belgeleri ve onaylanmamış yeni sürümü olan yürürlükteki belgeleri listeler (*Zorunlu*, *Yeni sürüm*, *Organ kararı* etiketleri). Seçilen her belge, seçim anında sabitlenen **incelenen revizyon** ile bir gündem maddesi olur
3. Her belge için **kararı** kaydedin: *Onaylandı*, *Ertelendi* veya *Reddedildi*; isterseniz tartışmaya not ekleyin. Seçimden sonra yeni bir revizyon yüklenirse madde bunu belirtir: **“Güncelle”**yi kullanın (karar yeni metin üzerinden yeniden kaydedilmelidir)
4. Diğer kararlar için tam gözden geçirmedeki gibi **serbest maddeler** ekleyin (tartışma, kararlar, görevler, PDCA)
5. **Toplantıyı kapatın**: en az bir madde gerekir ve her belgenin bir kararı olmalıdır
6. **Tutanağı onaylayın** (uygulamada veya kararı kaydederek): kararlar belgelere uygulanır. *Onaylananlar* organ kararıyla, karar veya toplantı tarihiyle yürürlüğe girer; *reddedilenler* taslağa döner; *ertelenenler* beklemede kalır. Bir karar uygulanamazsa (örneğin toplantıdan sonra yeni bir revizyon yüklendiyse) nedeniyle birlikte gösterilir ve yeniden denenebilir
7. Hedefli gözden geçirmenin **tutanağı**, incelenen belgeleri revizyon ve kararıyla, maddeleri ve kararları içerir; **denetim paketinde** hedefli toplantılar `09_management_review/sedute_intermedie/` klasöründedir

---

## 12. Denetim Hazırlığı (M17)

[Ekran görüntüsü: denetim hazırlığı — program listesi]

### Yıllık Program

#### Sihirbazla program nasıl oluşturulur (4 adım)

1. **Denetim → Denetim Hazırlığı → Yeni program** bölümüne gidin
2. 4 adımlı sihirbaz açılır:

**Adım 1 — Temel veriler**
- Program yılı (ör. 2026)
- Referans tesis
- Denetlenecek çerçeve (ISO 27001, TISAX L2, TISAX L3, NIS2 — bir veya daha fazla seçin)
- Program adı (ör. "ISO 27001 Denetim Programı — Kuzey Tesisi 2026")

**Adım 2 — Kapsama parametreleri**
Denetimin kapsam düzeyini seçin:
- **Örnek (%25)**: kontrollerin dörtte biri üzerinde spot denetim. Ara kontroller için veya kaynaklar sınırlı olduğunda uygundur
- **Genişletilmiş (%50)**: kontrollerin yarısının kapsamı. Derinlik ve sürdürülebilirlik arasında denge
- **Tam (%100)**: çerçevenin tüm kontrollerinin eksiksiz denetimi. Resmi sertifikalar için zorunludur

**Adım 3 — Önerilen planı gözden geçirme**
Sistem, mevcut kontrol durumunu analiz eder ve şu özelliklere sahip önerilen bir plan oluşturur:
- Q1 ve Q3'ü **en fazla boşluğa sahip alanlara** (en kritikler önce denetlenir) odaklar
- Kalan kontrolleri Q2 ve Q4'e dağıtır
- Tesiste mevcut rollere göre denetçiler önerir

Manuel olarak düzenleyebilirsiniz: her çeyreğin tarihleri, her oturuma atanan denetçi, her çeyreğe dahil edilen kontrollerin listesi.

**Adım 4 — Onay**
- Programın özetini gözden geçirin
- **Programı Onayla**'ya tıklayın
- Program etkin hale gelir ve dahil edilen tüm rollere görünür

#### Önerilen plan nasıl yorumlanır

Sistem, olası sertifika denetimlerinden önce çözüme yeterli süre tanımak amacıyla başlangıç çeyreklerinde (Q1 ve Q3) en fazla boşluğa sahip alanları önceliklendirir. İyi kapsamaya sahip alanlar Q2 ve Q4 çeyreklerine atanır. Dağılımın denetçiler için iş yükü açısından sürdürülebilir olduğunu kontrol edin.

#### Çeyrek başına tarihler ve denetçiler nasıl değiştirilir

Onaylanan programın ayrıntısından:
1. Güncellenecek çeyreğin yanındaki düzenleme simgesine tıklayın
2. Başlangıç/bitiş tarihini ve atanan denetçiyi değiştirin
3. Kaydedin — değişiklik programın günlüğüne kaydedilir

#### Program nasıl onaylanır

Sihirbazın 4. Adımı tamamlandığında program otomatik olarak "Onaylandı" durumuna geçer. Uyum Yetkilisi bir bildirim alır. Program artık atanan denetçiler tarafından görünürdür.

---

### Denetim Yürütme

[Ekran görüntüsü: denetim çeyreği ayrıntısı]

#### Bir çeyrekten denetim nasıl başlatılır

1. Onaylanan programdan ilgilendiğiniz çeyreğe gidin
2. **Denetimi Başlat**'a tıklayın — çeyrek "Planlandı"dan "Devam Ediyor"a geçer
3. O çeyrek için doğrulanacak kontrollerin kontrol listesi açılır

#### Örnek ile tam kapsama — pratik farklar

- **Örnek**: yalnızca sistem tarafından seçilen kontrol alt kümesini görürsünüz (toplam %25 veya %50'si). Örnekte yer almayan kontrol ekleyemezsiniz
- **Tam**: çerçevenin tüm kontrollerini görürsünüz. Denetimi kapatmadan önce her biri için kanıt doldurmanız gerekir

Her iki durumda da kontrol listesinin yapısı aynıdır — fark yalnızca doğrulanacak kontrol sayısındadır.

#### Kontrol listesi nasıl doldurulur

Kontrol listesindeki her kontrol için:
1. Ayrıntıyı genişletmek için kontrole tıklayın
2. Beyan edilen durumu ve bağlantılı kanıtı doğrulayın
3. **Denetçi yargısını** seçin: Onaylandı / Uygunsuz / Gözlem / Fırsat
4. Yargı "Onaylandı" değilse **Bulgu Ekle**'ye tıklayın (aşağıya bakın)
5. Uygunsa denetçi notları alanına not ekleyin
6. **Yargıyı Kaydet**'e tıklayın

#### Bulgu nasıl eklenir

1. Kontrol kartından **Bulgu Ekle**'ye tıklayın
2. Doldurun:
   - **Bulgunun başlığı**
   - **Ayrıntılı açıklama**: neyin eksik olduğu veya neyin uygunsuz olduğu
   - **Bulgu türü** (aşağıdaki tabloya bakın)
   - **Referans kontrol**
   - **Destekleyici kanıt**: açılış aşamasında isteğe bağlı, Majör NC için zorunlu

#### Bulgu türleri ve yanıt süreleri

| Tür | Anlam | Yanıt süresi |
|-----|-------|--------------|
| **Majör NC** (Majör Uygunsuzluk) | Uyumluluk veya güvenlik üzerinde önemli etkisi olan karşılanmamış gereksinim | 30 gün |
| **Minör NC** (Minör Uygunsuzluk) | Kısmen karşılanmamış gereksinim, sınırlı etki | 90 gün |
| **Gözlem** | Henüz uygunsuzluk olmayan potansiyel zayıflık. İzlenmeli | 180 gün |
| **Fırsat** | Uyumluluk üzerinde etkisi olmayan iyileştirme önerisi. Zorunlu son tarih yok | — |

Yanıt süreleri, bu politikalara dayanılarak bulgunun açılış tarihinden itibaren otomatik olarak hesaplanır. Majör NC için otomatik olarak PDCA döngüsü de oluşturulur.

#### Bulgu nasıl kapatılır

1. Bulgu kartından, düzeltici eylemleri aldıktan sonra **Kapanış Öner**'e tıklayın
2. **Kapanış kanıtı** yükleyin (Majör NC ve Minör NC için zorunlu)
3. **Kapanış yorumu** girin: alınan eylemleri açıklayın
4. Bulgu "Doğrulama Aşamasında" durumuna geçer
5. Sorumlu denetçi kanıtı doğrular ve **Kapanışı Onayla**'ya veya yorumla **Bulguyu Yeniden Aç**'a tıklar

#### Denetim raporu nasıl indirilir

Devam eden veya kapatılmış denetimden:
1. Denetim sayfasının sağ üstündeki **Rapor** düğmesine tıklayın
2. Raporun dilini seçin
3. Sistem bir **HTML** rapor oluşturur: kapsam özeti, türe göre bulgu listesi, kapanış durumu, önceki denetime kıyasla trend
4. Rapor, indirme için hemen kullanılabilir (yazdırılabilir/arşivlenebilir)

---

### Denetim İptal Etme

[Ekran görüntüsü: denetim iptal düğmesi]

#### "İptal" ile silme arasında ne zaman kullanılır

- Planlanmış bir denetim yapılmayacak ancak orijinal planlamanın izini korumak istiyorsanız **İptal Et**'i kullanın (ör. tarih değişikliği, kapsam değişikliği, şirket acil durumu)
- **Silme**, "Devam Ediyor" veya "Kapatıldı" durumundaki denetimler için mevcut değildir — başlatılmış denetimler için her zaman "İptal Et"i kullanın

#### İptal nasıl yapılır

1. Denetim listesinden, denetim satırındaki **İptal Et** düğmesine (X simgesi) tıklayın
2. **İptal gerekçesini** gerektiren bir iletişim kutusu açılır (zorunlu, en az 10 karakter)
3. Gerekçeyi girin (ör. "Denetçi müsaitliği nedeniyle Q3'e ertelendi")
4. **İptali Onayla**'ya tıklayın

#### Açık bulgulara ne olur

Zaten açık bulguları olan bir denetimi iptal ettiğinizde:
- Bulgular, iptal gerekçesiyle **otomatik olarak kapatılır** "İptal Edildi" durumuyla
- Bulgulara bağlı PDCA'lar açık kalır ve manuel olarak yönetilmesi gerekir
- Yıllık program değiştirilmez — çeyrek, gerekçenin iziyle birlikte "İptal Edildi" olarak işaretlenir

İptal edilen denetim hiçbir zaman fiziksel olarak silinmez — izlenebilirliği sağlamak için "İptal Edildi" durumuyla arşivde kalır.

---

## 13. Tedarikçiler (M14)

[Ekran görüntüsü: tedarikçi listesi]

Modül **Operasyonlar → Tedarikçiler** menüsünden açılır ve beş sekmeden oluşur: **Tedarikçiler**, **Anketler**, **Anket şablonları**, **NDA durumu** ve **Değerlendirme ayarları**. Tedarikçileri Super Admin, Compliance Officer, Risk Manager ve Plant Manager oluşturur ve düzenler; iç ve dış denetçiler yalnızca okuyabilir. Her kullanıcı kendi tesislerinin tedarikçilerini ve tesis atanmamış tedarikçileri (tüm kuruluşun tedarikçileri) görür.

### Tedarikçi nasıl kaydedilir

1. **Tedarikçiler** sekmesinde **+ Yeni tedarikçi**'ye tıklayın
2. Doldurun:
   - **Unvan (şirket adı)**, **Vergi / KDV no** ve **Merkez ülkesi** — zorunlu
   - **Tedarikçi e-postası (TO)** — zorunlu, anketlerin alıcısıdır; **Ek CC e-postaları** alanına bilgi olarak başka kişiler ekleyebilirsiniz
   - **Tedarik açıklaması** — tedarikçinin ne sağladığı; CPV kodu önerisi için de kullanılır
   - **Risk seviyesi** — ilk tahmininiz; asıl değerlendirme aşağıda açıklanan kaynaklardan gelir
   - **ACN / NIS2** bölümü: tedarikin **CPV kodları** (IA düğmesi, tedarikçi adı olmadan gönderilen açıklamadan kod önerir; her öneri elle kabul edilmelidir), **NIS2 kapsamında önemli tedarikçi** işareti ve işaretliyse **önem kriteri** (yapısal BİT tedariki, ikame edilemezlik veya her ikisi) ile **% tedarik yoğunluğu**
   - **TISAX** bölümü: tedarikçi TISAX kapsamındaki bilgileri işliyorsa (ör. OEM müşterilerinin verileri veya prototipleri) ya da kapsamdaki sistemlere erişiyorsa (VDA ISA 6.1.1) **TISAX kapsamında önemli tedarikçi** işareti
3. **Tedarikçi oluştur**'a tıklayın

**Mükerrer kayıt kontrolü** — formu doldururken sistem daha önce kaydedilmiş tedarikçileri arar:

- **Aynı vergi numarası** (boşluklar, noktalar, tireler ve ülke öneki yok sayılarak karşılaştırılır, ör. `IT 0123.4567.890` = `01234567890`): kayıt **engellenir**. Mevcut tedarikçi yetki alanınızdaysa **Aç** ile açabilirsiniz; yetki alanınız dışındaki bir tesiste kayıtlıysa yalnızca var olduğunu görürsünüz ve tesisinizle ilişkilendirmesi için bir Compliance Officer'a başvurmanız gerekir. Silinmiş bir tedarikçi yeniden girişi engellemez.
- **Benzer şirket unvanı** (büyük/küçük harf, noktalama ve S.r.l., S.p.A., GmbH, Ltd. Şti. gibi şirket türleri yok sayılarak): benzer tedarikçileri listeleyen bir **uyarı** görünür; yine de oluşturmak için **Kontrol ettim: bu farklı bir tedarikçi** seçeneğini işaretleyin. Denetim izi, oluşturma anında kaç benzer ad bulunduğunu kaydeder.

Düzenleme simgesiyle verileri ve tedarikçinin **Durumunu** (aktif, askıda, sonlandırılmış) değiştirebilirsiniz. Silme işlemi mantıksaldır (tedarikçi geçmişte kalır) ve anketlerini de kapsar.

**Yoğunlaşma** — yüzde, TPRM eşiğini belirler (ACN 127434 sayılı Karar): %20'nin altı **düşük**, %20 ile %50 arası **orta**, %50'nin üstü **kritik**. Bir tedarikçi kritik eşiğe girdiğinde sistem, yoğunlaşma düşene kadar yalnızca bir kez bildirim gönderir.

### Tedarikçi listesi

Liste her tedarikçi için vergi/KDV no, ülke, yoğunlaşma, **Adj risk**, durum ve son değerlendirmenin tarihi ile geçerlilik sonunu gösterir. Unvan, vergi/KDV no veya e-posta ile arama yapabilir, risk, durum, NIS2 önemi ve TISAX önemine göre filtreleyebilirsiniz; **Risk** filtresi Adj risk üzerinde çalışır ve **Değerlendirilmemiş** seçeneği hiçbir değerlendirmesi olmayan tedarikçileri listeler.

**↓ CSV dışa aktar**, tüm tedarikçileri, yalnızca NIS2 kapsamındakileri veya yalnızca TISAX kapsamındakileri CPV kodları, NIS2 kriteri, yoğunlaşma ve değerlendirme tarihleriyle indirir.

Ada tıklamak tedarikçi ayrıntısını üç bölümle açar: **İç değerlendirme**, **Üçüncü taraf denetimleri** ve **NDA / Sözleşmeler**.

### Risk nasıl hesaplanır (Adj risk)

**Adj risk**, her biri yalnızca mevcutsa dikkate alınan üç kaynak arasındaki en kötü sınıftır (düşük, orta, yüksek, kritik):

1. güncel **iç değerlendirme**;
2. değerlendirilmiş ve süresi dolmamış son **anket** (platformdan gönderilen veya kaydedilmiş mevcut değerlendirme);
3. yapılandırılan geçerlilik süresi içinde onaylanmış son **üçüncü taraf denetimi**.

Tedarikçi NIS2 kapsamındaysa ve yoğunlaşma kritikse sınıf bir seviye yükselir (ayarlarda seçenek etkinse). Hiçbir kaynak yoksa tedarikçi **değerlendirilmemiş** olarak görünür. Hesaplama her yeni değerlendirmede ve her gece yapılır; böylece süresi dolan bir değerlendirme kendiliğinden hesaba katılmaz.

### İç değerlendirme

Tedarikçi ayrıntısında, **İç değerlendirme** bölümünde **Değerlendirmeyi başlat**'a (veya **Yeni değerlendirme**'ye) tıklayın ve altı parametreye 1 (en düşük risk) ile 5 (en yüksek risk) arasında puan verin: **İş etkisi**, **Sistem erişimi**, **İşlenen veriler**, **Tedarikçi bağımlılığı**, **BT entegrasyonu** ve **Siber sertifika uyumluluğu**. Önizleme, kaydetmeden önce ağırlıklı puanı ve ortaya çıkan sınıfı gösterir. Her yeni değerlendirme öncekinin yerini alır; önceki **Değerlendirme geçmişinde** kalır.

### Anketler

**Şablonlar** — **Anket şablonları** sekmesinde bir veya daha fazla örnek e-posta hazırlarsınız: ad, anketin **form URL'si** (örneğin bir çevrimiçi form), konu ve metin. Konu ve metinde `{supplier_name}` tedarikçinin adına dönüşür; metinde `{questionnaire_link}` form bağlantısına dönüşür; metinde yoksa bağlantı e-postanın sonuna eklenir.

**Gönderim** — tedarikçi listesinde **Anket**'e tıklayın, şablonu seçin ve **Gönder**'e tıklayın. E-posta tedarikçinin TO adresine, CC e-postaları bilgi olarak eklenerek gider. Tedarikçi harici formu doldurur: platform yanıtları otomatik olarak almaz.

**Hatırlatmalar** — her pazartesi anketleri gönderen kişi, 7 günden uzun süredir yanıtsız olanları içeren tek bir özet e-posta alır. **Anketler** sekmesinden anketi **Yeniden gönder**ebilirsiniz; yanıtsız 3. gönderimden itibaren liste tedarikçiyle doğrudan iletişime geçilmesi gerektiğini belirtir.

**Değerlendirme** — yanıtları okuduktan sonra **Anketler** sekmesinde **Değerlendir**'e tıklayın ve **değerlendirme tarihini**, **değerlendirmeyi** (risk seviyesi) ve varsa notları girin. Geçerlilik sonu, ayarlarda yapılandırılan anket geçerlilik süresiyle hesaplanır (varsayılan 12 ay).

**Anketler** sekmesinin üstünde geçerli değerlendirmeler, 90 gün içinde süresi dolacaklar, yanıt bekleyen ve süresi dolmuş anketler görünür: bir kutuya tıklamak listeyi filtreler.

**Mevcut bir değerlendirmeyi kaydetme** — platformu kullanmaya başlamadan önce değerlendirilmiş tedarikçiler veya kağıt üzerinde toplanan bir anket için:

1. **Anketler** sekmesinden (veya tedarikçi kartından) **Mevcut değerlendirmeyi kaydet**'e tıklayın
2. Tedarikçiyi, değerlendirmenin **tarihini** (gelecek tarih olamaz) ve **sonucu** (risk seviyesi) girin
3. **Referans / notlar** alanına (zorunlu) değerlendirmenin nerede saklandığını ve kimin doldurduğunu yazın: denetçiye göstereceğiniz bilgi budur
4. **Kaydet**'e tıklayın. Tedarikçiye e-posta gönderilmez; Anketler sekmesinde kayıt **Kaydedildi** etiketiyle görünür

### Değerlendirme tarihi ve geçerlilik sonu

Değerlendirme tarihi **tedarikçi kaydına girilmez**: sistem bunu kaydedilen son değerlendirmeden türetir. Bu değerlendirme şunlardan biri olabilir:

- platformdan gönderilen bir **anketin** sonucu (**Anketler → Değerlendir** sekmesi);
- **mevcut bir değerlendirme**, yani platform dışında yapılmış bir değerlendirme;
- onaylanmış bir **üçüncü taraf denetimi**.

**Geçerlilik sonu**, **Değerlendirme ayarları** bölümünde yapılandırılan geçerlilik süresiyle hesaplanır (varsayılan 12 ay). Tedarikçi listesi tarihi, kaynağı ve geçerlilik sonunu gösterir; takvim, süre yaklaştığında **Tedarikçi yeniden değerlendirmesi** kalemini gösterir ve Compliance Officer için bir hatırlatma açar.

### Üçüncü taraf denetimleri: planlandı → tamamlandı → onaylandı / reddedildi

Denetime tabi tutulan tedarikçiler için (kendi denetiminiz veya üçüncü bir kuruluşun), tedarikçi ayrıntısında **Üçüncü taraf denetimleri** bölümünde:

1. **+ Yeni denetim**: tarihi girin ve **Kaydet**'e tıklayın. Denetim **Planlandı** durumundadır
2. **Tamamla**: **Governance**, **Security** ve **BCP** için 0–100 puanları ve **bulguları** girin. **Overall** puanı girilen puanların ortalamasıdır. Tamamlandığında tedarikçinin risk seviyesi güncellenir (Overall ≥ 75 düşük, ≥ 50 orta, 50'nin altı yüksek) ve denetim tamamlandı bildirimi gönderilir
3. **Onayla** veya **Reddet**: denetimi gözden geçiren kişi notlarını kaydeder; ret için gerekçe zorunludur (en az 10 karakter)

Adj riske yalnızca **onaylanmış** bir denetim ve yalnızca yapılandırılan denetim geçerlilik süresi içinde (varsayılan 12 ay) dahil edilir: Overall ≥ 75 düşük, ≥ 50 orta, ≥ 25 yüksek, 25'in altı kritik. Reddedilen bir denetim geçmişte kalır ancak hesaba katılmaz.

| Boyut | Neyi değerlendirir |
|-----------|-------------|
| **Governance** | Güvenlik organizasyonu, iç politikalar, tanımlı sorumluluklar, iç denetimler |
| **Security** | Uygulanan teknik kontroller, zafiyet yönetimi, olay müdahalesi, sertifikalar (ISO 27001, TISAX) |
| **BCP** | İş sürekliliği planları, beyan edilen RTO/RPO, yapılan süreklilik testleri, altyapı yedekliliği |

### NDA ve sözleşmeler

Tedarikçi ayrıntısında, **NDA / Sözleşmeler** bölümünde **+ NDA yükle**'ye tıklayın, dosyayı seçin ve **başlığı** ile varsa **geçerlilik sonunu** girin. Belge, Dokümanlar modülünde tedarikçiye bağlı bir sözleşme olarak arşivlenir; aynı bölümden indirebilir veya onaylanmamışsa onaylayabilirsiniz.

**NDA durumu** sekmesi aktif tedarikçilerin kapsamını özetler: aktif NDA'lı, 90 gün içinde süresi dolacak, süresi dolmuş, taslak veya NDA'sız. Tedarikçiye göre arama yapabilir, NDA durumu ve riske göre filtreleyebilirsiniz.

### Değerlendirme ayarları

**Değerlendirme ayarları** sekmesi hesaplama parametrelerini içerir: iç değerlendirmenin altı parametresinin **ağırlıkları** (toplamı 1,00 olmalıdır), her parametrenin **seviye etiketleri**, orta, yüksek ve kritik sınıflar için ağırlıklı puan **eşikleri**, anketlerin ve üçüncü taraf denetimlerinin **geçerlilik süresi** (ay olarak) ve **NIS2 artışı + kritik yoğunlaşma** seçeneği. Modülü kullananlar bunları görüntüleyebilir; yalnızca Super Admin değiştirebilir.

---

## 14. Eğitim (M15)

Platform kurs **vermez** ve e-öğrenme ya da oltalama simülasyonu platformlarına bağlanmaz: eğitimi **yönetir**. Her tesis için ne yapılacağı planlanır, her oturum **kanıt dosyasıyla** kaydedilir ve personel kapsamı **yalnızca sayılarla** ölçülür. ISO 27001 A.6.3 ve md. 7.2, NIS2 md. 21.2.g, ACN PR.AT ve TISAX ISA 2.1.3'ün istediği budur: bir plan, uygulandığının kanıtı ve ulaşılan kapsam.

**Operasyonlar → Eğitim** bölümüne gidin ve üstten tesisi seçin. Sayfada dört sekme vardır: **Plan**, **Oturumlar**, **Hedef gruplar**, **Kurs kataloğu**.

### Kim ne yapar

- Grupları, planları ve oturumları tesisin Compliance Officer'ı ve Plant Manager'ı ya da Governance'ta tesis veya kuruluş için **CISO ataması** olan kişi **kaydeder**. Görev ataması yoktur: ilk kim ulaşırsa o kaydeder.
- İç Denetçi ve Dış Denetçi de planı, oturumları ve kapsamı **görüntüler**: bunlar sayılar ve kanıt dosyalarıdır, kişisel veri değildir. Kritik roller ve yönetim kurulu için, Governance'ta zaten bulunan katılımcı adlarını da görürler: bunlar NIS2 Md. 20'nin istediği kanıttır.
- Diğer roller yalnızca **Kurs kataloğunu** görür.

### 1. Kurs kataloğu

Her kurs için şunları belirtin:

- **Tür**: kurs, farkındalık kampanyası veya oltalama simülasyonu;
- **Hedef kitle**: personel, kritik roller veya yönetim organı;
- **Geçerlilik (ay)**: oturumun kaç ay sonra tekrarlanması gerektiği (ör. 12 = her yıl); boş = süresi dolmaz;
- **Zorunlu**: personel için zorunlu kurslar kapsama dahil edilir;
- **Kapsam**: kurs tüm tesislerde geçerliyse **kuruluş** (ör. standart hijyen: yalnızca bir kez girersiniz), tesise özgü kurslar için **yalnızca seçili tesisler**. Kuruluş kurslarını kuruluş genelinde kapsamı olanlar yönetir; bir plant manager kendi tesislerinin kurslarını oluşturur ve düzenler. Bir tesisin planında ve oturumlarında kuruluş kursları ile o tesisin kursları sunulur.
- **Kazandırılan yetkinlik** ve **seviye** (yalnızca kritik roller ve yönetim organı, isteğe bağlı): hesabı olan katılımcılar bu yetkinliği yetkinlik profillerinde alır (ISO 27001 md. 7.2). Önerilen adlar rollerin yetkinlik gereksinimlerinden gelir.

Bir planda yer alan veya oturumu kaydedilmiş bir kurs silinemez: **arşivlenir**.

**Oturumların kanıtladığı kontroller.** Kataloğun üstünde tüm kurslar için geçerli tek bir ayar vardır: her hedef kitle için bir oturumun hangi kontrolleri kanıtladığı (ör. personel → ACN PR.AT-01, ISO A.6.3, TISAX ISA-2.1.3; kritik roller → ACN PR.AT-02). Bunu kuruluşu yöneten kişi, kontrolü koda göre arayarak düzenler; diğerleri salt okunur görür. Kontroller kurs kurs seçilmez ve çerçeveler değiştirilmez. Başlangıç değerleri `load_training_evidence_controls` komutuyla yüklenir.

### 2. Hedef gruplar

Tesis için eğitilecek kişi gruplarını **sayılarıyla** girin (ör. "Üretim: 240", "Ofisler: 45"). Çalışan adı veya verisi girilmez. Sayı değiştiğinde güncelleyin: güncelleme tarihi otomatik ayarlanır. 6 aydan uzun süredir doğrulanmayan grup **yeniden doğrulanmalı** olarak işaretlenir, çünkü kapsam bu sayıyla hesaplanır.

### 3. Eğitim planı

1. **Plan** sekmesinde yılı seçin ve **Tesis planını oluştur**'a tıklayın (kuruluşu yöneten kişi, tüm tesisler için geçerli olan **kuruluş planını** da oluşturabilir).
2. **Belge bağla**'ya tıklayın ve **Belgeler** modülünde yönetilen plan belgesini seçin: onay, belge iş akışını izler. Onaylı plan, ISO 27001 A.6.3'ün istediği belgedir.
3. Her faaliyet için **Kalem ekle**'ye tıklayın: kurs, vade ve hedef gruplar.

Her kalem durumunu (**Planlandı**, 30 gün içinde **Vadesi yakın**, **Gecikmiş**, **Yapıldı**), oturum sayısını ve ulaşılan kapsamı gösterir.

**Hatırlatıcılar.** Her sabah, oturumu olmayan ve 30 gün içinde vadesi dolacak ya da gecikmiş kalemler için tesisin **Compliance Officer'ına bir görev** açılır ve eğitimi takip edenlere bildirim gönderilir. Oturumu kaydettiğinizde görev kendiliğinden kapanır. Kalemlerin vadeleri **Activity Schedule** içinde de görünür.

### 4. Oturum kaydetme

1. **Oturumlar** sekmesinde **Oturum kaydet**'e tıklayın.
2. Kursu ve tarihi seçin. Plan kalemi otomatik tanınır; birden fazla varsa seçebilirsiniz.
3. Katılan grupları seçin ve **eğitilen kişi** sayısını girin. Eğitilecek kişi sayısı grupların toplamından önerilir ve düzeltilebilir.
   **Oltalama simülasyonu** için bunun yerine gönderilen e-posta, tıklama ve bildirim sayılarını girin.
4. **Kanıt dosyasını** ekleyin (katılım listesi, e-öğrenme dışa aktarımı, kampanya raporu). Zorunludur: katılımcıların adları yalnızca dosyada bulunur, platform sayıları kaydeder.
5. **Kaydet**'e tıklayın.

Dosyadan, kursun geçerlilik süresi kadar geçerli bir **kanıt** oluşur ve oturumun tesisinde, **yalnızca tesiste uygulanan çerçevelerde**, **kursun hedef kitlesi için belirlenen kontrollere otomatik bağlanır** (ör. ACN PR.AT-01 yalnızca NIS2 tesislerinde, ISA-2.1.3 yalnızca TISAX tesislerinde). Onay mesajı kaç kontrolün bağlandığını gösterir ve uygulanan bir çerçevenin oluşturulmamış veya SoA dışı bırakılmış kontrollerini listeler.

Kanıt dosyası değiştirilemez: yanlışsa oturumu silip yeniden kaydedin. Kanıtı daha önce değerlendirilmiş kontrolleri destekleyen bir oturum silinemez (yalnızca bir superuser silebilir). **Kanıtsız geçmiş kayıt** satırları eski kişi bazlı verilerin taşınmasından gelir: yalnızca sayıları içerir.

### 5. Kritik roller ve yönetim organı

Hedef kitlesi **kritik roller** veya **yönetim organı** olan kurslarda oturum, grupları değil **kimlerin katıldığını** kaydeder:

1. Kayıt formunda, kurs ve tarihten sonra iki liste görünür: tesiste etkin **atama sahipleri** (atamalarıyla birlikte) ve tesisin veya kuruluşun **yönetişim organlarının görevdeki üyeleri** (yönetim kurulu üyeleri YK etiketi taşır). Listeler oturum tarihine bağlıdır: o gün görevde olanları gösterir.
2. Katılanları işaretleyin. Eğitilen kişi sayısı katılımcı sayısıdır (hem üye hem atama sahibi olan kişi bir kez sayılır); eğitilecek kişi sayısı, belirtmezseniz aynı sayıdır.
3. Kanıt dosyasını (imza föyü, sertifikalar) ekleyin ve kaydedin.

Kurs bir **yetkinlik** kazandırıyorsa, hesabı olanlar bunu oturumun kanıtıyla ve aynı geçerlilik süresiyle alır. Zaten sahip olunan daha yüksek bir seviye düşürülmez. Oturumu silerseniz yetkinlik önceki haline döner. Katılımcılar değiştirilemez: hatalıysa oturumu silip yeniden kaydedin.

**Yönetim organı eğitimi (NIS2 Md. 20).** **Oturumlar** sekmesindeki bir panel, tesisin veya kuruluşun yönetim kurulu türündeki organlarının görevdeki üyelerini listeler: geçerli eğitimi olanlar yeşil (geçerlilik tarihiyle), henüz eğitilecek olanlar kırmızı. Hedef kitlesi "yönetim organı" olan ve hâlâ geçerli bir kursa katılım sayılır. Üyeler **Governance → Yönetişim organları** bölümünden yönetilir.

### Sonuçlar nerede görünür

- **Reporting → KPI**, "Eğitim ve farkındalık" bölümü: kurs ve tesis bazında kapsam, plan ilerlemesi, geciken kalemler, son oltalama simülasyonları ve tekrarlanacak eğitimler.
- **Güvenlik hedeflerinin** bağlanabildiği, otomatik hesaplanan **KPI'lar**: zorunlu eğitim kapsamı, plan ilerlemesi, geciken kalemler, oltalamada tıklama ve bildirim oranı, yönetim organı eğitimi.
- **Operasyon Merkezi**: geciken plan kalemlerini işaret eder.
- **Denetim paketi** (Audit Preparation): tesisin planı, kanıt referanslı oturumları, kapsamı, gruplarıyla, kritik rol ve yönetim kurulu oturumlarının katılımcıları ve yönetim kurulu eğitim durumuyla (`board_training.csv`) `07_training` klasörü.

---

## 15. İş Sürekliliği (M16)

[Ekran görüntüsü: İSP planları listesi]

### İSP planı nasıl oluşturulur

1. **Yönetişim → İSP → Yeni plan** bölümüne gidin
2. Doldurun:
   - **Planın adı** (ör. "İSP Planı — B Üretim Hattı — Güney Tesisi")
   - **Kapsam**: plan tarafından kapsanan kritik süreçler (İEA'dan seçin)
   - **Planın sahibi**: bakımdan sorumlu
   - **Hedef RTO** ve **Hedef RPO**: planın garanti etmesi gereken değerler
3. **Taslak Kaydet**'e tıklayın

### İEA'nın RTO/RPO ile bağlantı

İSP planının **Kapsanan süreçler** bölümünde, seçilen her süreç için şunlar arasındaki karşılaştırma gösterilir:

- **İEA'nın talep ettiği RTO**: kritik süreçte beyan edilen maksimum tolerans
- **İSP'nin garanti ettiği RTO**: planın fiilen garantileyebildiği

İSP, İEA'nın talep ettiğinden daha yüksek bir RTO garanti ediyorsa gözden geçirme talep eden turuncu bir uyarı görünür. Sistem kaydı engellemez ancak açık bir gerekçe ister.

### Test türleri

Plan periyodik olarak test edilmelidir. Mevcut test türleri:

| Tür | Açıklama |
|-----|----------|
| **Masa başı** | Kağıt/tartışma simülasyonu. Katılımcılar toplantı odasında, hiçbir gerçek sistem dahil değil |
| **Simülasyon** | Üretimi kesintiye uğratmadan test modunda bazı gerçek sistemlerle kısmi simülasyon |
| **Tam** | Normal üretimi etkilemeden gerçek sistemlerde planın etkinleştirilmesiyle tam test |
| **Tatbikat** | Ekibin gerçek tepki sürelerini test etmek için duyurulmamış alıştırma |

Test kaydetmek için: plan kartından **Yeni test**'e tıklayın, türü, tarihi, katılımcıları ve sonucu seçin.

### Test başarısız olursa ne olur (otomatik PDCA)

Test **Başarısız** veya **Kısmen Geçti** sonucuyla kaydedilirse:

1. PLAN başlangıç aşamasıyla otomatik olarak PDCA döngüsü oluşturulur
2. PDCA, İSP planının sahibine atanır
3. Sahip 30 gün içinde eylem planını doldurmak zorundadır
4. İSP planı, PDCA olumlu sonuçla kapatılana kadar "Güncellenmeli" durumunda kalır

### Plan son tarihleri ve uyarılar

Her İSP planının zorunlu bir gözden geçirme tarihi vardır (tipik olarak yıllık). Tarih yaklaştığında:

- **30 gün önce**: planın sahibine e-posta bildirimi
- **Son tarihte**: plan "Süresi Dolmuş" durumuna geçer ve kırmızı rozetle işaretlenir. Otomatik olarak gözden geçirme görevi oluşturulur
- Süresi dolmuş plan MTPD < 48 saat olan süreçleri kapsıyorsa Tesis Yöneticisi'ne eskalasyon bildirimi gönderilir

---

## 16. Etkinlik Takvimi (Vade Takvimi)

[Ekran görüntüsü: takvim görünümlü vade takvimi]

### Vade takvimi nasıl okunur

**Operasyonlar → Vade Takvimi** bölümüne gidin. Sayfa, seçilen dönemdeki (varsayılan: sonraki 30 gün) tüm son tarihleri tarih sırasıyla gösterir. Her son tarih için şunları görürsünüz:

- Son tarihin **türü** (belge, kanıt, görev, değerlendirme, İSP planı, eğitim kursu vb.)
- Öğenin **adı**
- Son tarih **tarihi**
- Sorumlu **sahip**
- Renkli rozetle **durum** (aşağıya bakın)

Sağ üstteki simgelere tıklayarak liste görünümü ile takvim görünümü arasında geçiş yapabilirsiniz.

### Tür ve döneme göre filtreler

Listenin üzerindeki filtre çubuğunda şunlara göre filtreleme yapabilirsiniz:

- **Tür**: bir veya daha fazla son tarih türü seçin (belgeler, kanıtlar, görevler, değerlendirmeler, İSP, eğitim)
- **Dönem**: bu hafta / bu ay / sonraki 30 gün / sonraki 90 gün / özel aralık
- **Sahip**: son tarihin sorumlusuna göre filtrele
- **Tesis**: tesise göre filtrele (çok tesisli erişiminiz varsa)

### Rozet renkleri

| Renk | Anlam |
|------|-------|
| **Yeşil** | Geçerli — eylem gerekmiyor, son tarih uzakta |
| **Sarı** | Yaklaşıyor — 30 günden az kaldı. Kontrol edin ve eylemi planlayın |
| **Kırmızı** | Süresi dolmuş — tarih geçti. Acil eylem gerekiyor |

### Son tarihten doğrudan öğeye nasıl gidilir

Listede herhangi bir son tarihin adına tıklayarak ilgili öğenin kartını doğrudan açın (ör. sona eren kanıta tıklamak kanıt kartını açar). Menüler aracılığıyla manuel gezinmeye gerek yoktur.

---

## 17. Zorunlu Belgeler

[Ekran görüntüsü: zorunlu belgeler sayfası]

### Belge bir normatif gereksinimiyle nasıl ilişkilendirilir

Zorunlu belgeler, bir normatif çerçeve tarafından açıkça talep edilen belgelerdir (ör. ISO 27001 bir "Bilgi Güvenliği Politikası" talep eder). Mevcut bir belgeyi bir gereksinime bağlamak için:

1. **Uyum → Zorunlu belgeler** bölümüne gidin
2. Listede normatif gereksinimi bulun
3. Gereksinimin yanındaki **Belge Bağla**'ya tıklayın
4. Belge kütüphanesinden (M07) uygun belgeyi arayın ve seçin
5. Kaydedin

Belge henüz mevcut değilse, M07'de oluşturma iş akışını başlatmak için **Belge Oluştur**'a tıklayın.

### Durum ışık sistemi

Listedeki her normatif gereksinim için ışık sistemi, bağlantılı belgenin durumunu gösterir:

| Işık rengi | Anlam |
|-----------|-------|
| **Yeşil** | Belge mevcut, onaylandı ve geçerli (süresi dolmamış) |
| **Sarı** | Belge mevcut ve onaylı ancak 30 gün içinde sona eriyor — gözden geçirme planlayın |
| **Kırmızı** | Belge mevcut ancak süresi dolmuş — acil güncelleme gerekiyor |
| **Gri** | Belge eksik — bu gereksinime bağlı belge yok |

Gri ışık gösteren gereksinimler, çerçevenin uyum KPI'ını olumsuz etkiler.

### Eksik belge nasıl eklenir

Işık gri olduğunda (belge eksik):

1. Gereksinimi tıklayın
2. Oluşturma sihirbazını başlatmak için **Belge Oluştur ve Bağla**'ya tıklayın
3. Sistem, önerilen başlığı, referans çerçeveyi ve belgenin normatif alanlarını otomatik olarak önceden doldurur
4. Eksik alanları tamamlayın (sahip, gözden geçiren, onaylayan) ve dosyayı yükleyin
5. Belge Taslak durumunda başlar ve normal onay iş akışını izler (M07)
6. Onaylandıktan sonra ışık otomatik olarak yeşile döner

---

## 18. E-posta Bildirimleri

### Bildirimler ne zaman gelir

Platform, olaylara göre otomatik e-posta bildirimleri gönderir. Başlıcaları:

| Olay | Alıcılar |
|------|----------|
| Görev atandı | Hedef rolün sahibi |
| Görev sona eriyor (7 gün) | Rol sahibi + sorumlu |
| Görev süresi doldu | Sahip + sorumlu + Uyum Yetkilisi (14 gün sonra) |
| Denetim bulgusu açıldı | Denetlenen alanın sorumlusu |
| Bulgu sona eriyor (30/90/180 gün) | Bulgunun sahibi |
| Yaklaşan denetim (7 gün) | Denetçi + Uyum Yetkilisi |
| NIS2 olayı — T+24s zamanlayıcısı | BGYS Yöneticisi + Uyum Yetkilisi |
| NIS2 olayı — T+72s zamanlayıcısı | BGYS Yöneticisi + Uyum Yetkilisi + Tesis Yöneticisi |
| Skor > 14 olan risk | Risk Yöneticisi + Tesis Yöneticisi |
| Sona eren belge (30 gün) | Belgenin sahibi |
| Süresi dolmuş kanıt | Bağlantılı kontrolün sahibi |
| Zorunlu rol boş | Uyum Yetkilisi + Tesis Yöneticisi |
| Tedarikçi değerlendirmesi sona eriyor (30 gün) | İç sorumlu |

Bazı bildirimler zorunludur ve devre dışı bırakılamaz (ör. NIS2 zamanlayıcıları, kritik görev eskalasyonları, kırmızı riskler).

### Role atanan profile göre nasıl değişir

Bir rol için gönderilen bildirimler, o role atanan **bildirim profiline** (Ayarlar'da yapılandırılmış) bağlıdır. "Temel" profilli bir rol yalnızca zorunlu bildirimleri ve kritik son tarihleri alır. "Tam" profilli bir rol, periyodik özetleri ve referans modüllerdeki bildirimleri de alır.

### Tercihler nasıl yapılandırılır (yalnızca yönetici)

**Ayarlar → Bildirim profilleri** bölümüne gidin:

1. Değiştirilecek profili seçin veya **Yeni profil**'e tıklayın
2. Her olay türü için yapılandırın: etkin / devre dışı, sıklık (anlık / günlük özet / haftalık özet)
3. Profili onu kullanacak rollere atayın
4. Kaydedin

Yapılandırma anında uygulanır. Değişiklikler daha önce gönderilen bildirimler üzerinde geriye dönük etki yapmaz.

---

## 19. Yönetişim (M00)

[Ekran görüntüsü: normatif roller org şeması]

### Normatif rol nasıl atanır

Normatif roller, çerçeveler tarafından talep edilen pozisyonlardır (ör. BGYS Yöneticisi, VKY, Risk Sahibi, Varlık Sahibi). Bir sahip atamak için:

1. **Yönetişim → Org şeması** bölümüne gidin
2. Atanacak rolü bulun (gerekirse çerçeve veya tesis filtresi kullanın)
3. **Sahip Ata**'ya tıklayın
4. Listeden kullanıcıyı seçin
5. Belirleyin:
   - **Başlangıç tarihi**: atamanın ne zaman yürürlüğe gireceği
   - **Bitiş tarihi** (isteğe bağlı): geçici görevler veya planlanan rotasyonlar için kullanışlı
6. **Atamayı Onayla**'ya tıklayın

Atama, denetim izine kaydedilir. Kullanıcı, rolün sorumluluklarını içeren bir e-posta bildirimi alır.

### Bir sahip nasıl değiştirilir (ardıllık)

Bir sahip emekli olursa, görevi değiştirirse veya şirketten ayrılırsa ardıllık mekanizmasını kullanın:

1. Rol kartından **Ardıllığı Yönet**'e tıklayın
2. Yeni sahibi seçin
3. **Geçiş tarihini** belirleyin
4. Sistem örtüşmeyi otomatik olarak yönetir: geçiş tarihine kadar eski sahip aktif kalır, ertesi gün yeni sahip devralır
5. **Ardıllığı Onayla**'ya tıklayın

Eski sahip görев bitiş bildirimi alır. Yeni sahip, sorumlulukların listesiyle görev başlangıç bildirimi alır.

### Rol nasıl sonlandırılır

Bir pozisyon artık gerekli değilse (ör. normatif kapsam değişikliği):

1. Rol kartından **Rolü Sonlandır**'a tıklayın
2. **Gerekçeyi** girin (zorunlu — ör. "2026 TISAX kapsamı gözden geçirmesinden sonra rol kaldırıldı")
3. **Bitiş tarihini** belirleyin
4. Bu role atanmış açık görevler varsa sistem bunların nasıl yönetileceğini sorar (başka bir role yeniden ata veya açık bırak)
5. **Onayla**'ya tıklayın

### Yönetişim organları (yönetim kurulu, komite, üst yönetim)

**Governance → Roller ve organlar** bölümüne gidin ve **Yönetişim organları**'na kaydırın. Bu, yönetim gözden geçirmesini kimin yürüttüğü ve onayladığının kaydıdır (ISO 27001 §5.1, §9.3).

1. **+ Yeni organ**: ad, **tür** (Yönetim kurulu, Güvenlik komitesi, Üst yönetim), **kapsam** (tüm kuruluş veya yönettiği tesisler: birden fazla tüzel kişilik varsa her biri için ayrı bir organ) ve görev tanımı. Yönetim kurulu **NIS2 yönetim organı** olarak işaretlenir (Madde 20: risk yönetimi tedbirlerini onaylar, bunlardan sorumludur ve eğitim almakla yükümlüdür)
2. **+ Üye**: ad soyad, unvan (ör. Genel Müdür), organdaki rolü (başkan, üye, sekreter), görev başlangıcı ve varsa bitişi. **Hesap** isteğe bağlıdır: bağlanması kişinin bu organın gözden geçirmelerini uygulamada onaylamasını sağlar. Yalnızca tutanağa bir ad yazmak için hesap oluşturmaya gerek yoktur
3. Organdan ayrılan kişi silinmez, **Görevi sonlandır** (bitiş tarihi) ile kapatılır: geçmiş tutanaklarda ve **eski üyeler** arasında kalır. **Sil** yalnızca hatalı bir girişi düzeltmek içindir ve üye bir gözden geçirmede yer alıyorsa izin verilmez

Kurallar: aynı anda yalnızca bir görevdeki başkan; aynı hesap, aynı dönemde aynı organın iki üyesine bağlanamaz. Organları Super Admin ve Compliance Officer yönetir, yalnızca kapsamı tamamen kendi kapsamlarında olanları; diğer roller kendi kapsamlarındaki tesisler için görüntüler. Üyeler ve uyarılar (devre dışı hesap, sona eren görev, eksik başkan) **Reporting → Erişim ve sorumluluklar** bölümünde ve denetim paketinde de görünür.


### Sona eren rol uyarıları ve zorunlu boş rol uyarıları

**Sona eren roller**: bir atamanın bitiş tarihi varsa, 30 gün önce sistem Uyum Yetkilisi ve Tesis Yöneticisi'ne yenileme veya ardıllık planlamak için bildirim gönderir.

**Zorunlu boş roller**: bazı roller çerçevede zorunlu olarak işaretlenir (ör. ISO 27001 için BGYS Yöneticisi). Zorunlu bir rolün aktif sahibi yoksa:
- Kontrol panelinde kırmızı başlık görünür
- Uyum KPI'ı ceza alır
- Acil atama görevi oluşturulur

---

## 20. Ayarlar (yalnızca Yönetici)

[Ekran görüntüsü: yönetici ayarları sayfası]

Bu bölüm yalnızca Sistem Yöneticisi veya Süper Yönetici rolüne sahip kullanıcılar tarafından erişilebilir.

### SMTP e-posta yapılandırması

1. **Ayarlar → E-posta → SMTP Yapılandırması** bölümüne gidin
2. Doldurun:
   - **SMTP Ana Bilgisayarı** (ör. smtp.azienda.com)
   - **Port** (tipik olarak STARTTLS için 587 veya SSL için 465)
   - **Kullanıcı** ve **Parola** — parola kaydedilmeden önce AES-256 (FERNET) ile şifrelenir
   - **Varsayılan gönderici** (ör. noreply@grc.azienda.com)
   - **TLS/SSL**: şifreleme türünü seçin
3. **Yapılandırmayı Kaydet**'e tıklayın

### E-posta bağlantısı testi

SMTP'yi yapılandırdıktan sonra:

1. Aynı sayfada **Test E-postası Gönder**'e tıklayın
2. Test için hedef e-posta adresini girin
3. **Gönder**'e tıklayın
4. Alımı kontrol edin. E-posta 2 dakika içinde ulaşmazsa olası SMTP hatasını görmek için **Günlüğü Görüntüle**'ye tıklayın

### Rol başına bildirim profilleri

**Ayarlar → Bildirimler → Profiller** bölümüne gidin:

1. Önceden tanımlanmış profiller şunlardır: Temel, Standart, Tam, Sessiz
2. Özel profil oluşturmak için **Yeni profil**'e tıklayın
3. Her bildirim türü için: etkin/devre dışı ve gönderim sıklığını ayarlayın
4. Profili rollere şu yolla atayın: **Ayarlar → Roller → rol seçin → Bildirim profili**

### Vade politikaları (23 yapılandırılabilir tür)

**Ayarlar → Politika → Son tarihler** bölümüne gidin. Aşağıdakiler dahil 23 tür öğe için önceden uyarı sürelerini ve varsayılan son tarihleri yapılandırabilirsiniz:

- Türe göre kanıtlar (günlükler: 30 gün, taramalar: 90 gün, sertifikalar: 365 gün)
- Türe göre belgeler (politika: 365 gün, prosedür: 730 gün)
- Ciddiyete göre bulgular (Majör NC: 30 gün, Minör NC: 90 gün, Gözlem: 180 gün)
- Tedarikçi değerlendirmeleri (varsayılan 12 ay)
- İSP planları (varsayılan 12 ay)
- Risk gözden geçirme (kırmızı riskler için 90 gün, sarı riskler için 180 gün)

Bu değerlerin değiştirilmesi, gelecekteki tüm öğelerin hesaplamalarını günceller. Mevcut öğeler, oluşturulma anında hesaplanan son tarihleri korur.

---

## Roller ve yapabilecekleriniz

### Uyum Yetkilisi

Kapsamınızdaki tüm tesislerde tüm modüllere tam erişiminiz vardır. Sorumluluklarınız:

- Kontrol kütüphanesini güncel tutmak (M03)
- Belge iş akışını koordine etmek (M07)
- Tüm ekibin görevlerini ve son tarihlerini izlemek (M08)
- NIS2 olaylarını ve ACN bildirimlerini yönetmek (M09)
- Denetim belgelerini hazırlamak (M17)
- Yönetim için raporlar oluşturmak (M18)

### Risk Yöneticisi

Risk modüllerine tam erişiminiz vardır. Sorumluluklarınız:

- BT ve OT risk değerlendirmesini denetlemek (M06)
- İEA ve MTPD/RTO/RPO değerlerini doğrulamak (M05)
- PDCA döngülerini başlatmak ve izlemek (M11)
- Skor > 14 olan riskler için uyarı almak

### Tesis Yöneticisi

Kendi tesisinize erişiminiz vardır. Sorumluluklarınız:

- Yönetim düzeyindeki belgeleri onaylamak (M07)
- Süresi geçmiş kritik görevler için eskalasyon almak
- Risk işlem kararlarını doğrulamak (M06)
- Yönetim gözden geçirmesine katılmak ve onaylamak (M13)

### Tesis Güvenlik Yetkilisi

Kendi tesisinizde operasyonel erişiminiz vardır. Sorumluluklarınız:

- Kontrol durumunu güncellemek (M03)
- Kanıt yüklemek (M07)
- BT ve OT risk değerlendirmelerini doldurmak (M06)
- Olayları açmak ve yönetmek (M09)
- Atanan görevleri tamamlamak (M08)

### Dış Denetçi

Geçici token ile salt okunur erişiminiz vardır. Yapabilecekleriniz:

- Kontrolleri ve durumlarını incelemek (M03)
- Belgeleri ve kanıtları indirmek (M07)
- Denetiminiz için kanıt paketini dışa aktarmak (M17)
- Her eyleminiz denetim izine kaydedilir

Token'ın son tarihi vardır: son tarihi arayüzün üst kısmında bulabilirsiniz. Uzatmaya ihtiyacınız varsa Uyum Yetkilisi ile iletişime geçin.

---

## AI Engine — Yapay Zeka Önerileri (M20)

> AI modülü yalnızca yöneticiniz bu özelliği tesisiniz için etkinleştirmişse kullanılabilir.

### Nasıl çalışır

AI modülü etkin olduğunda, bazı modüllerde — olaylar, varlıklar, belgeler, görevler — **Yapay Zeka Önerisi** kutusu göreceksiniz. Sistem bağlamı analiz eder ve şunları önerir:

- **Önerilen sınıflandırma** (ör. olay ciddiyeti, varlık kritikliği)
- **Metin taslağı** (ör. ACN bildirimi, politika, KNA)
- **Proaktif uyarı** (ör. kayma riski yüksek görev)

### Ne yapmanız gerekir

Yapay zeka önerisi, **açıkça onaylayana** kadar hiçbir etki yaratmaz. Yapabilecekleriniz:

- Öneriyi olduğu gibi **kabul etmek** — **Bu öneriyi kullan**'a tıklayın
- Metni **değiştirip** **Değiştirilmiş sürümü kullan**'a tıklayın — sizin sürümünüz yapay zekanınkinin yerini alır
- Öneriyi **yoksaymak** ve manuel olarak devam etmek — kutu etki yaratmadan kapanır

> Her etkileşim (alınan öneri, benimsenen nihai metin) kararların izlenebilirliğini sağlamak için denetim izine kaydedilir. Yapay zeka hiçbir zaman özerk kararlar almaz.

---

## Raporlama ve dışa aktarma (M18)

### Raporlama kontrol paneli

**Denetim → Raporlama** bölümüne gidin. Üç düzey kontrol paneli bulunur:

- **Operasyonel**: görev durumu, çerçeve ve tesise göre kontroller, son tarihler
- **Risk**: toplu ısı haritası, ilk 10 açık risk
- **Yönetici**: uyum %, PDCA olgunluk trendi, denetim hazırlığı

### Rapor oluşturma

1. Rapor türünü seçin (TISAX boşluk analizi, NIS2 uyumu, ISO 27001 SOA, İEA yönetici özeti)
2. Tesisi ve dönemi seçin
3. Raporun dilini seçin
4. **Oluştur**'a tıklayın — rapor uygun formatta üretilir: özet raporlar için **HTML**, tablo halindeki dışa aktarımlar için **CSV/Excel** (SOA, VDA ISA, NIS2 matrisi)
5. Rapor, **Oluşturulan Raporlar** bölümünde indirme için kullanılabilir

Oluşturulan tüm raporlar denetim izine kaydedilir.

---

## Operasyon Merkezi (M21)

[Ekran: önceliklendirilmiş insight'lar ve postür içeren cockpit]

Operasyon Merkezi, tüm modüllerden gelen sinyalleri önceliklendirilmiş **insight**'lara toplayan ve genel **güvenlik postürünü** trendiyle birlikte gösteren panodur. Günlük çalışma için tasarlanmıştır: modül modül açmadan *önce neye bakmanız gerektiğini* söyler.

### Insight nedir

Her insight, **advisor**'lar (kontrolleri, riskleri, olayları, son tarihleri, denetimleri vb. izleyen kurallar) tarafından bir öncelikle üretilen bir sinyaldir. Her insight için bir özet, kaynak modül ve önerilen eylem görürsünüz.

### Bir insight'ı yönetmek (alarm yorgunluğuna karşı)

Insight kartından şunları yapabilirsiniz:

- **Kabul et**: insight'ı bir tarihe kadar üstlenirsiniz — o zamana kadar yeniden görünmez
- **Ertele (snooze)**: isteğe bağlı notla birlikte bir tarihe kadar duraklatırsınız
- **Yeniden aç**: daha önce kabul edilen veya ertelenen bir insight'ı geri getirirsiniz

Bu eylemler aynı uyarıların sonsuza dek tekrarlanmasını önler ve audit trail'e kaydedilir.

### AI açıklaması ve asistan

AI modülü (M20) etkinse, insight'ın **AI açıklamasını** isteyebilir (veriler gönderilmeden önce anonimleştirilir) ve bağlam soruları için **operasyon asistanını** kullanabilirsiniz. AI asla tek başına değişiklik uygulamaz: her zaman human-in-the-loop ilkesi geçerlidir.

### Postür ve trend

Sayfa, genel bir postür göstergesini ve zaman içindeki değişimini (posture trend) gösterir; durumun iyileşip iyileşmediğini anlamak için kullanışlıdır.

### Kimler erişebilir

Operasyon Merkezi, yönetişim ve denetim rolleriyle sınırlıdır: Super Admin, Compliance Officer, Risk Manager, Internal Auditor ve Tesis Yöneticisi. Dış Denetçi erişemez.

---

## OSINT Monitor

[Ekran: OSINT maruziyet panosu]

OSINT Monitor, kuruluşunuzun **dış maruziyetini** — alan adlarınızı ve tedarikçilerinizin web sitelerini — kamuya açık kaynaklar (Open Source Intelligence) kullanarak izleyen yatay modüldür. Diğer modüllerin aksine tek bir tesise bağlı değildir: **kuruluş** düzeyinde çalışır.

### Neyi izler

- **Ana alan adı** ve yapılandırılmış olası **ek alan adları**
- **Tedarikçi web siteleri** (M14), *supplier* tipi OSINT varlıkları olarak
- Her varlık için: alt alan adları, SSL sertifikaları, DNS/WHOIS kayıtları ve — anahtarlar yapılandırılmışsa — itibar, ihlaller, kara listeler ve threat intelligence

### Taramalar ve zenginleştiriciler

Temel taramalar (SSL, DNS, WHOIS) **ücretsiz ve her zaman aktiftir**. Ek zenginleştirmeler (HaveIBeenPwned, VirusTotal, AbuseIPDB, Google Safe Browsing, AlienVault OTX, abuse.ch), ilgili **API anahtarlarını** **OSINT → Ayarlar**'a girerek etkinleştirilir (tümü isteğe bağlı; kayıt bağlantıları için ayarlar sayfasındaki `?` düğmesini kullanın). Anahtarlar şifrelenir ve asla açık metin olarak gösterilmez.

### Uyarılar ve otomatik eylemler

Bir tarama önemli bir sorun tespit ettiğinde:

- **Alan adlarınızdan birindeki kritik bir uyarı** otomatik olarak bir **olay** (M09) oluşturabilir
- **Bir tedarikçiye ilişkin uyarı**, iç referans için bir **doğrulama görevi** (M08) oluşturabilir
- Bulgular remediasyona yönlendirilebilir ve gerekirse **yükseltilebilir**

Dış maruziyet bildirimleri **yalnızca iç personele** yöneliktir (asla Dış Denetçiye).

### AI analizi

AI modülü (M20) etkinse, saldırı yüzeyi analizi, NIS2 brifingleri ve yönetim kurulu raporları isteyebilirsiniz: veriler AI sağlayıcısına gönderilmeden önce **anonimleştirilir**.

### Kimler erişebilir

OSINT Monitor, Super Admin, CISO ve Compliance Officer ile sınırlıdır.

---

## Ek: Sık sorulan sorular

**Çerçevemde olması gereken bir kontrolü bulamıyorum.**
Üstteki seçicide doğru tesisi seçtiğinizi doğrulayın. Çerçeve o tesis için etkinse ancak kontrol görünmüyorsa Uyum Yetkilisi ile iletişime geçin — çerçeve etkinleştirilirken oluşturulmamış olabilir.

**Kanıt yükledim ancak kontrol hâlâ "boşluk" gösteriyor.**
Kanıtın doğru kontrole bağlandığını (kanıt kartı → "Kapsanan kontroller" bölümü) ve son tarihinin geçmediğini doğrulayın.

**NIS2 zamanlayıcısı başladı ancak olay gerçekten bir NIS2 olayı değil.**
BGYS Yöneticisiyseniz olay kartını açın ve gerekçeyi girerek **NIS2 yükümlülüğünü hariç tutun**: son tarihler düşer ve karar denetim izine kaydedilir. Olay 'değerlendirilecek' olarak kaldığı sürece, 30 dakika sonra sınıflandırma için bir hatırlatma uyarısı alırsınız.

**Bir görevi tamamladım ancak açık olarak görünmeye devam ediyor.**
Bazı görevler, kaynak modülündeki eylem tamamlandığında otomatik olarak kapanır. Görev manüelse, görev kartından açıkça kapatmanız gerekir → **Tamamlandı Olarak İşaretle**.

**Onayladığım bir belge artık "gözden geçirmede" görünüyor.**
Olağanüstü bir gözden geçirme tetikleyicisi etkinleştirildi — muhtemelen bir olay, denetim bulgusu veya düzenleyici değişiklikle bağlantılı. Nedeni anlamak için belge kartındaki notları kontrol edin.

**Bir kontrolü N/A olarak ayarlayamıyorum.**
TISAX L3 kontrolleri için N/A durumu en az iki rolün imzasını (çift kilit) gerektirir. İlk onaylayan sizseniz kontrol ikinci imzayı bekler. Tek sahibiyseniz ortak imza için BGYS Yöneticisi ile iletişime geçin.

**Yapay zeka önerisi artık görünmüyor.**
AI modülü, yönetici tarafından tesisiniz için devre dışı bırakılmış olabilir veya belirli özellik etkin olmayabilir. Uyum Yetkilisi veya Sistem Yöneticisi ile iletişime geçin.

**Bir denetimi yanlışlıkla iptal ettim. Geri yükleyebilir miyim?**
Hayır, iptal geri alınamaz. Ancak aynı çeyrek için yeni bir denetim oluşturabilir ve kaybedilen bulguları yeniden oluşturabilirsiniz. İptal edilen bulguları arşivde görüntüleyip bilgileri geri almak için Uyum Yetkilisi ile iletişime geçin.

**Risk skorumuz herhangi bir şey yapmadan değişti.**
Kalıntı skor, bağlantılı kontrollerin durumu değiştiğinde otomatik olarak yeniden hesaplanır. Bir kanıtın süresi dolduysa kontrol "kısmi"ye döner ve bu kalıntı riski artırabilir. Riske bağlı kontrolleri kontrol edin ve kanıtları güncelleyin.

**E-posta bildirimleri almıyorum.**
Önce spam klasörünü kontrol edin. E-postalar hiç gelmiyorsa SMTP yapılandırmasını ve rolünüze atanan bildirim profilini doğrulamak için sistem yöneticisiyle iletişime geçin.

**Bir varlık veya belge üzerindeki değişiklik geçmişini nasıl görebilirim?**
Her kartın altında **Denetim izi** veya **Değişiklik geçmişi** bölümü bulunur. Tarih, kullanıcı ve değişiklik ayrıntısıyla kaydedilen tüm eylemleri görmek için tıklayın.

**Denetim programı "Güncellenmeli" durumunu gösteriyor. Ne yapmalıyım?**
"Güncellenmeli" durumu, programın oluşturulduğunu ancak bazı bilgilerin (ör. bir çeyreğe denetçi atanmamış, tarihler eksik) program onaylanmadan önce tamamlanması gerektiğini gösterir. Programı açın ve sarı renkle vurgulanan alanları arayın.

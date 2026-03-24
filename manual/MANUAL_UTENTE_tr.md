# Kullanıcı Kılavuzu — GRC Platform

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

Seçilen dil tüm arayüze uygulanır. Oluşturulan PDF raporlar, oluşturma anında etkin olan dili kullanır.

### Yan menü: ana bölümler ve içerikleri

[Ekran görüntüsü: genişletilmiş menüyle kenar çubuğu]

Sol taraftaki yan menü, yalnızca rolünüze göre erişilebilen bölümleri gösterir. Ana öğeler şunlardır:

| Öğe | İçeriği |
|-----|---------|
| **Kontrol Paneli** | Uyum KPI'ları, risk ısı haritası, yaklaşan son tarihler, uyarılar |
| **Uyum** | Kontrol kütüphanesi (M03), belgeler (M07), kanıtlar |
| **Risk** | BT/OT varlıkları (M04), İEA (M05), Risk Değerlendirmesi (M06) |
| **Operasyonlar** | Olaylar (M09), Görevler/Takvim (M08), PDCA (M11) |
| **Yönetişim** | Org şeması/Roller (M00), Alınan Dersler (M12), Yönetim Gözden Geçirmesi (M13), Tedarikçiler (M14), Eğitim (M15), İSP (M16) |
| **Denetim** | Denetim Hazırlığı (M17), Raporlama (M18) |
| **Bildirimler** | E-posta bildirimleri, tercihler |
| **Ayarlar** | Yalnızca yönetici rolleri için — SMTP, politika, bildirim profilleri |

Bir bölümü genişletmek veya daraltmak için öğenin başlığına tıklayın. Menü durumu oturumlar arasında hatırlanır.

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
| **N/A** | Kontrol tesisinizin bağlamında geçerli değil. Zorunlu not gerektirir. TISAX L3 için iki rolün imzasını gerektirir ve 12 ay sonra sona erer |

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

### ISO 27001 SOA, VDA ISA TISAX, NIS2 Matriksi nasıl indirilir

[Ekran görüntüsü: uyum dışa aktarma sayfası]

1. **Uyum → Kontrol kütüphanesi** bölümüne gidin
2. Sayfanın sağ üstündeki **Dışa Aktar** düğmesine (indirme simgesi) tıklayın
3. Dışa aktarma türünü seçin:
   - **ISO 27001 SOA** — tüm Ek A kontrolleri ve ilgili durumlarla birlikte Uygulanabilirlik Beyanı
   - **VDA ISA TISAX** — VDA Bilgi Güvenliği Değerlendirme Tablosu
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

BGYS Yöneticisi, olay oluşturulduktan sonra **NIS2 yükümlülüğünü hariç tut** düğmesi aracılığıyla bildirim yükümlülüğünü onaylamak veya dışlamak için 30 dakika süresine sahiptir. 30 dakika içinde yanıt vermezse sistem bildirimin gerekli olduğunu varsayar ve zamanlayıcılar aktif kalır.

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
| **DO → CHECK** | Gerçekleştirilen eylemi belgeleyen eklenmiş kanıt (zorunlu dosya) |
| **CHECK → ACT** | Doğrulama sonucu (açıklayıcı metin) + Seçilen sonuç: **tamam** / **kısmi** / **başarısız** |
| **ACT → KAPALI** | Standartlaştırma: benimsenen çözümün çoğaltılabilir olması için belgelenmesi (en az 20 karakter) |

### CHECK sonucu = başarısız ise ne olur

CHECK aşamasında sonuç **başarısız** ise (çözüm işe yaramadı):

1. Döngü ACT'e ilerlemez, otomatik olarak **DO** aşamasına döner
2. Döngünün günlüğüne başarısızlık tarihi kaydedilir
3. DO aşaması için yeni bir eylem planı doldurulması gerekir
4. Kaç iterasyonun gerektiğini izlemek için DO döngüsü sayacı artırılır

DO-CHECK iterasyonlarının sayısında sınır yoktur, ancak sistem 3'ten fazla iterasyona sahip döngüleri Uyum Yetkilisi'ne bildirir.

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

### Gözden geçirme nasıl oluşturulur

1. **Yönetişim → Yönetim Gözden Geçirmesi → Yeni** bölümüne gidin
2. Doldurun:
   - **Yıl ve numara**: ör. "2026 — Rev. 1/2026"
   - **Planlanan tarih**
   - **Katılımcılar**: dahil edilen rolleri seçin (Tesis Yöneticisi, BGYS Yöneticisi, Risk Yöneticisi, UY)
3. Sistem, zorunlu gündem maddelerini otomatik olarak ekler (aşağıya bakın)
4. **Gündem Maddesi Ekle** aracılığıyla ek maddeler ekleyebilirsiniz
5. **Taslak Kaydet**'e tıklayın

### Zorunlu gündem maddeleri (ISO 27001 Madde 9.3)

ISO 27001 Madde 9.3 standardı, yönetim gözden geçirmesinin zorunlu olarak bir dizi madde içermesini şart koşar. Sistem bunları taslağa otomatik olarak ekler:

- Önceki gözden geçirmelerdeki eylemlerin durumu
- BGYS için geçerli iç ve dış bağlamdaki değişiklikler
- BGYS performansına ilişkin geri bildirim (NC'ler, denetimler, izleme, ölçümler)
- İlgili tarafların geri bildirimi
- Risk değerlendirmesinin sonuçları ve işlem planının durumu
- Sürekli iyileştirme fırsatları

Bu maddelerden herhangi biri en az bir yorum veya kaydedilmiş karar içermiyorsa gözden geçirme kapatılamaz.

### Kararlar nasıl kaydedilir

Gündemdeki her madde için:

1. Maddeyi genişletmek için tıklayın
2. **Tartışma özetini** girin
3. Yönetim tarafından onaylanan eylemleri kaydetmek için **Karar Ekle**'ye tıklayın
4. Her karar için: sorumlu, yapılacak eylem, son tarih

Sorumlusu ve son tarihi olan kararlar otomatik olarak M08'de görevlere ve yapısal nitelikteyse M11'de PDCA döngülerine dönüştürülür.

### Kapanış ve onay

1. Tüm zorunlu maddeleri tamamladıktan sonra **Onay İçin Gönder**'e tıklayın
2. Tesis Yöneticisi bir onay görevi alır
3. Onaylandıktan sonra gözden geçirme değiştirilemez hale gelir
4. Gözden geçirmenin **Oluşturulan Belgeler** bölümünde kullanılabilen karma ve zaman damgasıyla imzalanmış PDF tutanağı otomatik olarak oluşturulur

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
1. Denetim sayfasının sağ üstündeki **Rapor** düğmesine (PDF simgesi) tıklayın
2. Raporun dilini seçin
3. Sistem bir PDF oluşturur: kapsam özeti, türe göre bulgu listesi, kapanış durumu, önceki denetime kıyasla trend
4. PDF, indirme için hemen kullanılabilir

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

### Tedarikçi nasıl kaydedilir

1. **Yönetişim → Tedarikçiler → Yeni tedarikçi** bölümüne gidin
2. Doldurun:
   - **Ticari unvan** ve **Vergi kimlik numarası**
   - **Kategori**: BT, OT, Profesyonel Hizmetler, Lojistik, diğer
   - **Kritiklik**: operasyonel süreklilik için ne kadar kritik (1–5)
   - **İç sorumlu**: tedarikçi yönetiminden sorumlu rolü seçin
   - **Tedarikçi sorumlusu**: tedarikçideki ilgili kişinin adı ve e-postası
   - **Veri işleme**: tedarikçi kişisel veri işliyorsa işaretleyin (ek GDPR yükümlülükleri doğurur)
3. **Kaydet**'e tıklayın

### Değerlendirme: planlandı → devam ediyor → tamamlandı → onaylandı/reddedildi

Her kritik tedarikçi periyodik değerlendirmelerle değerlendirilmelidir. Akış şöyledir:

1. **Planlandı**: değerlendirme hedef tarihle oluşturulur. İç sorumlu bir görev alır
2. **Devam Ediyor**: değerlendirme başlatılır. Tedarikçi (e-posta veya geçici erişim aracılığıyla) doldurulacak anketi alır
3. **Tamamlandı**: tedarikçi tüm soruları yanıtladı. İç sorumlu anketi inceleme için alır
4. **Onaylandı** veya **Reddedildi**: Uyum Yetkilisi veya Risk Yöneticisi nihai yargıyı verir (aşağıya bakın)

### Yönetişim, güvenlik, İSP skoru

Değerlendirme anketi, tedarikçiyi 3 boyutta değerlendirir:

| Boyut | Ne değerlendirir |
|-------|-----------------|
| **Yönetişim** | Güvenlik için organizasyon yapısı, iç politikalar, tanımlanmış sorumluluklar, iç denetimler |
| **Güvenlik** | Uygulanan teknik kontroller, güvenlik açığı yönetimi, olay müdahalesi, sertifikalar (ISO 27001, TISAX) |
| **İSP** | Operasyonel süreklilik planları, beyan edilen RTO/RPO, gerçekleştirilen süreklilik testleri, altyapı fazlalıkları |

Her boyut 0-100 arası skor üretir. Genel skor, üç boyutun ağırlıklı ortalamasıdır.

### Zorunlu notlarla onay ve red

**Onay:**
1. Tamamlanmış değerlendirme kartından **Tedarikçiyi Onayla**'ya tıklayın
2. **Onay notlarını** girin (zorunlu — ör. "ISO 27001 sertifikalı tedarikçi, yeterli puan. Sonraki gözden geçirme 12 ay sonra")
3. **Onay son tarihini** belirleyin (tipik olarak 12 ay)
4. **Onayı Onayla**'ya tıklayın

**Red:**
1. Tamamlanmış değerlendirme kartından **Tedarikçiyi Reddet**'e tıklayın
2. **Red notlarını** girin (zorunlu — kararı gerekçelendiren ayrıntılı gerekçe olmalıdır)
3. **Reddi Onayla**'ya tıklayın

Red, iç sorumluda geçişi yönetmek için görev oluşturur (tedarikçi değişimi veya iyileştirme planı).

---

## 14. Eğitim (M15)

[Ekran görüntüsü: kişisel eğitim planı]

### Kendi zorunlu kurslarınızı nasıl görebilirsiniz

1. **Yönetişim → Eğitim → Planım** bölümüne gidin
2. Rolünüz ve tesisiniz için zorunlu kursların listesini şunlarla birlikte bulursunuz:
   - Kursun adı
   - Durum: Tamamlanmamış / Devam Ediyor / Tamamlandı / Süresi Dolmuş
   - Son tarih (veya zaten yapıldıysa tamamlanma tarihi)
   - Tür: çevrimiçi (KnowBe4), yüz yüze, belgesel

### Tamamlama ve son tarihler

- Çevrimiçi kurslarda **Kursu Başlat**'a tıklayarak doğrudan KnowBe4'teki modülü açın
- Tamamlamalar her gece otomatik olarak eşitlenir — KnowBe4'te bir kursu tamamladıysanız ve GRC Platform'da henüz tamamlandı olarak görünmüyorsa ertesi güne kadar bekleyin veya Uyum Yetkilisi ile iletişime geçin
- Süresi dolmuş kurs (tamamlandı ancak periyodik olarak yenilenmesi gerekiyor) kırmızı rozetle görünür ve yenileme görevi oluşturur

### Yetkinlik boşluğu analizi

**Yönetişim → Eğitim → Boşluk analizi** bölümüne gidin. Sayfada şunlar gösterilir:

- Her rol ve tesis için öngörülen yetkinlik gereksinimleri
- Fiilen sertifikalanmış yetkinlikler (tamamlanan kurslar, yüklenen belgeler)
- Vurgulanan boşluklar: gerekli ancak henüz tamamlanan hiçbir kursla karşılanmamış yetkinlikler

Uyum Yetkilisi, eğitim oturumlarını planlamak ve öncelikli boşlukları kapatmak için bu görünümü kullanabilir.

### KnowBe4 eşitleme (yalnızca yönetici)

**Ayarlar → Entegrasyonlar → KnowBe4** bölümüne gidin:

1. KnowBe4 API anahtarını yapılandırın
2. Tamamlamaların anlık eşitlemesini zorlamak için **Şimdi Eşitle**'ye tıklayın
3. Olası hataları belirlemek için son eşitleme günlüğünü doğrulayın

Otomatik eşitleme her gece 02:00'de gerçekleşir.

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

### PDF raporu oluşturma

1. Rapor türünü seçin (TISAX boşluk analizi, NIS2 uyumu, ISO 27001 SOA, İEA yönetici özeti)
2. Tesisi ve dönemi seçin
3. Raporun dilini seçin
4. **Oluştur**'a tıklayın — PDF zaman damgası ve karmayla imzalanır
5. Rapor, **Oluşturulan Raporlar** bölümünde indirme için kullanılabilir

Oluşturulan tüm raporlar denetim izine kaydedilir.

---

## Ek: Sık sorulan sorular

**Çerçevemde olması gereken bir kontrolü bulamıyorum.**
Üstteki seçicide doğru tesisi seçtiğinizi doğrulayın. Çerçeve o tesis için etkinse ancak kontrol görünmüyorsa Uyum Yetkilisi ile iletişime geçin — çerçeve etkinleştirilirken oluşturulmamış olabilir.

**Kanıt yükledim ancak kontrol hâlâ "boşluk" gösteriyor.**
Kanıtın doğru kontrole bağlandığını (kanıt kartı → "Kapsanan kontroller" bölümü) ve son tarihinin geçmediğini doğrulayın.

**NIS2 zamanlayıcısı başladı ancak olay gerçekten bir NIS2 olayı değil.**
BGYS Yöneticisi bildirim yükümlülüğünü dışlamak için 30 dakika süresine sahiptir. BGYS Yöneticisiyseniz olay kartını açın ve gerekçeyi girerek **NIS2 yükümlülüğünü hariç tut**'a tıklayın. Zamanlayıcılar durur ve karar denetim izine kaydedilir.

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

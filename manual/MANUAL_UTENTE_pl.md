# Podręcznik Użytkownika — GRC Platform

> Przewodnik dla użytkowników końcowych: Compliance Officer, Risk Manager, Plant Manager, Plant Security Officer, Audytor Zewnętrzny.

---

## Spis treści

- [1. Logowanie i nawigacja](#1-logowanie-i-nawigacja)
- [2. Pulpit nawigacyjny](#2-pulpit-nawigacyjny)
- [3. Zarządzanie kontrolami (M03)](#3-zarządzanie-kontrolami-m03)
- [4. Aktywa IT i OT (M04)](#4-aktywa-it-i-ot-m04)
- [5. Analiza wpływu na działalność (M05)](#5-analiza-wpływu-na-działalność-m05)
- [6. Ocena ryzyka (M06)](#6-ocena-ryzyka-m06)
- [7. Dokumenty i dowody (M07)](#7-dokumenty-i-dowody-m07)
- [8. Zarządzanie incydentami (M09)](#8-zarządzanie-incydentami-m09)
- [9. PDCA (M11)](#9-pdca-m11)
- [10. Lekcje (M12)](#10-lekcje-m12)
- [11. Przegląd Zarządu (M13)](#11-przegląd-zarządu-m13)
- [12. Przygotowanie do audytu (M17)](#12-przygotowanie-do-audytu-m17)
- [13. Dostawcy (M14)](#13-dostawcy-m14)
- [14. Szkolenia (M15)](#14-szkolenia-m15)
- [15. Ciągłość działania (M16)](#15-ciągłość-działania-m16)
- [16. Harmonogram działań (Terminarz)](#16-harmonogram-działań-terminarz)
- [17. Dokumenty obowiązkowe](#17-dokumenty-obowiązkowe)
- [18. Powiadomienia e-mail](#18-powiadomienia-e-mail)
- [19. Ład organizacyjny (M00)](#19-ład-organizacyjny-m00)
- [20. Ustawienia (tylko Administrator)](#20-ustawienia-tylko-administrator)
- [Role i uprawnienia](#role-i-uprawnienia)
- [AI Engine — sugestie SI (M20)](#ai-engine--sugestie-si-m20)
- [Raportowanie i eksport (M18)](#raportowanie-i-eksport-m18)
- [Załącznik: Często zadawane pytania](#załącznik-często-zadawane-pytania)

---

## 1. Logowanie i nawigacja

### Logowanie e-mailem i hasłem

[Zrzut ekranu: strona logowania]

1. Otwórz przeglądarkę i przejdź na `https://grc.azienda.com`
2. Wpisz swój **służbowy adres e-mail** w pierwszym polu
3. Wpisz **hasło** w drugim polu (minimum 12 znaków)
4. Kliknij **Zaloguj się**
5. Przy pierwszym logowaniu zostaniesz poproszony o zmianę tymczasowego hasła otrzymanego e-mailem

Jeśli korzystasz z firmowego SSO, kliknij **Zaloguj się kontem firmowym** i wpisz dane logowania swojego konta domenowego.

> Sesja pozostaje aktywna przez 30 minut bezczynności. Po upływie tego czasu zostaniesz poproszony o ponowne wpisanie hasła. Token sesji odnawiany jest automatycznie podczas aktywnego użytkowania.

Aby zresetować hasło: na stronie logowania kliknij **Zapomniałem hasła** i wpisz swój adres e-mail. Otrzymasz link ważny przez 15 minut.

### Wybór zakładu (plant) w lewym górnym rogu

[Zrzut ekranu: selektor plant na pasku górnym]

Zaraz po zalogowaniu, w lewym górnym rogu obok logo, znajduje się **selektor plant**. Jeśli masz dostęp do kilku zakładów lub jednostek biznesowych:

1. Kliknij nazwę bieżącego plant (lub „Wybierz plant" przy pierwszym logowaniu)
2. Pojawi się rozwijane menu ze wszystkimi plant w Twoim zakresie
3. Kliknij plant, który chcesz wyświetlić — strona odświeży się natychmiast

Pozycja **Wszystkie plant** wyświetla zagregowany widok wszystkich zakładów. Ta opcja dostępna jest tylko dla Compliance Officer i ról z dostępem wielozakładowym.

Wszystkie operacje (tworzenie aktywów, otwieranie incydentów, ocena kontroli) są powiązane z plant wybranym w danym momencie.

### Zmiana języka (IT/EN) w prawym górnym rogu

[Zrzut ekranu: menu języka na pasku górnym]

1. Kliknij ikonę języka (lub skrót bieżącego języka) w prawym górnym rogu
2. Wybierz żądany język: **Italiano**, **English**, **Français**, **Polski**, **Türkçe**
3. Interfejs aktualizuje się natychmiast bez przeładowania strony

Wybrany język obowiązuje w całym interfejsie. Raporty PDF generowane są w języku aktywnym w momencie generowania.

### Menu boczne: główne sekcje i ich zawartość

[Zrzut ekranu: pasek boczny z rozwiniętym menu]

Menu boczne po lewej stronie wyświetla tylko sekcje dostępne zgodnie z Twoją rolą. Główne pozycje:

| Pozycja | Zawartość |
|---------|-----------|
| **Pulpit** | KPI compliance, mapa ciepła ryzyk, zbliżające się terminy, alerty |
| **Compliance** | Biblioteka kontroli (M03), dokumenty (M07), dowody |
| **Ryzyko** | Aktywa IT/OT (M04), BIA (M05), Ocena ryzyka (M06) |
| **Operacje** | Incydenty (M09), Zadania/Terminarz (M08), PDCA (M11) |
| **Ład organizacyjny** | Schemat organizacyjny/Role (M00), Lekcje (M12), Przegląd Zarządu (M13), Dostawcy (M14), Szkolenia (M15), BCP (M16) |
| **Audyt** | Przygotowanie do audytu (M17), Raportowanie (M18) |
| **Powiadomienia** | Powiadomienia e-mail, preferencje |
| **Ustawienia** | Tylko dla ról administracyjnych — SMTP, polityki, profile powiadomień |

Aby rozwinąć lub zwinąć sekcję, kliknij jej tytuł. Stan menu jest zapamiętywany między sesjami.

### Ikona ? na każdej stronie — pomoc kontekstowa

[Zrzut ekranu: przycisk ? obok tytułu strony]

Na niemal wszystkich stronach operacyjnych znajdziesz mały przycisk **`?`** przy tytule modułu. Po kliknięciu otworzy się panel boczny zawierający:

- Krótkie wyjaśnienie działania modułu
- Typowe kroki do wykonania
- Powiązania z innymi modułami (np. jakie zadania lub PDCA są tworzone automatycznie)
- Listę zalecanych warunków wstępnych („Przed rozpoczęciem")

Korzystaj z panelu pomocy, gdy pracujesz z rzadziej używanymi modułami lub gdy wprowadzasz system nowym pracownikom.

### Przyciski Podręcznik Użytkownika i Podręcznik Techniczny na dolnym pasku

[Zrzut ekranu: dolny pasek z przyciskami podręcznika]

Na dole każdej strony, w dolnym pasku, znajdują się dwa stałe przyciski:

- **Podręcznik Użytkownika** (ikona książki): otwiera ten podręcznik w nowej karcie
- **Podręcznik Techniczny** (ikona klucza): otwiera podręcznik techniczny ze szczegółami architektonicznymi, widoczny tylko dla profili z dostępem administracyjnym

Oba przyciski są zawsze widoczne niezależnie od modułu, w którym się znajdujesz.

---

## 2. Pulpit nawigacyjny

[Zrzut ekranu: główny pulpit nawigacyjny]

Pulpit nawigacyjny to pierwsza strona wyświetlana po zalogowaniu. Zawartość dostosowana jest do Twojej roli i wybranego plant.

### Co pokazują główne KPI

Na górze pulpitu znajdują się 4 kafelki z głównymi KPI:

| KPI | Co mierzy |
|-----|-----------|
| **Compliance %** | Procent kontroli w stanie „zgodny" lub „częściowy z ważnym dowodem" w stosunku do wszystkich aktywnych kontroli dla wybranego frameworku |
| **Otwarte ryzyka** | Liczba ocen ryzyka ze statusem „otwarte" (nieakceptowane i niezamknięte). Liczba ta zawiera zliczenie ryzyk krytycznych (wynik > 14) w kolorze czerwonym |
| **Incydenty** | Otwarte incydenty w wybranym plant. Liczby czerwone oznaczają incydenty z aktywnymi timerami NIS2 |
| **Przeterminowane zadania** | Zadania przypisane do Twojej roli (lub całej organizacji, jeśli jesteś CO) z przekroczoną datą realizacji |

### Jak interpretować kolory

Platforma stosuje spójną konwencję kolorystyczną w całym interfejsie:

- **Zielony**: wszystko w porządku — zgodny, ukończony, ważny, w terminie
- **Żółty**: wymagana uwaga — częściowy, wygasający w ciągu 30 dni, w toku
- **Czerwony**: krytyczny — luka, przeterminowany, wysokie ryzyko (wynik > 14), timer NIS2 wygasający
- **Szary**: nieoceniony, N/A, zarchiwizowany
- **Pomarańczowy**: alert lub ostrzeżenie — wymaga uwagi, ale jeszcze nie jest krytyczny

Te kolory stosowane są dla odznak statusu, pasków postępu, wskaźników na mapie ciepła i ikon na pasku bocznym.

### Widget nadchodzących terminów

[Zrzut ekranu: widget terminów na pulpicie]

Widget „Nadchodzące terminy" wyświetla pierwsze 10 terminów w ciągu następnych 30 dni. Dla każdego terminu widać:

- Typ (dokument, dowód, zadanie, ocena dostawcy itp.)
- Nazwę elementu
- Datę terminu z kolorem żółtym (< 30 dni) lub czerwonym (< 7 dni)

Kliknięcie terminu przenosi bezpośrednio na stronę danego elementu.

### Alerty o wakatach ról

Jeśli obowiązkowe role normatywne nie mają przypisanego właściciela (np. CISO niepowołany, wakat DPO), na pulpicie pojawia się pomarańczowy baner „Wakaty ról" z licznikiem i linkiem do strony ładu organizacyjnego (M00). Te alerty negatywnie wpływają na KPI compliance.

### Jak przejść bezpośrednio do elementu z pulpitu

Każdy interaktywny element na pulpicie jest klikalny:

- Kliknij przeterminowane zadanie, aby otworzyć kartę zadania
- Kliknij kwadrant mapy ciepła, aby zobaczyć ryzyka w tej strefie
- Kliknij pasek compliance, aby przejść do biblioteki kontroli przefiltrowanej według danego frameworku
- Kliknij incydent, aby otworzyć kartę incydentu

---

## 3. Zarządzanie kontrolami (M03)

[Zrzut ekranu: biblioteka kontroli]

### Jak ocenić kontrolę

1. Przejdź do **Compliance → Biblioteka kontroli**
2. Użyj filtrów (framework, domena, status, plant), aby znaleźć interesującą Cię kontrolę
3. Kliknij nazwę kontroli, aby otworzyć kartę
4. W polu **Status** kliknij, aby otworzyć selektor i wybierz odpowiedni status
5. Dodaj notatkę kontekstową w polu **Notatki oceny** (obowiązkowe dla Luki i N/A)
6. Podłącz dowód za pomocą przycisku **Dołącz dowód**
7. Kliknij **Zapisz**

### Różnica między Zgodny, Częściowy, Luka, N/A

| Status | Kiedy stosować |
|--------|---------------|
| **Zgodny** | Kontrola jest w pełni spełniona. Posiadasz ważny, nieprzeterminowany dowód to potwierdzający |
| **Częściowy** | Kontrola jest wdrożona tylko częściowo. Istnieje plan jej ukończenia, ale nie wszystkie wymagania są jeszcze spełnione |
| **Luka** | Kontrola nie jest wdrożona. Konieczne jest działanie naprawcze. Automatycznie generuje zadanie |
| **N/A** | Kontrola nie ma zastosowania w kontekście Twojego plant. Wymaga pisemnego uzasadnienia o długości co najmniej 20 znaków. Uzasadnienie jest zapisywane i widoczne przy każdym ponownym otwarciu kontroli. W VDA ISA TISAX pojawia się w kolumnie "Note / Justification", a poziom dojrzałości jest ustawiany na 0. Dla TISAX L3 wymaga podpisu dwóch ról i wygasa po 12 miesiącach |

> Kontrola z przeterminowanym dowodem automatycznie wraca do stanu „Częściowy", nawet jeśli ustawiłeś ją jako Zgodna. Aktualizuj dowody na bieżąco.

### Jak wgrać dowód

1. Z karty kontroli kliknij **Dołącz dowód**
2. Kliknij **Wybierz plik** i wybierz plik z komputera (akceptowane formaty: PDF, DOCX, XLSX, PNG, JPG, ZIP — maksymalny rozmiar 50 MB)
3. Wypełnij:
   - **Krótki opis** (np. „Zrzut ekranu konfiguracji zapory z 15.03.2026")
   - **Data wygaśnięcia** — obowiązkowa dla logów systemowych, raportów skanowania, certyfikatów. Pozostaw puste dla dokumentów bez daty ważności
   - **Framework / kontrole objęte** — wybierz wszystkie kontrole, które ten dowód dokumentuje
4. Kliknij **Wgraj**

Dowód jest dostępny natychmiast. System automatycznie sprawdzi, czy typ MIME pliku odpowiada zadeklarowanemu rozszerzeniu.

### Jak pobrać SOA ISO 27001, VDA ISA TISAX, Matrycę NIS2

[Zrzut ekranu: strona eksportu compliance]

1. Przejdź do **Compliance → Biblioteka kontroli**
2. Kliknij przycisk **Eksportuj** (ikona pobierania) w prawym górnym rogu strony
3. Wybierz typ eksportu:
   - **SOA ISO 27001** — Deklaracja Stosowalności ze wszystkimi kontrolami Annex A i ich statusem
   - **VDA ISA TISAX** — Tabela VDA Information Security Assessment
   - **Matryca NIS2** — Matryca zgodności NIS2

> **Ważna uwaga**: zawsze używaj przycisku „Eksportuj" wewnątrz strony. Nie otwieraj bezpośrednio URL pliku, kopiując link w przeglądarce — pobranie wymaga tokenu JWT aktywnej sesji i zakończy się błędem 401, jeśli zostanie podjęte poza platformą.

### Analiza luk między frameworkami

1. Przejdź do **Compliance → Analiza luk**
2. Wybierz dwa frameworki do porównania (np. ISO 27001 vs TISAX L2)
3. System wyświetla tabelę z kontrolami zmapowanymi między dwoma frameworkami, podkreślając:
   - Kontrole spełnione w obu frameworkach (zielony)
   - Kontrole spełnione tylko w jednym z nich (żółty)
   - Kontrole z luką w obu (czerwony)
4. Możesz wyeksportować analizę luk w formacie Excel

### Propagacja statusu między frameworkami (i między plantami)

Przycisk **Propaguj** jest dostępny na liście kontroli, obok odznaki statusu, dla kontroli w statusie **Zgodny** lub **N/A**, które mają mapowania do innych frameworków.

**Jak to działa:**

| Typ mapowania | Kierunek | Przykład |
|---------------|----------|---------|
| `Równoważny` | Dwukierunkowy | ISO A.8.1 ≡ TISAX ISA-1.1 → propaguje w obu kierunkach |
| `Pokrywa (covers)` | Tylko źródło → cel | ISO A pokrywa NIS2 art.21 → ISO propaguje na NIS2, nie odwrotnie |
| `Częściowy`, `Powiązany`, `Rozszerza` | Nie propagowany | Wymagają oddzielnej oceny |

**Co jest kopiowane:**
- Status (`compliant` lub `na`) do zmapowanej kontroli w tym samym plancie
- Dla N/A: kopiowane jest również uzasadnienie (z odniesieniem do kontroli źródłowej)
- Dla każdej zaktualizowanej kontroli generowany jest wpis w dzienniku audytu

**Propagacja wieloplantowa:**
Zaznaczenie pola **"wszystkie planty"** rozszerza propagację na wszystkie planty posiadające aktywną instancję kontroli docelowej. Używaj tej opcji, gdy polityka organizacyjna jest współdzielona przez kilka zakładów.

> Statusy `luka`, `częściowy` i `nieoceniony` nie mogą być propagowane: każdy plant musi je ocenić niezależnie.

---

## 4. Aktywa IT i OT (M04)

[Zrzut ekranu: inwentarz aktywów]

### Jak dodać aktywo

**Aktywa IT:**

1. Przejdź do **Ryzyko → Inwentarz aktywów → Nowe aktywo IT**
2. Wypełnij obowiązkowe pola:
   - **Nazwa / FQDN**: nazwa hosta lub adres IP
   - **System operacyjny** i **wersja**
   - **Data EOL**: jeśli system jest poza wsparciem, krytyczność zostanie automatycznie zwiększona
   - **Dostępny w Internecie**: krytyczna flaga — zwiększa profil ryzyka
   - **Poziom krytyczności**: od 1 do 5 (patrz tabela poniżej)
3. W sekcji **Powiązane procesy krytyczne** wybierz procesy z BIA (M05) zależne od tego aktywa
4. Kliknij **Zapisz**

**Aktywa OT:**

1. Przejdź do **Ryzyko → Inwentarz aktywów → Nowe aktywo OT**
2. Oprócz pól wspólnych z aktywami IT, wypełnij:
   - **Poziom Purdue** (0–5): pozycja w hierarchii sieci OT
   - **Kategoria**: PLC, SCADA, HMI, RTU, czujnik, inne
   - **Możliwość aktualizacji**: jeśli system nie może być aktualizowany, podaj przyczynę i zaplanowane okno serwisowe
3. Kliknij **Zapisz**

### Różnica między aktywem IT a OT

| Cecha | Aktywo IT | Aktywo OT |
|-------|-----------|-----------|
| Przykłady | Serwery, stacje robocze, zapory, przełączniki, aplikacje | PLC, SCADA, HMI, RTU, czujniki przemysłowe |
| Typowa sieć | Sieć firmowa, Internet | Sieć produkcyjna, magistrala polowa |
| Aktualizacja | Częsta, możliwa do zautomatyzowania | Ograniczona, wymaga okien serwisowych |
| Wpływ przestoju | Utrata danych, niedostępność usługi | Zatrzymanie produkcji, szkody fizyczne, ryzyko bezpieczeństwa |
| Ocena ryzyka | Wymiary ekspozycja/CVE | Wymiary Purdue/możliwość aktualizacji/bezpieczeństwo |

### Tabela krytyczności 1-5

W formularzu tworzenia i edycji aktywa znajdziesz odznakę krytyczności z podpowiedziami dla każdego poziomu. Dla reference:

| Poziom | Etykieta | Opis |
|--------|----------|------|
| **1** | Niska | Przestój lub kompromitacja nie wpływa na produkcję. Akceptowalna strata bez dedykowanego planu ciągłości |
| **2** | Średnio-niska | Ograniczony wpływ na funkcje administracyjne lub pomocnicze. Odtworzenie w ciągu 24 godzin |
| **3** | Średnia | Wpływ na procesy operacyjne. Wymaga planu ciągłości. Mierzalna utrata danych lub produkcji |
| **4** | Wysoka | Przestój powoduje znaczną stratę ekonomiczną, wpływ na klientów lub zgodność regulacyjną. RTO < 4 godziny |
| **5** | Krytyczna | Wpływ na bezpieczeństwo, ryzyko dla życia lub szkody fizyczne, albo całkowite zatrzymanie produkcji. RTO < 1 godzina. Wymaga natychmiastowej analizy ryzyka |

Zawsze korzystaj z tej tabeli, aby zapewnić spójność między różnymi zakładami.

### Jak zarejestrować zewnętrzną zmianę

Gdy aktywo ulega znaczącej zmianie (aktualizacja firmware, zmiana konfiguracji, rozszerzenie obwodu sieciowego):

1. Otwórz kartę aktywa
2. Kliknij **Zarejestruj zmianę** w sekcji „Historia zmian"
3. Wypełnij: datę zmiany, opis, typ (konfiguracja / sprzęt / oprogramowanie / sieć), szacowany wpływ
4. Zapisz — zmiana jest rejestrowana w śladzie audytu, a aktywo otrzymuje odznakę „Do ponownej oceny"

### Odznaka „Do ponownej oceny" — kiedy się pojawia i co zrobić

Pomarańczowa odznaka **„Do ponownej oceny"** pojawia się na karcie aktywa gdy:

- Zarejestrowano zewnętrzną zmianę
- Upłynął termin okresowego przeglądu przewidziany w polityce
- Ryzyko powiązane z aktywem istotnie zmieniło wynik
- Aktywo osiągnęło datę EOL systemu operacyjnego

Co zrobić: otwórz kartę aktywa, sprawdź czy informacje są nadal aktualne (szczególnie krytyczność, ekspozycja i powiązane procesy krytyczne), a następnie kliknij **Oznacz jako ponownie ocenione**. W razie potrzeby zaktualizuj pola przed potwierdzeniem.

---

## 5. Analiza wpływu na działalność (M05)

[Zrzut ekranu: lista procesów BIA]

### Jak utworzyć proces krytyczny

1. Przejdź do **Ryzyko → BIA → Nowy proces**
2. Wypełnij:
   - **Nazwa procesu**: np. „Zarządzanie zleceniami produkcyjnymi"
   - **Opis**: co robi proces, kto go używa
   - **Właściciel procesu**: wybierz odpowiedzialną rolę
   - **Dział / funkcja**: obszar firmy
   - **Plant**: zakład odniesienia
3. Zapisz — proces przechodzi do stanu **Szkic**

### MTPD, RTO, RPO — proste wyjaśnienie z przykładami

Te trzy parametry określają tolerancję procesu na przerwę:

| Parametr | Definicja | Praktyczny przykład |
|----------|-----------|---------------------|
| **MTPD** (Maximum Tolerable Period of Disruption) | Jak długo proces może być wstrzymany, zanim firma poniesie nieodwracalne szkody | Np. „Proces wysyłki może być wstrzymany maksymalnie 48 godzin, zanim stracimy kluczowych klientów" |
| **RTO** (Recovery Time Objective) | W jakim czasie musimy przywrócić proces po przerwie | Np. „System MES musi wrócić do działania w ciągu 4 godzin od incydentu" |
| **RPO** (Recovery Point Objective) | Do którego punktu w przeszłości możemy stracić dane bez akceptowalnych szkód | Np. „Nie możemy stracić więcej niż 1 godzinę danych produkcyjnych" — kopie zapasowe muszą być wykonywane co najmniej co godzinę |

System używa RTO i RPO do sprawdzenia, czy powiązany plan BCP (M16) jest spójny: jeśli BCP zakłada RTO wyższe niż zadeklarowane w BIA, pojawia się ostrzeżenie.

### Przepływ: szkic → walidacja → zatwierdzenie

1. **Szkic**: proces został utworzony, ale nie został jeszcze zwalidowany. Możesz modyfikować wszystkie pola
2. **Walidacja**: Risk Manager weryfikuje parametry MTPD/RTO/RPO i je zatwierdza lub prosi o zmiany
3. **Zatwierdzenie**: Plant Manager formalnie zatwierdza. Proces staje się niezmienny — aby go zmodyfikować, należy otworzyć nową rewizję

Aby przejść do następnej fazy: z karty procesu kliknij **Wyślij do walidacji** (ze Szkicu) lub **Wyślij do zatwierdzenia** (z Walidacji).

### Jak powiązać proces z aktywem

1. Otwórz kartę procesu BIA
2. W sekcji **Zależne aktywa** kliknij **Dodaj aktywo**
3. Wyszukaj i wybierz aktywo z inwentarza (M04)
4. Wskaż typ zależności: **Krytyczna** (proces zatrzymuje się bez tego aktywa) lub **Pomocnicza** (pogorszenie wydajności)
5. Zapisz

Zależność jest dwukierunkowa: aktywo pokaże na swojej karcie procesy, które od niego zależą, a krytyczność procesu wpływa na obliczenie ryzyka aktywa.

---

## 6. Ocena ryzyka (M06)

[Zrzut ekranu: lista ocen ryzyka]

### Różnica między ryzykiem wrodzonym a rezydualnym

- **Ryzyko wrodzone**: poziom ryzyka w przypadku braku jakichkolwiek kontroli. Reprezentuje „surowe" zagrożenie dla aktywa lub domeny
- **Ryzyko rezydualne**: poziom ryzyka po zastosowaniu istniejących kontroli. To wartość, na której opiera się decyzja o akceptacji lub leczeniu ryzyka

W formularzu oceny najpierw wypełniasz ryzyko wrodzone, a następnie system automatycznie oblicza ryzyko rezydualne na podstawie statusu powiązanych kontroli. Jeśli kontrole nie są jeszcze wystarczające, ryzyko rezydualne pozostaje wysokie.

### Jak wypełnić wymiary IT i OT

**Wymiary oceny ryzyka IT (4 osie):**

1. **Ekspozycja**: czy aktywo jest w Internecie? W DMZ? Izolowane? (1 = całkowicie izolowane, 5 = dostępne w Internecie bez zabezpieczeń)
2. **CVE**: jaki jest maksymalny wynik CVE zaangażowanych aktywów? (1 = brak znanych podatności, 5 = krytyczne CVE nienaprawione)
3. **Zagrożenia sektorowe**: czy istnieją znane aktywne zagrożenia dla sektora automotive? (1 = brak, 5 = udokumentowana aktywna kampania)
4. **Luki w kontrolach**: ile istotnych kontroli jest w stanie luka lub niezocenionych? (1 = wszystkie zgodne, 5 = większość z lukami)

**Wymiary oceny ryzyka OT (5 osi):**

1. **Purdue + łączność**: czy system jest podłączony do sieci IT lub Internetu? (1 = poziom 0 izolowany, 5 = podłączony do Internetu)
2. **Możliwość aktualizacji**: czy system może być aktualizowany? Jak często? (1 = regularne łatki, 5 = nigdy nieaktualizowany)
3. **Wpływ fizyczny / bezpieczeństwo**: czy przerwa lub zmiana może spowodować szkody fizyczne lub BHP? (1 = brak wpływu fizycznego, 5 = zagrożenie życia ludzkiego)
4. **Segmentacja**: czy strefa OT jest odpowiednio oddzielona od IT i Internetu? (1 = całkowita segregacja, 5 = sieć płaska)
5. **Wykrywalność anomalii**: czy istnieje system wykrywania anomalnych zachowań? (1 = aktywny dedykowany IDS/ICS, 5 = brak widoczności)

### Próg krytyczny (wynik > 14) i automatycznie generowane zadania

Gdy **ryzyko rezydualne przekracza 14** (czerwone kwadranty mapy ciepła 5x5):

- Risk Manager i Plant Manager otrzymują natychmiastowe powiadomienie
- Automatycznie tworzone jest zadanie planowania leczenia ryzyka z terminem 15 dni
- Jeśli zadanie nie zostanie ukończone w ciągu 15 dni, następuje eskalacja do Compliance Officer
- Ryzyko jest podświetlone na czerwono na pulpicie i mapie ciepła

### Formalna akceptacja ryzyka

Jeśli ryzyko rezydualne jest znane, ale decyduje się je zaakceptować (np. koszt leczenia wyższy niż oczekiwany wpływ):

1. Z karty ryzyka kliknij **Akceptuj ryzyko**
2. Wypełnij formularz formalnej akceptacji:
   - Uzasadnienie (obowiązkowe, minimum 50 znaków)
   - Data przeglądu (obowiązkowa — ryzyko musi być okresowo ponownie oceniane)
   - Podpis cyfrowy upoważnionego odpowiedzialnego
3. Zapisz — ryzyko przechodzi do stanu „Zaakceptowane" i nie generuje alertów do daty przeglądu

### Mapa ciepła i interpretacja

[Zrzut ekranu: mapa ciepła 5x5]

Mapa ciepła pokazuje ryzyka na siatce Prawdopodobieństwo x Wpływ 5x5:

- **Zielony** (wynik 1-7): akceptowalne ryzyko — okresowe monitorowanie
- **Żółty** (wynik 8-14): umiarkowane ryzyko — plan łagodzenia w ciągu 90 dni
- **Czerwony** (wynik 15-25): wysokie ryzyko — automatyczna eskalacja, plan w ciągu 15 dni

Kliknij kwadrant, aby zobaczyć listę ryzyk w tej strefie. Użyj filtra plant, aby porównać rozkład ryzyk między różnymi zakładami.

---

## 7. Dokumenty i dowody (M07)

[Zrzut ekranu: zarządzanie dokumentami]

### Różnica między Dokumentem a Dowodem

| Cecha | Dokument | Dowód |
|-------|----------|-------|
| Co reprezentuje | Polityka, procedura, instrukcja operacyjna | Zrzut ekranu, log, raport ze skanowania, certyfikaty |
| Obowiązkowy przepływ | Tak — redakcja, przegląd, zatwierdzenie | Nie — bezpośrednie wgranie |
| Wersjonowanie | Tak — każda wersja jest niezmienna po zatwierdzeniu | Nie |
| Data wygaśnięcia | Tylko jeśli wyraźnie skonfigurowana | Obowiązkowa dla logów, skanów, certyfikatów |
| Główne zastosowanie | Udowodnienie, że proces istnieje i jest zarządzany | Udowodnienie, że kontrola jest aktywna i działa |

### Przepływ zatwierdzania dokumentów (3 poziomy)

Dokument przechodzi przez 3 obowiązkowe fazy w kolejności:

1. **Redakcja** (właściciel dokumentu): wgrywa plik PDF, wypełnia metadane (tytuł, kod, framework, właściciel, recenzent, zatwierdzający), zapisuje szkic. Dokument można modyfikować tylko na tym etapie
2. **Przegląd** (wyznaczony recenzent): czyta dokument, może dodać ustrukturyzowane notatki lub zatwierdzić. Jeśli odmawia, musi napisać komentarz, który staje się częścią stałego dziennika zmian
3. **Zatwierdzenie przez kierownictwo** (Plant Manager lub CISO): formalnie zatwierdza. Po zatwierdzeniu dokument jest niezmienny — aby go zmodyfikować, należy otworzyć nową rewizję za pomocą przycisku **Nowa rewizja**

### Jak powiązać dowód z kontrolą

Metoda 1 — z karty kontroli:
1. Przejdź do karty kontroli (Compliance → Biblioteka kontroli → wybierz kontrolę)
2. Kliknij **Dołącz dowód** w sekcji „Powiązane dowody"
3. Wgraj plik lub wybierz już wgrany dowód ze swojego archiwum
4. Zapisz

Metoda 2 — z karty dowodu:
1. Wgraj dowód przez **Compliance → Dowody → Nowy dowód**
2. W polu **Objęte kontrole** wybierz jedną lub więcej kontroli, które ten dowód dokumentuje
3. Zapisz

Dowód może obejmować wiele kontroli jednocześnie, nawet z różnych frameworków.

### Wygaśnięcie dowodów i kolorowe odznaki

Dowody z datą wygaśnięcia pokazują kolorową odznakę na karcie kontroli i na liście dowodów:

| Odznaka | Znaczenie |
|---------|-----------|
| **Zielona** | Dowód ważny — wygaśnięcie za ponad 30 dni |
| **Żółta** | Wygasający — pozostało mniej niż 30 dni |
| **Czerwona** | Wygasły — data ważności już minęła. Powiązana kontrola automatycznie degraduje do „Częściowej" |
| **Szara** | Nie ustawiono daty wygaśnięcia |

System wysyła przypomnienie e-mailem 30 dni przed wygaśnięciem i alert w dniu faktycznego wygaśnięcia.

### Wersjonowanie dokumentów

Każdy zatwierdzony dokument otrzymuje numer wersji (np. v1.0, v1.1, v2.0). Pełna historia wszystkich wersji jest dostępna z karty dokumentu w sekcji **Historia wersji**. Każda wersja rejestruje:

- Datę zatwierdzenia
- Imię zatwierdzającego
- Dziennik zmian (notatki recenzenta)
- Hash pliku gwarantujący integralność

---

## 8. Zarządzanie incydentami (M09)

[Zrzut ekranu: lista incydentów]

### Jak otworzyć incydent

1. Przejdź do **Operacje → Incydenty → Nowy incydent**
2. Wypełnij obowiązkowe pola:
   - **Zaangażowany plant**: automatycznie określa profil NIS2 podmiotu
   - **Tytuł**: krótki opis (np. „Nieautoryzowany dostęp do systemu MES — zakład Północ")
   - **Opis**: co się stało, kiedy zostało wykryte, jak odkryto
   - **Zaangażowane aktywa**: wybierz z inwentarza (M04)
   - **Wstępna powaga**: Niska / Średnia / Wysoka / Krytyczna — można aktualizować w dowolnym momencie
3. Kliknij **Utwórz incydent**

Natychmiast po utworzeniu system ocenia, czy plant jest podmiotem NIS2 i jeśli tak, uruchamia timery ACN widoczne na górze karty incydentu.

### Flaga NIS2 i timer 24h (zgłoszenie ACN)

[Zrzut ekranu: karta incydentu z timerami NIS2]

Jeśli plant jest sklasyfikowany jako podmiot NIS2 (istotny lub ważny), na karcie incydentu pojawiają się trzy odliczania:

- **T+24h — Wczesne ostrzeżenie ACN**: wstępne zgłoszenie do właściwego organu (obowiązek prawny)
- **T+72h — Pełne zgłoszenie**: szczegółowe zgłoszenie z wpływem i podjętymi środkami
- **T+30 dni — Raport końcowy**: raport końcowy z RCA

CISO ma 30 minut od utworzenia incydentu, aby potwierdzić lub wykluczyć obowiązek zgłoszenia za pomocą przycisku **Wyklucz obowiązek NIS2**. Jeśli nie odpowie w ciągu 30 minut, system zakłada, że zgłoszenie jest wymagane i timery pozostają aktywne.

Timery wyświetlane są z czerwonym tłem, gdy pozostały czas jest krótszy niż 2 godziny.

### Wypełnianie RCA (Analiza przyczyn źródłowych)

1. Na karcie incydentu przejdź do sekcji **Analiza przyczyn źródłowych**
2. Wybierz metodę analizy:
   - **5 Why**: z przewodnikiem, z 5 poziomami „dlaczego"
   - **Ishikawa**: diagram przyczyna-skutek według kategorii (Ludzie, Proces, Technologia, Środowisko)
   - **Tekst swobodny**: narracyjny, nieustrukturyzowany
3. Wypełnij przyczynę źródłową, zawiedzione kontrole i proponowane działania naprawcze
4. Wyślij do zatwierdzenia do Risk Manager za pomocą **Wyślij do zatwierdzenia**

Incydent nie może zostać zamknięty bez zatwierdzonej RCA.

### Zamknięcie i automatycznie generowane PDCA

Po zatwierdzeniu RCA możesz zamknąć incydent za pomocą przycisku **Zamknij incydent**. Zamknięcie automatycznie generuje:

- **Lekcję** w M12 z informacjami o incydencie i działaniami naprawczymi
- Cykl **PDCA** w M11, jeśli działania naprawcze mają charakter strukturalny (np. modyfikacja procedur, wdrożenie nowych kontroli)
- Wyzwalacz **przeglądu** dla powiązanych dokumentów w M07, jeśli zawiedzione kontrole są objęte istniejącymi politykami

---

## 9. PDCA (M11)

[Zrzut ekranu: lista cykli PDCA]

### 4 fazy: PLAN, DO, CHECK, ACT

Każdy cykl PDCA reprezentuje działanie ciągłego doskonalenia. 4 fazy następują po sobie w obowiązkowej kolejności:

- **PLAN**: zdefiniuj cel, działania do podjęcia i niezbędne zasoby
- **DO**: wykonaj zaplanowane działania
- **CHECK**: sprawdź, czy wyniki odpowiadają celom poprzez mierzalny dowód
- **ACT**: standaryzuj rozwiązanie jeśli zadziałało, albo wróć do DO z innym podejściem

### Co jest wymagane do przejścia każdej fazy

| Przejście | Obowiązkowy wymóg |
|-----------|------------------|
| **PLAN → DO** | Opis działania do wykonania (minimum 20 znaków). Plan musi być zrozumiały również poza kontekstem |
| **DO → CHECK** | Dołączony dowód dokumentujący wykonane działanie (plik obowiązkowy) |
| **CHECK → ACT** | Wynik weryfikacji (opisowy tekst) + Wybrany rezultat: **ok** / **częściowy** / **ko** |
| **ACT → ZAMKNIĘTY** | Standaryzacja: dokumentacja przyjętego rozwiązania, aby było odtwarzalne (minimum 20 znaków) |

### Co się dzieje, gdy wynik CHECK = ko

Jeśli w fazie CHECK wynik jest **ko** (rozwiązanie nie zadziałało):

1. Cykl nie przechodzi do ACT, ale automatycznie wraca do fazy **DO**
2. W dzienniku cyklu dodawana jest notatka z datą niepowodzenia
3. Konieczne jest opracowanie nowego planu działania dla fazy DO
4. Licznik cykli DO jest inkrementowany, aby śledzić liczbę potrzebnych iteracji

Nie ma limitu liczby iteracji DO-CHECK, ale system sygnalizuje cykle z więcej niż 3 iteracjami do Compliance Officer.

### PDCA tworzone automatycznie z incydentów, wyników audytu, ryzyk krytycznych

Cykle PDCA są tworzone ręcznie lub automatycznie przez:

- **Zamknięte incydenty (M09)**: gdy działania naprawcze RCA mają charakter strukturalny — faza startowa PLAN
- **Wyniki audytu (M17)**: dla Major NC i Minor NC — faza startowa PLAN z terminem określonym przez powagę
- **Ryzyka z wynikiem > 14 (M06)**: gdy plan leczenia wymaga działań strukturalnych — pilna faza PLAN
- **Uchwały przeglądu zarządu (M13)**: dla każdego działania zatwierdzonego przez przegląd — faza PLAN

We wszystkich przypadkach automatycznego tworzenia cykl PDCA zawiera odniesienie do encji źródłowej (np. „Incydent #INC-2026-042") i ewentualny termin wynikający z polityki.

---

## 10. Lekcje (M12)

[Zrzut ekranu: baza wiedzy lekcji]

### Jak ręcznie utworzyć lekcję

1. Przejdź do **Ład organizacyjny → Lekcje → Nowa**
2. Wypełnij:
   - **Tytuł**: krótki opis zdarzenia lub nauki
   - **Opis zdarzenia**: co się stało, kontekst, znaczenie
   - **Zastosowana metoda analizy**: 5 Why, Ishikawa, tekst swobodny
   - **Zidentyfikowana przyczyna źródłowa**
   - **Objęte kontrole**: wybierz odpowiednie kontrole z biblioteki
   - **Działania krótkoterminowe**: działania do ukończenia w ciągu 30 dni
   - **Działania strukturalne**: działania długoterminowe (będą zarządzane przez PDCA)
3. Kliknij **Wyślij do zatwierdzenia**

Risk Manager lub Compliance Officer zatwierdzają lekcję, zanim stanie się widoczna dla całej organizacji w bazie wiedzy.

### Lekcje tworzone automatycznie z zamkniętych PDCA

Gdy cykl PDCA zostaje zamknięty z pozytywnym wynikiem, system automatycznie tworzy lekcję zawierającą:

- Oryginalny kontekst (incydent, wynik audytu, ryzyko), który zapoczątkował PDCA
- Działania wykonane w fazach DO
- Wynik uzyskany w fazie CHECK
- Standaryzację udokumentowaną w fazie ACT

Automatyczna lekcja startuje w stanie „Szkic" i jest przypisana jako zadanie właścicielowi cyklu PDCA do przeglądu przed zatwierdzeniem.

### Wyszukiwanie w bazie wiedzy

Przejdź do **Ład organizacyjny → Lekcje → Baza wiedzy**. Możesz wyszukiwać według:

- **Słowa kluczowego**: wyszukiwanie tekstowe w tytule i opisie
- **Framework / kontrola**: filtrowanie według objętych kontroli
- **Typ zdarzenia**: incydent, wynik audytu, ryzyko, dobrowolne doskonalenie
- **Plant**: tylko lekcje z Twojego plant lub wszystkich plant (jeśli masz dostęp wielozakładowy)
- **Okres**: data zatwierdzenia

Wyświetlane są tylko zatwierdzone lekcje. Szkice są widoczne tylko dla właściciela i recenzentów.

---

## 11. Przegląd Zarządu (M13)

[Zrzut ekranu: przegląd zarządu]

### Jak utworzyć przegląd

1. Przejdź do **Ład organizacyjny → Przegląd Zarządu → Nowy**
2. Wypełnij:
   - **Rok i numer**: np. „2026 — Prz. 1/2026"
   - **Planowana data**
   - **Uczestnicy**: wybierz zaangażowane role (Plant Manager, CISO, Risk Manager, CO)
3. System automatycznie dodaje obowiązkowe punkty do porządku obrad (patrz poniżej)
4. Możesz dodawać dodatkowe punkty za pomocą **Dodaj punkt PO**
5. Kliknij **Zapisz szkic**

### Obowiązkowe punkty porządku obrad (ISO 27001 kl.9.3)

Norma ISO 27001 klauzula 9.3 wymaga, aby przegląd zarządu obowiązkowo obejmował szereg punktów. System automatycznie wstawia je do szkicu:

- Status działań z poprzednich przeglądów
- Zmiany w wewnętrznym i zewnętrznym kontekście istotne dla SZBI
- Informacje zwrotne o wynikach SZBI (NC, audyty, monitorowanie, pomiary)
- Informacje zwrotne od zainteresowanych stron
- Wyniki oceny ryzyka i status planu postępowania
- Możliwości ciągłego doskonalenia

Nie można zamknąć przeglądu, jeśli którykolwiek z tych punktów nie ma przynajmniej jednego zarejestrowanego komentarza lub decyzji.

### Jak rejestrować decyzje

Dla każdego punktu porządku obrad:

1. Kliknij punkt, aby go rozwinąć
2. Wpisz **streszczenie dyskusji**
3. Kliknij **Dodaj decyzję**, aby zarejestrować działania zatwierdzone przez kierownictwo
4. Dla każdej decyzji podaj: odpowiedzialnego, działanie do podjęcia, termin

Decyzje z odpowiedzialnym i terminem są automatycznie przekształcane w zadania w M08 i, jeśli strukturalne, w cykle PDCA w M11.

### Zamknięcie i zatwierdzenie

1. Po uzupełnieniu wszystkich obowiązkowych punktów kliknij **Wyślij do zatwierdzenia**
2. Plant Manager otrzymuje zadanie zatwierdzenia
3. Po zatwierdzeniu przegląd staje się niezmienny
4. Automatycznie generowany jest protokół PDF podpisany hashem i znacznikiem czasu, dostępny w sekcji **Wygenerowane dokumenty** przeglądu

---

## 12. Przygotowanie do audytu (M17)

[Zrzut ekranu: przygotowanie do audytu — lista programów]

### Program roczny

#### Jak utworzyć program za pomocą kreatora (4 kroki)

1. Przejdź do **Audyt → Przygotowanie do audytu → Nowy program**
2. Otworzy się kreator w 4 krokach:

**Krok 1 — Dane podstawowe**
- Rok programu (np. 2026)
- Plant odniesienia
- Frameworki do audytowania (ISO 27001, TISAX L2, TISAX L3, NIS2 — wybierz jeden lub więcej)
- Nazwa programu (np. „Program audytu ISO 27001 — Zakład Północ 2026")

**Krok 2 — Parametry pokrycia**
Wybierz poziom pokrycia audytu:
- **Próbka (25%)**: wyrywkowy audyt jednej czwartej kontroli. Odpowiedni dla pośrednich weryfikacji lub gdy zasoby są ograniczone
- **Rozszerzony (50%)**: pokrycie połowy kontroli. Równowaga między głębokością a zrównoważonością
- **Pełny (100%)**: kompletny audyt wszystkich kontroli frameworku. Wymagany dla formalnych certyfikacji

**Krok 3 — Przegląd sugerowanego planu**
System analizuje bieżący stan kontroli i generuje sugerowany plan, który:
- Koncentruje Q1 i Q3 na **domenach z największymi lukami** (najbardziej krytyczne są audytowane jako pierwsze)
- Rozkłada pozostałe kontrole na kwartały Q2 i Q4
- Sugeruje audytorów na podstawie dostępnych ról w plant

Możesz ręcznie modyfikować: daty każdego kwartału, audytora przypisanego do każdej sesji, listę kontroli objętych każdym kwartałem.

**Krok 4 — Zatwierdzenie**
- Przejrzyj podsumowanie programu
- Kliknij **Zatwierdź program**
- Program staje się aktywny i widoczny dla wszystkich zaangażowanych ról

#### Jak interpretować sugerowany plan

System nadaje priorytet domenom z największymi lukami w początkowych kwartałach (Q1 i Q3), aby dać wystarczająco czasu na rozwiązanie problemów przed ewentualnymi audytami certyfikacyjnymi. Domeny z dobrym pokryciem są przypisywane do kwartałów Q2 i Q4. Sprawdź, czy rozkład jest zrównoważony pod względem obciążenia pracą audytorów.

#### Jak zmodyfikować daty i audytorów dla kwartału

Ze szczegółów zatwierdzonego programu:
1. Kliknij ikonę edycji obok kwartału do aktualizacji
2. Zmodyfikuj datę rozpoczęcia/zakończenia i przypisanego audytora
3. Zapisz — zmiana jest rejestrowana w dzienniku programu

#### Jak zatwierdzić program

Po ukończeniu Kroku 4 kreatora, program automatycznie przechodzi do stanu „Zatwierdzony". Compliance Officer otrzymuje powiadomienie. Program jest teraz widoczny dla przypisanych audytorów.

---

### Wykonanie audytu

[Zrzut ekranu: szczegóły kwartału audytu]

#### Jak uruchomić audyt z kwartału

1. Z zatwierdzonego programu przejdź do interesującego kwartału
2. Kliknij **Uruchom audyt** — kwartał przechodzi z „Zaplanowany" do „W toku"
3. Otwiera się lista kontrolna kontroli do weryfikacji w tym kwartale

#### Próbka vs pełna — praktyczne różnice

- **Próbka**: widzisz tylko podzbiór kontroli wybranych przez system (25% lub 50% z całości). Nie możesz dodawać kontroli nieujętych w próbce
- **Pełna**: widzisz wszystkie kontrole frameworku. Musisz wypełnić dowód dla każdej z nich przed zamknięciem audytu

W obu przypadkach struktura listy kontrolnej jest identyczna — różnica polega jedynie na liczbie kontroli do weryfikacji.

#### Jak wypełnić listę kontrolną kontroli

Dla każdej kontroli na liście:
1. Kliknij kontrolę, aby rozwinąć szczegóły
2. Sprawdź zadeklarowany status i powiązany dowód
3. Wybierz **ocenę audytora**: Potwierdzona / Niezgodna / Obserwacja / Możliwość
4. Jeśli ocena jest inna niż „Potwierdzona", kliknij **Dodaj wynik** (patrz poniżej)
5. Dodaj ewentualne notatki audytora w odpowiednim polu
6. Kliknij **Zapisz ocenę**

#### Jak dodać wynik audytu

1. Z karty kontroli kliknij **Dodaj wynik**
2. Wypełnij:
   - **Tytuł wyniku**
   - **Szczegółowy opis**: czego brakuje lub co nie jest zgodne
   - **Typ wyniku** (patrz tabela poniżej)
   - **Kontrola odniesienia**
   - **Dowód na poparcie**: opcjonalny przy otwieraniu, obowiązkowy dla Major NC

#### Typy wyników i terminy odpowiedzi

| Typ | Znaczenie | Termin odpowiedzi |
|-----|-----------|------------------|
| **Major NC** (Poważna Niezgodność) | Niespełniony wymóg z istotnym wpływem na zgodność lub bezpieczeństwo | 30 dni |
| **Minor NC** (Mniejsza Niezgodność) | Częściowo niespełniony wymóg, ograniczony wpływ | 90 dni |
| **Obserwacja** | Potencjalna słabość, która nie jest jeszcze niezgodnością. Do monitorowania | 180 dni |
| **Możliwość** | Sugestia doskonalenia bez wpływu na zgodność. Brak obowiązkowego terminu | — |

Terminy odpowiedzi są obliczane automatycznie od daty otwarcia wyniku na podstawie tych polityk. Dla Major NC automatycznie tworzony jest również cykl PDCA.

#### Jak zamknąć wynik audytu

1. Z karty wyniku, po podjęciu działań naprawczych, kliknij **Zaproponuj zamknięcie**
2. Wgraj **dowód zamknięcia** (obowiązkowy dla Major NC i Minor NC)
3. Wpisz **komentarz zamknięcia**: opisz podjęte działania
4. Wynik przechodzi do stanu „W weryfikacji"
5. Odpowiedzialny audytor weryfikuje dowód i klika **Potwierdź zamknięcie** lub **Ponownie otwórz wynik** z komentarzem

#### Jak pobrać raport audytu

Z audytu w toku lub zamkniętego:
1. Kliknij przycisk **Raport** (ikona PDF) w prawym górnym rogu strony audytu
2. Wybierz język raportu
3. System generuje PDF z: podsumowaniem pokrycia, listą wyników według typu, statusem zamknięcia, trendem w porównaniu z poprzednim audytem
4. PDF jest natychmiast dostępny do pobrania

---

### Anulowanie audytu

[Zrzut ekranu: przycisk anulowania audytu]

#### Kiedy używać „Anuluj" vs usunięcia

- Użyj **Anuluj**, gdy zaplanowany audyt nie zostanie przeprowadzony, ale chcesz zachować ślad oryginalnego planowania (np. zmiana daty, zmiana zakresu, sytuacja awaryjna w firmie)
- **Usunięcie** nie jest dostępne dla audytów w stanie „W toku" lub „Zamknięty" — zawsze używaj „Anuluj" dla uruchomionych audytów

#### Jak anulować

1. Z listy audytów kliknij przycisk **Anuluj** (ikona X) w wierszu audytu
2. Otwiera się okno dialogowe wymagające **uzasadnienia anulowania** (obowiązkowe, minimum 10 znaków)
3. Wpisz uzasadnienie (np. „Przesunięty na Q3 ze względu na dostępność audytora")
4. Kliknij **Potwierdź anulowanie**

#### Co dzieje się z otwartymi wynikami

Gdy anulujesz audyt, który ma już otwarte wyniki:
- Wyniki są **automatycznie zamykane** ze statusem „Anulowany" i uzasadnieniem anulowania
- PDCA powiązane z wynikami pozostają otwarte i muszą być zarządzane ręcznie
- Program roczny nie jest modyfikowany — kwartał jest oznaczany jako „Anulowany" ze śladem uzasadnienia

Anulowany audyt nigdy nie jest fizycznie usuwany — pozostaje w archiwum ze statusem „Anulowany" w celu zapewnienia identyfikowalności.

---

## 13. Dostawcy (M14)

[Zrzut ekranu: lista dostawców]

### Jak zarejestrować dostawcę

1. Przejdź do **Ład organizacyjny → Dostawcy → Nowy dostawca**
2. Wypełnij:
   - **Nazwa firmy** i **NIP**
   - **Kategoria**: IT, OT, Usługi Profesjonalne, Logistyka, inne
   - **Krytyczność**: jak ważny jest dla ciągłości operacyjnej (1–5)
   - **Wewnętrzny opiekun**: wybierz rolę odpowiedzialną za zarządzanie dostawcą
   - **Kontakt dostawcy**: imię i e-mail kontaktu u dostawcy
   - **Przetwarzanie danych**: flaga, jeśli dostawca przetwarza dane osobowe (wiąże się z dodatkowymi obowiązkami RODO)
3. Kliknij **Zapisz**

### Ocena: zaplanowana → w toku → zakończona → zatwierdzona/odrzucona

Każdy krytyczny dostawca musi być okresowo oceniany. Przepływ to:

1. **Zaplanowana**: ocena jest tworzona z docelową datą. Wewnętrzny opiekun otrzymuje zadanie
2. **W toku**: ocena jest uruchamiana. Dostawca otrzymuje (e-mailem lub tymczasowym dostępem) kwestionariusz do wypełnienia
3. **Zakończona**: dostawca odpowiedział na wszystkie pytania. Wewnętrzny opiekun otrzymuje kwestionariusz do przeglądu
4. **Zatwierdzona** lub **Odrzucona**: Compliance Officer lub Risk Manager wydaje ostateczną ocenę (patrz poniżej)

### Wynik w zakresie ładu, bezpieczeństwa, BCP

Kwestionariusz oceny ocenia dostawcę w 3 wymiarach:

| Wymiar | Co ocenia |
|--------|-----------|
| **Ład organizacyjny** | Struktura organizacyjna w zakresie bezpieczeństwa, wewnętrzne polityki, zdefiniowane obowiązki, audyty wewnętrzne |
| **Bezpieczeństwo** | Wdrożone kontrole techniczne, zarządzanie podatnościami, reagowanie na incydenty, certyfikacje (ISO 27001, TISAX) |
| **BCP** | Plany ciągłości operacyjnej, zadeklarowane RTO/RPO, przeprowadzone testy ciągłości, redundancje infrastrukturalne |

Każdy wymiar daje wynik 0-100. Wynik ogólny to ważona średnia trzech wymiarów.

### Zatwierdzenie i odrzucenie z obowiązkowymi notatkami

**Zatwierdzenie:**
1. Z karty zakończonej oceny kliknij **Zatwierdź dostawcę**
2. Wpisz **notatki zatwierdzenia** (obowiązkowe — np. „Dostawca certyfikowany ISO 27001, odpowiedni wynik. Następny przegląd za 12 miesięcy")
3. Ustaw **datę wygaśnięcia zatwierdzenia** (zazwyczaj 12 miesięcy)
4. Kliknij **Potwierdź zatwierdzenie**

**Odrzucenie:**
1. Z karty zakończonej oceny kliknij **Odrzuć dostawcę**
2. Wpisz **notatki odrzucenia** (obowiązkowe — musi to być szczegółowe uzasadnienie uzasadniające decyzję)
3. Kliknij **Potwierdź odrzucenie**

Odrzucenie generuje zadanie dla wewnętrznego opiekuna w celu zarządzania przejściem (zastąpienie dostawcy lub plan naprawczy).

---

## 14. Szkolenia (M15)

[Zrzut ekranu: indywidualny plan szkoleń]

### Jak zobaczyć swoje obowiązkowe kursy

1. Przejdź do **Ład organizacyjny → Szkolenia → Mój plan**
2. Znajdziesz listę obowiązkowych kursów dla swojej roli i plant z:
   - Nazwą kursu
   - Statusem: Do ukończenia / W toku / Ukończony / Wygasły
   - Datą terminu (lub datą ukończenia, jeśli już wykonano)
   - Typem: online (KnowBe4), stacjonarny, dokumentalny

### Ukończenie i terminy

- Kliknij **Uruchom kurs** na kursach online, aby bezpośrednio otworzyć moduł na KnowBe4
- Ukończenia są synchronizowane automatycznie każdej nocy — jeśli ukończyłeś kurs na KnowBe4, ale nie pojawia się jeszcze jako ukończony w GRC Platform, poczekaj do następnego dnia lub skontaktuj się z Compliance Officer
- Kurs wygasły (ukończony, ale wymagający okresowego powtórzenia) pojawia się z czerwoną odznaką i generuje zadanie odświeżenia

### Analiza luk kompetencji

Przejdź do **Ład organizacyjny → Szkolenia → Analiza luk**. Strona pokazuje:

- Wymagania kompetencyjne przewidziane dla każdej roli i plant
- Faktycznie certyfikowane kompetencje (ukończone kursy, wgrane zaświadczenia)
- Podświetlone luki: wymagane kompetencje, ale niezabezpieczone żadnym ukończonym kursem

Compliance Officer może używać tego widoku do planowania sesji szkoleniowych i uzupełniania priorytetowych luk.

### Synchronizacja KnowBe4 (tylko admin)

Przejdź do **Ustawienia → Integracje → KnowBe4**:

1. Skonfiguruj klucz API KnowBe4
2. Kliknij **Synchronizuj teraz**, aby wymusić natychmiastową synchronizację ukończeń
3. Sprawdź dziennik ostatniej synchronizacji, aby zidentyfikować ewentualne błędy

Automatyczna synchronizacja odbywa się każdej nocy o 02:00.

---

## 15. Ciągłość działania (M16)

[Zrzut ekranu: lista planów BCP]

### Jak utworzyć plan BCP

1. Przejdź do **Ład organizacyjny → BCP → Nowy plan**
2. Wypełnij:
   - **Nazwa planu** (np. „Plan BCP — Linia produkcyjna B — Zakład Południe")
   - **Zakres**: procesy krytyczne objęte planem (wybierz z BIA)
   - **Właściciel planu**: odpowiedzialny za utrzymanie
   - **Docelowe RTO** i **docelowe RPO**: wartości, które plan musi gwarantować
3. Kliknij **Zapisz szkic**

### Powiązanie z RTO/RPO z BIA

W sekcji **Objęte procesy** planu BCP, dla każdego wybranego procesu wyświetlane jest porównanie między:

- **RTO wymaganym przez BIA**: maksimum tolerowane zadeklarowane w procesie krytycznym
- **RTO gwarantowanym przez BCP**: tym, co plan jest w stanie faktycznie zagwarantować

Jeśli BCP gwarantuje RTO wyższe niż wymagane przez BIA, pojawia się pomarańczowe ostrzeżenie wymagające przeglądu. System nie blokuje zapisu, ale wymaga wyraźnego uzasadnienia.

### Typy testów

Plan musi być okresowo testowany. Dostępne typy testów:

| Typ | Opis |
|-----|------|
| **Tabletop** | Symulacja papierowa/dyskusja. Uczestnicy w sali konferencyjnej, bez zaangażowania rzeczywistych systemów |
| **Symulacja** | Częściowa symulacja z niektórymi rzeczywistymi systemami w trybie testowym, bez przerywania produkcji |
| **Pełny** | Kompletny test z aktywacją planu na rzeczywistych systemach, bez wpływu na normalną produkcję |
| **Drill** | Nieogłoszone ćwiczenie testujące rzeczywiste czasy reakcji zespołu |

Aby zarejestrować test: z karty planu kliknij **Nowy test**, wybierz typ, datę, uczestników i wynik.

### Co się dzieje, gdy test nie powiedzie się (automatyczny PDCA)

Jeśli test jest zarejestrowany z wynikiem **Nieudany** lub **Częściowo zaliczony**:

1. Automatycznie tworzony jest cykl PDCA z fazą startową PLAN
2. PDCA jest przypisywany właścicielowi planu BCP
3. Właściciel musi opracować plan działania w ciągu 30 dni
4. Plan BCP pozostaje w stanie „Do aktualizacji", dopóki PDCA nie zostanie zamknięty z pozytywnym wynikiem

### Wygaśnięcie planów i alerty

Każdy plan BCP ma obowiązkową datę przeglądu (zazwyczaj roczną). Gdy data się zbliża:

- **30 dni przed**: powiadomienie e-mail do właściciela planu
- **W dniu wygaśnięcia**: plan przechodzi do stanu „Wygasły" z czerwoną odznaką. Automatycznie tworzone jest zadanie przeglądu
- Jeśli wygasły plan obejmuje procesy z MTPD < 48 godzin, do Plant Manager wysyłane jest powiadomienie eskalacyjne

---

## 16. Harmonogram działań (Terminarz)

[Zrzut ekranu: terminarz z widokiem kalendarza]

### Jak czytać kalendarz terminów

Przejdź do **Operacje → Terminarz**. Strona wyświetla wszystkie terminy w wybranym okresie (domyślnie: następne 30 dni), posortowane według daty. Dla każdego terminu widzisz:

- **Typ** terminu (dokument, dowód, zadanie, ocena, plan BCP, kurs szkoleniowy itp.)
- **Nazwę** elementu
- **Datę** terminu
- **Właściciela** odpowiedzialnego
- **Status** z kolorową odznaką (patrz poniżej)

Możesz przełączać się między widokiem listy a widokiem kalendarza, klikając ikony w prawym górnym rogu.

### Filtry według typu i okresu

Na pasku filtrów nad listą możesz filtrować według:

- **Typu**: wybierz jeden lub więcej typów terminów (dokumenty, dowody, zadania, oceny, BCP, szkolenia)
- **Okresu**: ten tydzień / ten miesiąc / następne 30 dni / następne 90 dni / niestandardowy zakres
- **Właściciela**: filtrowanie według odpowiedzialnego za termin
- **Plant**: filtrowanie według zakładu (jeśli masz dostęp wielozakładowy)

### Kolory odznak

| Kolor | Znaczenie |
|-------|-----------|
| **Zielony** | Ważny — nie wymaga działania, termin daleko |
| **Żółty** | Wygasający — pozostało mniej niż 30 dni. Sprawdź i zaplanuj działanie |
| **Czerwony** | Wygasły — data już minęła. Wymagane pilne działanie |

### Jak przejść bezpośrednio do elementu z terminu

Kliknij nazwę dowolnego terminu na liście, aby bezpośrednio otworzyć kartę danego elementu (np. klikając dowód wygasający, otwierasz kartę dowodu). Nie ma potrzeby ręcznego nawigowania przez menu.

---

## 17. Dokumenty obowiązkowe

[Zrzut ekranu: strona dokumentów obowiązkowych]

### Jak powiązać dokument z wymogiem normatywnym

Dokumenty obowiązkowe to te wyraźnie wymagane przez framework normatywny (np. ISO 27001 wymaga „Polityki bezpieczeństwa informacji"). Aby powiązać istniejący dokument z wymogiem:

1. Przejdź do **Compliance → Dokumenty obowiązkowe**
2. Znajdź wymóg normatywny na liście
3. Kliknij **Powiąż dokument** obok wymogu
4. Wyszukaj i wybierz odpowiedni dokument z biblioteki dokumentów (M07)
5. Zapisz

Jeśli dokument jeszcze nie istnieje, kliknij **Utwórz dokument**, aby uruchomić przepływ tworzenia w M07.

### Sygnalizator statusu

Dla każdego wymogu normatywnego na liście, sygnalizator pokazuje status powiązanego dokumentu:

| Kolor sygnalizatora | Znaczenie |
|--------------------|-----------|
| **Zielony** | Dokument obecny, zatwierdzony i ważny (nieprzeterminowany) |
| **Żółty** | Dokument obecny i zatwierdzony, ale wygasający w ciągu 30 dni — zaplanuj przegląd |
| **Czerwony** | Dokument obecny, ale wygasły — pilna aktualizacja wymagana |
| **Szary** | Brakujący dokument — żaden dokument nie jest powiązany z tym wymogiem |

Wymogi z szarym sygnalizatorem negatywnie wpływają na KPI compliance frameworku.

### Jak dodać brakujący dokument

Gdy sygnalizator jest szary (brakujący dokument):

1. Kliknij wymóg
2. Kliknij **Utwórz i powiąż dokument**, aby uruchomić kreator tworzenia
3. System automatycznie preuzupełnia sugerowany tytuł, framework odniesienia i normatywne pola dokumentu
4. Uzupełnij brakujące pola (właściciel, recenzent, zatwierdzający) i wgraj plik
5. Dokument startuje w stanie Szkic i podąża normalnym przepływem zatwierdzania (M07)
6. Po zatwierdzeniu sygnalizator automatycznie zmienia kolor na zielony

---

## 18. Powiadomienia e-mail

### Kiedy przychodzą powiadomienia

Platforma wysyła automatyczne powiadomienia e-mail na podstawie zdarzeń. Główne z nich:

| Zdarzenie | Odbiorcy |
|-----------|----------|
| Przypisane zadanie | Właściciel roli docelowej |
| Zadanie wygasające (7 dni) | Właściciel roli + odpowiedzialny |
| Zadanie przeterminowane | Właściciel + odpowiedzialny + Compliance Officer (po 14 dniach) |
| Otwarty wynik audytu | Odpowiedzialny za auditowany obszar |
| Wynik audytu wygasający (30/90/180 dni) | Właściciel wyniku |
| Nadchodzący audyt (7 dni) | Audytor + Compliance Officer |
| Incydent NIS2 — timer T+24h | CISO + Compliance Officer |
| Incydent NIS2 — timer T+72h | CISO + Compliance Officer + Plant Manager |
| Ryzyko z wynikiem > 14 | Risk Manager + Plant Manager |
| Dokument wygasający (30 dni) | Właściciel dokumentu |
| Wygasły dowód | Właściciel powiązanej kontroli |
| Wakat obowiązkowej roli | Compliance Officer + Plant Manager |
| Ocena dostawcy wygasająca (30 dni) | Wewnętrzny opiekun |

Niektóre powiadomienia są obowiązkowe i nie można ich dezaktywować (np. timery NIS2, eskalacja krytycznych zadań, czerwone ryzyka).

### Jak zmieniają się w zależności od profilu przypisanego do roli

Powiadomienia wysyłane dla roli zależą od **profilu powiadomień** przypisanego do tej roli (skonfigurowanego w Ustawieniach). Rola z profilem „Podstawowy" otrzymuje tylko obowiązkowe powiadomienia i krytyczne terminy. Rola z profilem „Pełny" otrzymuje również okresowe podsumowania i powiadomienia dotyczące modułów odniesienia.

### Jak konfigurować preferencje (tylko admin)

Przejdź do **Ustawienia → Profile powiadomień**:

1. Wybierz profil do modyfikacji lub kliknij **Nowy profil**
2. Skonfiguruj dla każdego typu zdarzenia: aktywny / nieaktywny, częstotliwość (natychmiastowa / dzienne podsumowanie / tygodniowe podsumowanie)
3. Przypisz profil do ról, które mają go używać
4. Zapisz

Konfiguracja obowiązuje natychmiast. Zmiany nie mają zastosowania wstecznego do już wysłanych powiadomień.

---

## 19. Ład organizacyjny (M00)

[Zrzut ekranu: schemat ról normatywnych]

### Jak przypisać rolę normatywną

Role normatywne to stanowiska wymagane przez frameworki (np. CISO, DPO, Risk Owner, Asset Owner). Aby przypisać właściciela:

1. Przejdź do **Ład organizacyjny → Schemat organizacyjny**
2. Znajdź rolę do przypisania (opcjonalnie użyj filtra według frameworku lub plant)
3. Kliknij **Przypisz właściciela**
4. Wybierz użytkownika z listy
5. Ustaw:
   - **Data rozpoczęcia**: od kiedy przypisanie ma moc
   - **Data wygaśnięcia** (opcjonalna): przydatna dla tymczasowych przydziałów lub zaplanowanych rotacji
6. Kliknij **Potwierdź przypisanie**

Przypisanie jest rejestrowane w śladzie audytu. Użytkownik otrzymuje powiadomienie e-mail z obowiązkami roli.

### Jak zastąpić właściciela (sukcesja)

Jeśli właściciel przechodzi na emeryturę, zmienia funkcję lub odchodzi z firmy, użyj mechanizmu sukcesji:

1. Z karty roli kliknij **Zarządzaj sukcesją**
2. Wybierz nowego właściciela
3. Ustaw **datę przejścia**
4. System automatycznie zarządza nakładaniem się: do daty przejścia stary właściciel pozostaje aktywny, od następnego dnia przejmuje nowy
5. Kliknij **Potwierdź sukcesję**

Stary właściciel otrzymuje powiadomienie o zakończeniu kadencji. Nowy właściciel otrzymuje powiadomienie o rozpoczęciu kadencji z listą obowiązków.

### Jak zakończyć rolę

Jeśli stanowisko nie jest już wymagane (np. zmiana zakresu normatywnego):

1. Z karty roli kliknij **Zakończ rolę**
2. Wpisz **uzasadnienie** (obowiązkowe — np. „Rola zlikwidowana po przeglądzie zakresu TISAX 2026")
3. Ustaw **datę zakończenia**
4. Jeśli są otwarte zadania przypisane do tej roli, system pyta jak nimi zarządzić (przypisz do innej roli lub pozostaw otwarte)
5. Kliknij **Potwierdź**

### Alerty o rolach wygasających i wakatach obowiązkowych ról

**Role wygasające**: jeśli przypisanie ma datę wygaśnięcia, 30 dni przed nią system wysyła powiadomienie do Compliance Officer i Plant Manager w celu zaplanowania odnowienia lub sukcesji.

**Wakaty obowiązkowych ról**: niektóre role są oznaczone jako obowiązkowe we frameworku (np. CISO dla ISO 27001). Jeśli obowiązkowa rola nie ma aktywnego właściciela:
- Na pulpicie pojawia się czerwony baner
- KPI compliance jest obniżany
- Generowane jest pilne zadanie przypisania

---

## 20. Ustawienia (tylko Administrator)

[Zrzut ekranu: strona ustawień admina]

Ta sekcja jest dostępna tylko dla użytkowników z rolą Administratora systemu lub Super Admin.

### Konfiguracja e-mail SMTP

1. Przejdź do **Ustawienia → E-mail → Konfiguracja SMTP**
2. Wypełnij:
   - **Host SMTP** (np. smtp.azienda.com)
   - **Port** (zazwyczaj 587 dla STARTTLS lub 465 dla SSL)
   - **Użytkownik** i **Hasło** — hasło jest szyfrowane AES-256 (FERNET) przed zapisaniem
   - **Domyślny nadawca** (np. noreply@grc.azienda.com)
   - **TLS/SSL**: wybierz typ szyfrowania
3. Kliknij **Zapisz konfigurację**

### Test połączenia e-mail

Po skonfigurowaniu SMTP:

1. Na tej samej stronie kliknij **Wyślij testowego e-maila**
2. Wpisz adres e-mail odbiorcy dla testu
3. Kliknij **Wyślij**
4. Sprawdź odbiór. Jeśli e-mail nie dotrze w ciągu 2 minut, kliknij **Wyświetl dziennik**, aby zobaczyć ewentualny błąd SMTP

### Profile powiadomień dla roli

Przejdź do **Ustawienia → Powiadomienia → Profile**:

1. Predefiniowane profile to: Podstawowy, Standardowy, Pełny, Cichy
2. Aby utworzyć niestandardowy profil, kliknij **Nowy profil**
3. Dla każdego typu powiadomienia ustaw: aktywny/nieaktywny i częstotliwość wysyłania
4. Przypisz profil do ról przez **Ustawienia → Role → wybierz rolę → Profil powiadomień**

### Polityki terminów (23 konfigurowalne typy)

Przejdź do **Ustawienia → Polityki → Terminy**. Możesz konfigurować czasy ostrzeżeń i domyślne terminy dla 23 typów elementów, w tym:

- Dowody według typu (logi: 30 dni, skany: 90 dni, certyfikaty: 365 dni)
- Dokumenty według typu (polityka: 365 dni, procedura: 730 dni)
- Wyniki audytu według powagi (Major NC: 30 dni, Minor NC: 90 dni, Obserwacja: 180 dni)
- Oceny dostawców (domyślnie 12 miesięcy)
- Plany BCP (domyślnie 12 miesięcy)
- Przegląd ryzyk (90 dni dla czerwonych ryzyk, 180 dni dla żółtych)

Modyfikacja tych wartości aktualizuje obliczenia dla wszystkich przyszłych elementów. Istniejące elementy zachowują terminy obliczone w momencie tworzenia.

---

## Role i uprawnienia

### Compliance Officer

Masz pełny dostęp do wszystkich modułów dla wszystkich plant w swoim zakresie. Jesteś odpowiedzialny za:

- Aktualizowanie biblioteki kontroli (M03)
- Koordynowanie przepływu dokumentów (M07)
- Monitorowanie zadań i terminów całego zespołu (M08)
- Zarządzanie incydentami NIS2 i zgłoszeniami ACN (M09)
- Przygotowywanie dokumentacji do audytów (M17)
- Generowanie raportów dla kierownictwa (M18)

### Risk Manager

Masz pełny dostęp do modułów ryzyka. Jesteś odpowiedzialny za:

- Nadzorowanie oceny ryzyka IT i OT (M06)
- Walidację BIA i wartości MTPD/RTO/RPO (M05)
- Uruchamianie i monitorowanie cykli PDCA (M11)
- Otrzymywanie alertów o ryzykach z wynikiem > 14

### Plant Manager

Masz dostęp do swojego plant. Jesteś odpowiedzialny za:

- Zatwierdzanie dokumentów na poziomie kierownictwa (M07)
- Otrzymywanie eskalacji o krytycznych przeterminowanych zadaniach
- Walidację decyzji o leczeniu ryzyka (M06)
- Uczestnictwo i zatwierdzanie przeglądu zarządu (M13)

### Plant Security Officer

Masz dostęp operacyjny do swojego plant. Jesteś odpowiedzialny za:

- Aktualizowanie statusu kontroli (M03)
- Wgrywanie dowodów (M07)
- Wypełnianie ocen ryzyka IT i OT (M06)
- Otwieranie i zarządzanie incydentami (M09)
- Realizację przypisanych zadań (M08)

### Audytor Zewnętrzny

Masz dostęp tylko do odczytu z tymczasowym tokenem. Możesz:

- Przeglądać kontrole i ich status (M03)
- Pobierać dokumenty i dowody (M07)
- Eksportować pakiet dowodów dla swojego audytu (M17)
- Każda Twoja akcja jest rejestrowana w śladzie audytu

Token ma datę wygaśnięcia: znajdziesz ją na górze interfejsu. Skontaktuj się z Compliance Officer, jeśli potrzebujesz przedłużenia.

---

## AI Engine — sugestie SI (M20)

> Moduł AI jest włączony tylko jeśli Twój administrator aktywował tę funkcję dla Twojego plant.

### Jak to działa

Gdy moduł AI jest aktywny, zobaczysz ramkę **Sugestia SI** w niektórych modułach — incydenty, aktywa, dokumenty, zadania. System analizuje kontekst i proponuje:

- **Sugerowaną klasyfikację** (np. powagę incydentu, krytyczność aktywa)
- **Szkic tekstu** (np. zgłoszenie ACN, polityka, RCA)
- **Proaktywny alert** (np. zadanie z wysokim ryzykiem opóźnienia)

### Co musisz zrobić

Sugestia SI nie ma żadnego efektu, dopóki jej **jawnie nie potwierdzisz**. Możesz:

- **Zaakceptować** sugestię taką, jaka jest — kliknij **Użyj tej sugestii**
- **Zmodyfikować** tekst, a następnie kliknąć **Użyj zmodyfikowanej wersji** — Twoja wersja nadpisuje wersję SI
- **Zignorować** sugestię i postępować ręcznie — ramka zamyka się bez efektów

> Każda interakcja (otrzymana sugestia, przyjęty tekst końcowy) jest rejestrowana w śladzie audytu, aby zapewnić identyfikowalność decyzji. SI nigdy nie podejmuje decyzji autonomicznie.

---

## Raportowanie i eksport (M18)

### Pulpit raportowania

Przejdź do **Audyt → Raportowanie**. Znajdziesz trzy poziomy pulpitów:

- **Operacyjny**: status zadań, kontrole według frameworku i plant, terminy
- **Ryzyko**: zagregowana mapa ciepła, 10 największych otwartych ryzyk
- **Wykonawczy**: compliance %, trend dojrzałości PDCA, gotowość do audytu

### Generowanie raportu PDF

1. Wybierz typ raportu (luka TISAX, compliance NIS2, SOA ISO 27001, BIA wykonawczy)
2. Wybierz plant i okres
3. Wybierz język raportu
4. Kliknij **Generuj** — PDF jest podpisywany znacznikiem czasu i hashem
5. Raport jest dostępny do pobrania w sekcji **Wygenerowane raporty**

Wszystkie wygenerowane raporty są rejestrowane w śladzie audytu.

---

## Załącznik: Często zadawane pytania

**Nie mogę znaleźć kontroli, która powinna być w moim frameworku.**
Sprawdź, czy wybrałeś właściwy plant w selektorze na górze. Jeśli framework jest aktywny dla tego plant, ale kontrola się nie pojawia, skontaktuj się z Compliance Officer — mogło nie zostać wygenerowane podczas aktywacji frameworku.

**Wgrałem dowód, ale kontrola nadal pokazuje „luka".**
Sprawdź, czy dowód jest powiązany z właściwą kontrolą (karta dowodu → sekcja „Objęte kontrole") i czy data wygaśnięcia jeszcze nie minęła.

**Timer NIS2 uruchomił się, ale incydent nie jest naprawdę incydentem NIS2.**
CISO ma 30 minut na wykluczenie obowiązku zgłoszenia. Jeśli jesteś CISO, otwórz kartę incydentu i kliknij **Wyklucz obowiązek NIS2**, podając uzasadnienie. Timery zatrzymują się, a decyzja jest rejestrowana w śladzie audytu.

**Ukończyłem zadanie, ale nadal pojawia się jako otwarte.**
Niektóre zadania zamykają się automatycznie po zakończeniu akcji w module źródłowym. Jeśli zadanie jest ręczne, musisz je jawnie zamknąć z karty zadania → **Oznacz jako ukończone**.

**Dokument, który zatwierdziłem, pojawia się teraz jako „w przeglądzie".**
Został aktywowany wyzwalacz nadzwyczajnego przeglądu — prawdopodobnie powiązany z incydentem, wynikiem audytu lub zmianą normatywną. Sprawdź notatki na karcie dokumentu, aby zrozumieć przyczynę.

**Nie mogę ustawić kontroli jako N/A.**
Dla kontroli TISAX L3 status N/A wymaga podpisu co najmniej dwóch ról (podwójne blokowanie). Jeśli jesteś pierwszym zatwierdzającym, kontrola pozostaje w oczekiwaniu na drugi podpis. Jeśli jesteś jedynym właścicielem, skontaktuj się z CISO w celu współpodpisania.

**Sugestia SI już się nie pojawia.**
Moduł AI mógł zostać wyłączony przez administratora dla Twojego plant, lub konkretna funkcja nie jest aktywna. Skontaktuj się z Compliance Officer lub Administratorem systemu.

**Anulowałem audyt przez pomyłkę. Czy mogę go przywrócić?**
Nie, anulowanie jest nieodwracalne. Możesz jednak utworzyć nowy audyt dla tego samego kwartału i odtworzyć ewentualnie utracone wyniki. Skontaktuj się z Compliance Officer, który może wyświetlić anulowane wyniki w archiwum, aby odzyskać informacje.

**Wynik mojego ryzyka zmienił się bez mojej interwencji.**
Wynik rezydualny jest przeliczany automatycznie, gdy zmienia się status powiązanych kontroli. Jeśli dowód wygasł, kontrola wraca do „częściowej" i może to zwiększyć ryzyko rezydualne. Sprawdź kontrole powiązane z ryzykiem i zaktualizuj dowody.

**Nie otrzymuję powiadomień e-mail.**
Najpierw sprawdź folder ze spamem. Jeśli e-maile w ogóle nie docierają, skontaktuj się z administratorem systemu, aby sprawdzić konfigurację SMTP i profil powiadomień przypisany do Twojej roli.

**Jak mogę zobaczyć historię zmian na aktywach lub dokumentach?**
Każda karta ma sekcję **Ślad audytu** lub **Historia zmian** na dole. Kliknij ją, aby zobaczyć wszystkie zarejestrowane akcje z datą, użytkownikiem i szczegółem zmiany.

**Program audytu pokazuje status „Do aktualizacji". Co mam zrobić?**
Status „Do aktualizacji" oznacza, że program został utworzony, ale niektóre informacje (np. audytor nieprzypisany do kwartału, brakujące daty) wymagają uzupełnienia przed zatwierdzeniem programu. Otwórz program i szukaj pól podświetlonych na żółto.

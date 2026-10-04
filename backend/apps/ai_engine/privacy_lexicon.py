"""Lessici per la tokenizzazione dei prompt verso l'IA (vedi sanitizer.py).

FIRST_NAMES: nomi propri frequenti nelle lingue dei siti (IT, EN, FR, PL, TR,
più arabi/maghrebini). Servono a riconoscere persone NON registrate in GRC
("Mario Bianchi ha segnalato"): un nome della lista seguito da una parola con
iniziale maiuscola viene trattato come "Nome Cognome". Esclusi i nomi che sono
anche parole comuni (es. Will, Mark, Rosa, Vera, Can, Deniz), che
produrrebbero troppi falsi positivi a inizio frase.
"""

FIRST_NAMES = frozenset("""
alessandro alessandra alberto alessio alice andrea angela angelo anna antonella antonio
arianna barbara beatrice benedetta bruno carla carlo carmela carmine caterina cesare
chiara claudia claudio cristian cristina daniela daniele dario davide debora domenico
elena elisa elisabetta emanuela emanuele enrico enzo erika ettore fabio fabrizio federica
federico filippo francesca francesco franco gabriele gabriella giacomo gianluca gianni
giorgia giorgio giovanna giovanni giulia giuliana giuliano giulio giuseppe giuseppina
graziella guido ilaria irene jessica laura lorenzo luca lucia luciana luciano luigi luisa
manuela marcello marco margherita maria marina mario marta martina massimo matteo mattia
maurizio michela michele mirko monica nadia nicola nicoletta noemi paola paolo patrizia
pietro raffaele riccardo rita roberta roberto rocco salvatore sara serena sergio silvia
simona simone sofia stefania stefano tiziana tommaso valentina valerio vincenzo viola
vittoria walter
james john robert michael william david richard joseph thomas charles christopher daniel
matthew anthony donald steven paul andrew joshua kenneth kevin brian george edward ronald
timothy jason jeffrey ryan jacob gary nicholas eric jonathan stephen larry justin scott
brandon benjamin samuel gregory alexander patrick jack dennis jerry tyler aaron henry
peter adam nathan zachary kyle mary patricia jennifer linda elizabeth susan sarah karen
nancy lisa betty margaret sandra ashley kimberly emily donna michelle carol amanda melissa
deborah stephanie rebecca sharon cynthia kathleen amy shirley angela helen anna brenda
pamela nicole emma samantha katherine christine rachel catherine olivia julia victoria
oliver harry charlie sophie chloe lucy
jean pierre michel philippe alain nicolas christophe patrick laurent frederic sebastien
stephane olivier julien thierry eric pascal david francois jacques bernard antoine
guillaume mathieu vincent maxime thomas romain hugo louis lucas gabriel arthur jules
marie nathalie isabelle sylvie catherine francoise martine christine monique valerie
sandrine sophie celine stephanie aurelie emilie julie camille manon chloe lea ines
amelie helene veronique brigitte nadine
piotr krzysztof andrzej tomasz pawel jan michal marcin grzegorz jozef lukasz adam
zbigniew jerzy tadeusz mateusz dariusz mariusz wojciech ryszard kazimierz marek jakub
stanislaw rafal robert maciej sebastian bartosz kamil damian janusz przemyslaw artur
anna maria katarzyna malgorzata agnieszka barbara krystyna ewa elzbieta zofia teresa
magdalena joanna janina monika danuta jadwiga aleksandra halina irena beata marta
dorota karolina jolanta iwona natalia justyna grazyna urszula renata agata paulina
mehmet mustafa ahmet ali huseyin hasan ibrahim ismail osman yusuf murat omer ramazan
halil suleyman abdullah mahmut recep salih fatih kadir emre hakan burak serkan kemal
cem onur volkan tolga baris selim kaan oguz ozan levent erkan sinan berk eren
fatma ayse emine hatice zeynep elif meryem sultan zehra hulya leyla esra merve busra
ozlem gulsen sevgi derya ebru tugba seda burcu gamze pinar asli dilek nur sibel
mohamed mohammed muhammad ahmed mahmoud youssef yousef karim amine mehdi sami walid
hichem nabil khaled tarek omar hamza bilal anis aymen wassim slim sofiane rachid
fatima khadija amina leila salma meriem nour rania sana yasmine ines imen asma hela
""".split())

# Titoli che precedono un nome di persona (match senza distinzione maiuscole).
# Le abbreviazioni ambigue richiedono il punto: "MS Teams", "Arch Linux" e
# "Dr Web" non sono persone.
TITLES_BEFORE = (
    r"sig\.?(?:ra|na)?|signor[ae]?|dott\.?(?:ssa)?|dr\.|ing\.|avv\.?|geom\.?|arch\."
    r"|prof\.?(?:ssa)?|rag\.|mr\.|mrs\.|ms\.|mme\.?|mlle\.?|monsieur|madame"
    r"|herr|frau|pan|pani|bay|bayan"
)
# Titoli turchi che seguono il nome ("Ahmet Bey").
TITLES_AFTER = r"bey|hanım|hanim"

# Parole con iniziale maiuscola che dopo un nome proprio NON sono un cognome
# (evita "Maria Vergine"/"Santa Maria Hotel" solo in parte; il resto è accettato
# come falso positivo: meglio un token in più che un nome che esce).
NOT_SURNAMES = frozenset("""
spa srl srls sas snc ltd gmbh sa sarl sp zoo as inc llc co the il lo la le gli i un una
""".split())

# Nomi di asset/fornitori troppo generici per essere tokenizzati come entità:
# sostituirli ovunque toglierebbe significato al testo senza proteggere nulla.
GENERIC_NAMES = frozenset("""
server firewall router switch erp crm mes scada plc hmi nas san vpn wifi wlan lan wan
email mail posta backup database db storage laptop notebook desktop pc stampante
printer sito website portale portal intranet cloud office sharepoint teams
active directory ad dns dhcp ntp proxy gateway telefono phone smartphone tablet
""".split())

# Prefissi di norme e cataloghi: "ISO27001", "IEC62443" non sono hostname.
STANDARD_PREFIXES = frozenset("""
iso iec nist cve cwe tisax nis vda gdpr soc pci enisa rfc en uni cei sp cis capec
mitre owasp acn isa itsec bsi din bs ansi ieee etsi cobit itil hipaa sox dora
aes sha rsa tls ssl des ecc ecdsa ecdh dh fips base covid win office utf
""".split())

# Parole che dopo un numero di 5 cifre indicano un importo, non una città.
CURRENCY_WORDS = frozenset("""
euro eur usd dollari dollars pln zloty zł try lira lire tnd dinar dinari gbp sterline chf
""".split())

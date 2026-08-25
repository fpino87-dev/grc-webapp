"""
Postura attesa di un'entità monitorata.

Il modulo confrontava ogni dominio con un'aspettativa universale implicita —
«ogni dominio deve avere HTTPS, SPF, DMARC» — invece che con l'aspettativa
dichiarata per quel dominio specifico. È la differenza fra uno scanner, che
dice cosa vede, e un controllo di conformità, che dice cosa dovrebbe esserci e
non c'è. Senza sapere cosa dovrebbe esserci, ogni assenza è ambigua: l'assenza
di DMARC su un dominio senza posta è la configurazione corretta, sullo stesso
dominio che manda fatture è un buco.

Qui vive quella risposta. Tre stati e non due: dichiarato sì, dichiarato no,
non dichiarato — e in quest'ultimo caso si ricade su ciò che la scansione ha
effettivamente rilevato, che è il comportamento storico.
"""


def expects_mail(entity, scan) -> bool:
    """
    Il dominio è atteso inviare/ricevere posta?

    Dichiarato `no`  → mai, nemmeno se un MX viene rilevato (può essere l'MX di
                       un provider che ospita il dominio senza che ci passi la
                       posta aziendale).
    Dichiarato `yes` → sempre, anche senza MX: un dominio usato solo come
                       mittente (From:) non ha MX ma DEVE avere SPF e DMARC,
                       ed è esattamente il caso più abusato dal phishing.
    Non dichiarato   → si ricade sulla rilevazione.
    """
    from apps.osint.models import ExpectedPosture

    declared = getattr(entity, "expected_mail", ExpectedPosture.UNKNOWN)
    if declared == ExpectedPosture.NO:
        return False
    if declared == ExpectedPosture.YES:
        return True
    return getattr(scan, "mx_present", None) is True


def expects_web(entity, scan) -> bool:
    """
    Il dominio è atteso servire contenuti web?

    Dichiarato `no` → nessun finding sulla postura HTTPS: un dominio registrato
    a scopo difensivo (typosquatting, brand protection) non deve servire nulla,
    e segnalarlo perché «non ha HTTPS» è rumore.
    """
    from apps.osint.models import ExpectedPosture

    declared = getattr(entity, "expected_web", ExpectedPosture.UNKNOWN)
    if declared == ExpectedPosture.NO:
        return False
    if declared == ExpectedPosture.YES:
        return True
    # Non dichiarato: è atteso servire web se qualcosa risponde. Vale anche un
    # certificato scaduto o non valido (`ssl_valid` valorizzato): la sua sola
    # presenza dimostra che un servizio HTTPS c'è. Senza questa condizione gli
    # scan precedenti all'introduzione di `https_available` — dove il campo è
    # nullo — verrebbero letti come «dominio che non serve web» e la dimensione
    # SSL sarebbe azzerata a posteriori su tutto lo storico.
    return (
        getattr(scan, "https_available", None) is True
        or getattr(scan, "http_only", None) is True
        or getattr(scan, "ssl_valid", None) is not None
    )

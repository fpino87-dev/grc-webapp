"""Ordine del giorno obbligatorio del riesame di direzione (ISO/IEC 27001:2022 §9.3.2).

I titoli sono traducibili: il verbale li stampa nella lingua di chi lo
scarica. L'interfaccia traduce per `code`
(`management_review.agenda.items.<code>`).
"""

from django.utils.translation import gettext_lazy as _

ISO_AGENDA = [
    ("azioni_precedenti", "a", _("Stato delle azioni dei riesami precedenti")),
    ("contesto", "b", _("Cambiamenti nei fattori esterni e interni rilevanti per il SGSI")),
    ("parti_interessate", "c", _("Cambiamenti nelle esigenze e aspettative delle parti interessate")),
    ("prestazioni", "d", _("Prestazioni della sicurezza delle informazioni: non conformità e azioni "
                         "correttive, monitoraggio e misurazioni, audit, obiettivi")),
    ("feedback_parti", "e", _("Feedback delle parti interessate")),
    ("rischi", "f", _("Risultati della valutazione del rischio e stato del piano di trattamento")),
    ("miglioramento", "g", _("Opportunità di miglioramento continuo")),
]

ISO_AGENDA_CODES = [code for code, _clause, _title in ISO_AGENDA]
ISO_AGENDA_TITLES = {code: title for code, _clause, title in ISO_AGENDA}
ISO_AGENDA_CLAUSE = {code: clause for code, clause, _title in ISO_AGENDA}

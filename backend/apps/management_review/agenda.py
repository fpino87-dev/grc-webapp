"""Ordine del giorno obbligatorio del riesame di direzione (ISO/IEC 27001:2022 §9.3.2).

I titoli qui sono quelli usati nella relazione (IT); l'interfaccia traduce per
`code` (`management_review.agenda.items.<code>`).
"""

ISO_AGENDA = [
    ("azioni_precedenti", "a", "Stato delle azioni dei riesami precedenti"),
    ("contesto", "b", "Cambiamenti nei fattori esterni e interni rilevanti per il SGSI"),
    ("parti_interessate", "c", "Cambiamenti nelle esigenze e aspettative delle parti interessate"),
    ("prestazioni", "d", "Prestazioni della sicurezza delle informazioni: non conformità e azioni "
                         "correttive, monitoraggio e misurazioni, audit, obiettivi"),
    ("feedback_parti", "e", "Feedback delle parti interessate"),
    ("rischi", "f", "Risultati della valutazione del rischio e stato del piano di trattamento"),
    ("miglioramento", "g", "Opportunità di miglioramento continuo"),
]

ISO_AGENDA_CODES = [code for code, _, _ in ISO_AGENDA]
ISO_AGENDA_TITLES = {code: title for code, _, title in ISO_AGENDA}
ISO_AGENDA_CLAUSE = {code: clause for code, clause, _ in ISO_AGENDA}

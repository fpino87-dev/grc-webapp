def generate_procedure_document(control, lang: str, user) -> bytes:
    """
    Generates a .docx procedure document for a Control via AI.
    Returns raw bytes of the Word document.
    """
    from apps.ai_engine.router import route
    from ..document_generator import markdown_to_docx

    _LANG_NAMES = {
        "it": "italiano",
        "en": "English",
        "fr": "français",
        "pl": "polski",
        "tr": "Türkçe",
    }
    lang_name = _LANG_NAMES.get(lang, "italiano")

    title_loc = control.get_title(lang) or control.external_id
    desc_loc = control.tr("description", lang)

    prompt = (
        f"Sei un esperto GRC certificato ISO 27001 e NIS2. "
        f"Genera un documento formale di PROCEDURA operativa per il seguente controllo di sicurezza.\n\n"
        f"Framework: {control.framework.code} — {control.framework.name}\n"
        f"Codice controllo: {control.external_id}\n"
        f"Titolo: {title_loc}\n"
        f"Descrizione: {desc_loc}\n\n"
        f"Regole OBBLIGATORIE:\n"
        f"- Basati ESCLUSIVAMENTE sui requisiti reali del framework {control.framework.code}\n"
        f"- NON inventare requisiti normativi non presenti nel controllo\n"
        f"- Per ogni requisito cita la specifica clausola della norma\n"
        f"- Lingua del documento: {lang_name}\n\n"
        f"Struttura obbligatoria (usa heading Markdown ##):\n"
        f"1. Scopo\n"
        f"2. Ambito di applicazione\n"
        f"3. Riferimenti normativi\n"
        f"4. Ruoli e responsabilità\n"
        f"5. Procedura (passo per passo)\n"
        f"6. KPI e metriche di verifica\n"
        f"7. Frequenza di revisione\n\n"
        f"Output: solo Markdown, nessun preambolo, nessuna spiegazione."
    )

    result = route(
        task_type="generate_procedure",
        prompt=prompt,
        user=user,
        entity_id=control.pk,
        module_source="M03",
        sanitize=False,  # dati normativi puri — nessun PII
        max_tokens=4096,
        timeout=300,
    )

    md_text = result["text"]
    doc_title = f"{control.external_id} — {title_loc}"
    return markdown_to_docx(md_text, title=doc_title)

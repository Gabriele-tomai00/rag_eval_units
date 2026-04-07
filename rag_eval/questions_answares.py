samples = [
        {
            "question": "sede dell'università di Trieste",
            "grading_notes": "deve menzionare Piazzale Europa e Trieste",
            "ground_truth": (
                "La sede principale dell'Università degli Studi di Trieste si trova a Trieste, "
                "in Piazzale Europa 1, in un'area sopraelevata rispetto al centro della città."
            ),
        },
        {
            "question": "in quale edificio, piano e aula stampare all università",
            "grading_notes": "edificio H3, 5 piano, aule informatiche",
            "ground_truth": (
                "È possibile stampare presso l'edificio H3, situato nel polo di Piazzale Europa, "
                "al quinto piano all'interno delle aule informatiche."
            ),
        },
        {
            "question": "obiettivi formativi ingegneria elettronica e informatica: Capacità di applicare conoscenza e comprensione per curriculum Ingegneria biomedica",
            "grading_notes": "esercitazioni, laboratori e strumenti didattici",
            "ground_truth": (
                "L'obiettivo è formare laureati capaci di affrontare problemi dell'ingegneria dell'informazione e biomedica. "
                "Lo studio è affiancato da esercitazioni scritte e in laboratorio. Gli strumenti includono lezioni ordinarie, "
                "integrative, seminari ed esercitazioni, con valutazioni tramite verifiche scritte, orali e prova finale."
            ),
        },
        {
            "question": "titolo di studio richiesto per immatricolazione",
            "grading_notes": "diploma superiore e nota sui titoli esteri",
            "ground_truth": (
                "Il titolo richiesto è il diploma di scuola media superiore o titolo estero equipollente. "
                "Per i titoli esteri è necessario verificare la validità presso la sezione Studenti Internazionali."
            ),
        },
        {
            "question": "quali sono i vari curriculum del corso Scienze e Tecnologie per l'ambiente e la natura",
            "grading_notes": "Ambientale, Biologico e Didattico",
            "ground_truth": "I curriculum sono tre: Ambientale, Biologico e Didattico.",
        },
        {
            "question": "contatti e ufficio tasse",
            "grading_notes": "indirizzo, telefono, mail e orari sportello",
            "ground_truth": (
                "Ufficio Applicativi per la carriera dello studente e i contributi universitari: Piazzale Europa 1, Edificio A. "
                "Tel: +39 040 558 3731 (mar, mer, ven 12-13). Email: tasse.studenti@amm.units.it. "
                "Sportello su prenotazione (EasyPlanning): Lunedì 15:00-16:40 e Giovedì 09:00-11:10."
            ),
        },
        {
            "question": "parlami dell iniziativa Climbing for Climate (CFC)",
            "grading_notes": "RUS, CAI e sensibilizzazione riscaldamento globale",
            "ground_truth": (
                "Iniziativa promossa da RUS e CAI per sensibilizzare sul riscaldamento globale. "
                "Il nome richiama i clorofluorocarburi (CFC), gas responsabili del buco nell'ozono banditi dal Protocollo di Montreal. "
                "L'ateneo partecipa organizzando eventi sul territorio."
            ),
        },
        {
            "question": "inizio e fine lezioni primo semestre SCIENZE INTERNAZIONALI E DIPLOMATICHE",
            "grading_notes": "22 settembre - 19 dicembre 2025 (1 ottobre per I anno)",
            "ground_truth": (
                "Le lezioni iniziano il 22 settembre 2025 (il 1 ottobre per gli studenti del primo anno) "
                "e terminano il 19 dicembre 2025."
            ),
        },
        {
            "question": "inizio e fine lezioni primo semestre SCIENZE E TECNICHE PSICOLOGICHE",
            "grading_notes": "22/29 settembre - 19 dicembre 2025",
            "ground_truth": (
                "Il primo semestre inizia il 29 settembre 2025 per il I anno e il 22 settembre per gli anni successivi, "
                "con termine il 19 dicembre 2025 per tutti."
            ),
        },
        {
            "question": "dove trovare il materiale didattico del corso di DIGITAL ELECTRONICS AND DEVICES",
            "grading_notes": "Moodle, MS Teams e link docente",
            "ground_truth": (
                "Il materiale (slide ed esercizi) è disponibile su Moodle e MS Teams o sul sito del docente: "
                "http://www2.units.it/carrato/didatt/DSE_web/index.html"
            ),
        },
        {
            "question": "dove trovare il materiale didattico del corso di Cybersecurity",
            "grading_notes": "link bartolialberto.github.io",
            "ground_truth": (
                "Il materiale del corso è disponibile sul sito: https://bartolialberto.github.io/CybersecurityCourse/"
            ),
        },
        {
            "question": "l aula T dell'edificio A è libera il giorno 20 marzo 2026?",
            "grading_notes": "ammettere mancanza di info",
            "ground_truth": "Non ho informazioni sulla disponibilità dell'aula T per quella data specifica.",
        },
        {
            "question": "dimmi i corsi disponibili del dipartimento di musicologia",
            "grading_notes": "ammettere mancanza di info",
            "ground_truth": "Non dispongo di informazioni sui corsi del dipartimento di Musicologia.",
        },
    ]
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
        {
            "question": "sono uno studente, come accedo a teams per vedere videolezioni",
            "grading_notes": "deve spiegare come usare le credenziali",
            "ground_truth": (
                "Per accedere utilizza le credenziali di Ateneo nel seguente formato: userid@ds.units.it "
                "Esempio:"
                "s123456@ds.units.it seguita dalla password utilizzata per la posta elettronica ed i servizi online di Esse3. "
                "È possibile digitare anche solo una parte del nome e si possono usare più filtri assieme"
            ),
        },
        {
            "question": "Chi amministra le risorse di un corso interdipartimentale?",
            "grading_notes": "deve citare il dipartimento di gestione",
            "ground_truth": (
                "Il dipartimento di gestione, individuato dal Consiglio di Amministrazione "
                "al momento dell'attivazione del corso (comma 6). "
            ),
        },
        {
            "question": "Come vengono elette le rappresentanze studentesche nei corsi interdipartimentali?",
            "grading_notes": "deve citare il dipartimento di gestione",
            "ground_truth": (
                "Le modalità di elezione delle rappresentanze studentesche nei consigli di dipartimento "
                "sono definite dal regolamento degli studenti (comma 7)."
            ),
        },
        {
            "question": "Quali attività promuove l'Università per facilitare l'inserimento nel mondo del lavoro?",
            "grading_notes": "La risposta deve menzionare orientamento, tutorato e associazioni di ex-alunni.",
            "ground_truth": (
                "L'Università cura le attività di orientamento e tutorato e attiva servizi intesi ad agevolare "
                "l'inserimento nel mondo del lavoro di studenti e laureati. Favorisce inoltre la costituzione "
                "di associazioni di ex-alunni, finalizzate al mantenimento di relazioni con l'Ateneo e al "
                "sostegno delle sue attività istituzionali."
            ),
        },
        {
            "question": "Cosa gestisce il sistema bibliotecario e museale di Ateneo?",
            "grading_notes": "La risposta deve menzionare l'accesso alle risorse informative online e il trasferimento delle conoscenze.",
            "ground_truth": (
                "Il sistema bibliotecario e museale di Ateneo favorisce l'accesso alle risorse informative online "
                "e assicura il trasferimento delle conoscenze, nell'ambito della conservazione, sviluppo, "
                "valorizzazione e gestione del patrimonio bibliografico, documentario e archivistico, "
                "delle raccolte e dei musei dell'Università."
            ),
        },
        {
            "question": "Quali forme di sostegno economico eroga l'Università agli studenti?",
            "grading_notes": "La risposta deve menzionare borse di studio, premi di studio, contributi e agevolazioni.",
            "ground_truth": (
                "L'Università promuove, anche con il sostegno di soggetti esterni, l'istituzione di borse e premi "
                "di studio per studenti capaci e meritevoli. Eroga inoltre contributi e agevolazioni per studenti "
                "che collaborino nelle attività di servizio."
            ),
        },
        {
            "question": "Chi può proporre il conferimento del titolo di Dottore di Ricerca honoris causa?",
            "grading_notes": "La risposta deve menzionare il Rettore e il Collegio dei docenti del Dottorato, con la maggioranza dei due terzi.",
            "ground_truth": (
                "Il conferimento può essere proposto dal Rettore o dal Collegio dei docenti del Dottorato di "
                "riferimento, previa deliberazione assunta con la maggioranza dei due terzi dei componenti."
            ),
        },
        {
            "question": "Quanti dottorati honoris causa può conferire l'Ateneo per ogni anno accademico?",
            "grading_notes": "La risposta deve indicare il limite massimo di un solo dottorato honoris causa per anno accademico.",
            "ground_truth": (
                "L'Ateneo può conferire al massimo un solo Dottorato honoris causa per ogni anno accademico, "
                "e comunque nei limiti stabiliti dal Ministero."
            ),
        },
        {
            "question": "Quali diritti attribuisce il diploma di Dottorato honoris causa?",
            "grading_notes": "La risposta deve specificare che il diploma è equiparato ex lege al dottorato ordinario e ne attribuisce tutti i diritti.",
            "ground_truth": (
                "Il diploma di Dottorato honoris causa attribuisce tutti i diritti del Dottorato ordinario, "
                "in quanto è equiparato ex lege al titolo normalmente conseguito."
            ),
        },
        {
            "question": "In quali casi una proposta di dottorato honoris causa non viene presa in considerazione?",
            "grading_notes": "La risposta deve indicare che la proposta è esclusa se il candidato è già in possesso di un dottorato ordinario o honoris causa della stessa tipologia.",
            "ground_truth": (
                "Non vengono prese in considerazione le proposte inerenti a persone già in possesso di un "
                "diploma di Dottorato di Ricerca ordinario o honoris causa della stessa tipologia."
            ),
        },
        {
            "question": "Per quanto tempo può essere incrementata la borsa di dottorato per soggiorno all'estero?",
            "grading_notes": "La risposta deve menzionare l'incremento del 50%, il limite di 12 mesi ordinario e il limite esteso di 18 mesi per dottorati in convenzione o co-tutela.",
            "ground_truth": (
                "L'importo della borsa è incrementato nella misura massima del 50% per un periodo di soggiorno "
                "all'estero complessivo non superiore a 12 mesi. Il periodo può essere esteso fino a un massimo "
                "complessivo di 18 mesi per i dottorati in convenzione o per i dottorandi in co-tutela con soggetti esteri."
            ),
        },
        {
            "question": "Chi ha già usufruito di una borsa di dottorato nel sistema universitario italiano può ottenerne un'altra?",
            "grading_notes": "La risposta deve indicare chiaramente che non è possibile usufruire di una seconda borsa di dottorato, anche se la prima è stata fruita solo parzialmente.",
            "ground_truth": (
                "Chi ha già usufruito di una borsa di dottorato nell'ambito del sistema universitario italiano, "
                "anche parzialmente, non può usufruirne una seconda volta."
            ),
        },
        {
            "question": "Cosa succede alla borsa di dottorato in caso di rinuncia da parte del dottorando?",
            "grading_notes": "La risposta deve menzionare la possibilità di assegnare la borsa a un dottorando privo di borsa dello stesso ciclo e corso, e il reinvestimento dell'importo non utilizzato.",
            "ground_truth": (
                "In caso di rinuncia alla borsa, di mancato rinnovo o di rinuncia agli studi, la borsa può essere "
                "assegnata, nella sua quota totale o residua, su proposta del Collegio dei docenti, a un dottorando "
                "privo di borsa dello stesso ciclo e dello stesso Corso. In ogni caso l'importo non utilizzato è "
                "reinvestito dal soggetto che ha attivato il Corso per il finanziamento di dottorati di ricerca."
            ),
        },
        {
            "question": "Quali conseguenze può avere il rifiuto del dottorando di dedicarsi al tema di ricerca assegnato?",
            "grading_notes": "La risposta deve menzionare la possibilità di decadenza dal dottorato oppure la revoca della borsa con attribuzione di un nuovo tema e supervisore, senza prolungamento della durata.",
            "ground_truth": (
                "Il Collegio dei docenti, sentito il dottorando, può disporre la decadenza dal dottorato oppure "
                "la revoca della borsa e l'attribuzione al dottorando di un nuovo tema di ricerca e di un nuovo "
                "supervisore, senza prolungamento della durata di 36 mesi del dottorato."
            ),
        },
        {
            "question": "Quali sono gli insegnamenti previsti nel semestre aperto per l'accesso a Medicina e Odontoiatria?",
            "grading_notes": "La risposta deve elencare i tre insegnamenti: Chimica e propedeutica biochimica, Fisica e Biologia, ciascuno da 6 CFU.",
            "ground_truth": (
                "Il semestre aperto prevede la frequenza e il superamento di tre insegnamenti da 6 CFU ciascuno: "
                "Chimica e propedeutica biochimica, Fisica e Biologia."
            ),
        },
        {
            "question": "Qual è il contributo economico richiesto per l'iscrizione al semestre aperto di Medicina?",
            "grading_notes": "La risposta deve indicare il contributo forfettario di 250 euro e la possibilità di ricalcolo in base all'ISEE universitario.",
            "ground_truth": (
                "Per l'iscrizione al semestre aperto è previsto un contributo forfettario unico a livello nazionale "
                "di 250 euro. L'importo verrà ricalcolato in un secondo momento in base all'ISEE Universitario "
                "e agli altri casi di esonero totale o parziale previsti dalla normativa vigente."
            ),
        },
        {
            "question": "Cosa succede a chi non risulta in posizione utile in graduatoria dopo il semestre aperto?",
            "grading_notes": "La risposta deve menzionare la possibilità di accedere a un corso affine scelto in fase di iscrizione, in base alla posizione raggiunta e ai posti disponibili.",
            "ground_truth": (
                "Chi non risulta in posizione utile in graduatoria può accedere, sulla base della posizione "
                "raggiunta e dei posti disponibili, al corso affine scelto in fase di iscrizione."
            ),
        },
        {
            "question": "Con quanto anticipo minimo deve essere inviato il summary al professore per la fast track?",
            "grading_notes": "La risposta deve indicare almeno una settimana prima dell'ultima data utile per la registrazione del tirocinio.",
            "ground_truth": (
                "Il summary deve essere inviato per email con almeno una settimana di anticipo rispetto "
                "all'ultima data utile per la registrazione del tirocinio, indicando nello stesso email "
                "tale data, determinata contattando la segreteria studenti."
            ),
        },
    ]
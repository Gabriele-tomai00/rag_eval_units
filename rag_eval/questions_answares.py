samples = [
        {
            "question": "dove si trova la sede principale dell'ateneo",
            "grading_notes": "deve menzionare Piazzale Europa e Trieste",
            "ground_truth": (
                "La sede principale dell'Università degli Studi di Trieste si trova a Trieste, "
                "in Piazzale Europa 1, in un'area sopraelevata rispetto al centro della città."
            ),
            "source": "https://portale.units.it/it/ateneo/campus",
        },
        {
            "question": "edificio, piano e aula stampare all università",
            "grading_notes": "edificio H3, 5 piano, aule informatiche",
            "ground_truth": (
                "È possibile stampare presso l'edificio H3, situato nel polo di Piazzale Europa, "
                "al quinto piano all'interno delle aule informatiche."
            ),
            "source": "https://portale.units.it/it/ateneo/campus/trieste/piazzale-europa-polo/aula-informatica",
        },
        {
            "question": "requisiti: titolo di studio richiesto per immatricolazione a ingegneria elettronica e informatica",
            "grading_notes": "diploma superiore e nota sui titoli esteri",
            "ground_truth": (
                "Il titolo richiesto è il diploma di scuola media superiore o titolo estero equipollente. "
                "Per i titoli esteri è necessario verificare la validità presso la sezione Studenti Internazionali."
            ),
            "source": "https://lauree.units.it/it/0320106200800001/come-iscriversi",
        },
        {
            "question": "i curricula del corso Scienze e Tecnologie per l'ambiente e la natura",
            "grading_notes": "Ambientale, Biologico e Didattico",
            "ground_truth": "I curriculum sono tre: Ambientale, Biologico e Didattico.",
            "source": "https://www.biologia.units.it/index.php?/corsi/5/Laurea-in-Scienze-e-Tecnologie-per-lambiente-e-la-natura"
        },
        {
            "question": "i 3 docenti tutor dei 3 curricula del corso Scienze e Tecnologie per l'ambiente e la natura",
            "grading_notes": "Deve indicare almeno il nome del professore, relativo a ogni curricula",
            "ground_truth": "Curriculum Biologico: Prof. Stanislao Bevilacqua. Curriculum Ambientale: Prof. Pieluigi Barbieri.",
            "source": "https://www.biologia.units.it/index.php?/corsi/5/Laurea-in-Scienze-e-Tecnologie-per-lambiente-e-la-natura"
        },
        {
            "question": "contatti orari e indirizzo Ufficio Applicativi per la carriera dello studente e i contributi universitari",
            "grading_notes": "indirizzo, telefono, mail e orari sportello",
            "ground_truth": (
                "Ufficio Applicativi per la carriera dello studente e i contributi universitari: Piazzale Europa 1, Edificio A. "
                "Tel: +39 040 558 3731 (mar, mer, ven 12-13). Email: tasse.studenti@amm.units.it. "
                "Sportello su prenotazione (EasyPlanning): Lunedì 15:00-16:40 e Giovedì 09:00-11:10."
            ),
            "source": "https://portale.units.it/it/studiare/contributi/lauree-magistrali-e-magistrali-ciclo-unico"
        },
        {
            "question": "iniziativa Climbing for Climate (CFC)",
            "grading_notes": "RUS, CAI e sensibilizzazione riscaldamento globale",
            "ground_truth": (
                "Iniziativa promossa da RUS e CAI per sensibilizzare sul riscaldamento globale. "
                "Il nome richiama i clorofluorocarburi (CFC), gas responsabili del buco nell'ozono banditi dal Protocollo di Montreal. "
                "L'ateneo partecipa organizzando eventi sul territorio."
            ),
            "source": "https://portale.units.it/it/terza-missione/sostenibilita"
        },
        {
            "question": "inizio e fine lezioni primo semestre SCIENZE INTERNAZIONALI E DIPLOMATICHE",
            "grading_notes": "22 settembre - 19 dicembre 2025 (1 ottobre per I anno)",
            "ground_truth": (
                "Le lezioni iniziano il 22 settembre 2025 (il 1 ottobre per gli studenti del primo anno) "
                "e terminano il 19 dicembre 2025."
            ),
            "source": "https://degree.units.it/it/0320106203600002/area-studenti/calendario-didattico"
        },
        {
            "question": "inizio e fine lezioni primo semestre SCIENZE E TECNICHE PSICOLOGICHE",
            "grading_notes": "22/29 settembre - 19 dicembre 2025",
            "ground_truth": (
                "Il primo semestre inizia il 29 settembre 2025 per il I anno e il 22 settembre per gli anni successivi, "
                "con termine il 19 dicembre 2025 per tutti."
            ),
            "source": "https://degree.units.it/it/0320106202400001/area-studenti/calendario-didattico"
        },
        {
            "question": "dove si trova il materiale didattico corso Cybersecurity di Bartoli",
            "grading_notes": "deve indicare che si trova sul sito del corso e su Microsoft Teams",
            "ground_truth": (
                "Il materiale didattico per il corso di Cybersecurity è disponibile sul sito del corso, dove si trova il programma dettagliato e molto altro materiale aggiuntivo. Le slide sono caricate su Microsoft Teams, e l'iscrizione al team è automatica."
            ),
            "source": "https://degree.units.it/en/0320107303300001/students-area/taught-courses/2025/120014/2025/2/10740/2025"
        },
        {
            "question": "Regolmaneto in cui sono definite le modalità di elezione delle rappresentanze studentesche nei corsi interdipartimentali?",
            "grading_notes": "deve citare il regolamento degli studenti",
            "ground_truth": (
                "Le modalità di elezione delle rappresentanze studentesche nei consigli di dipartimento "
                "sono definite dal regolamento degli studenti (comma 7)."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-22178/art-31-corsi-studio"
        },
        {
            "question": "Quali attività cura l'Università per facilitare l'inserimento nel mondo del lavoro?",
            "grading_notes": "La risposta deve menzionare orientamento, tutorato e associazioni di ex-alunni.",
            "ground_truth": (
                "L'Università cura le attività di orientamento e tutorato e attiva servizi intesi ad agevolare "
                "l'inserimento nel mondo del lavoro di studenti e laureati. Favorisce inoltre la costituzione "
                "di associazioni di ex-alunni, finalizzate al mantenimento di relazioni con l'Ateneo e al "
                "sostegno delle sue attività istituzionali."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-22145/art-1-natura-e-fini"
        },
        {
            "question": "Quali forme di sostegno economico eroga l'Università agli studenti?",
            "grading_notes": "La risposta deve menzionare almeno una forma di sostegno economico, come borse di studio, esenzioni o riduzioni delle tasse universitarie.",
            "ground_truth": (
                "L'Università eroga diverse forme di sostegno economico agli studenti. Offre borse di studio proprie, "
                "destinate a incentivare la frequenza universitaria e a supportare gli studenti in situazioni economiche "
                "difficili, promuovendo l'inclusione e valorizzando il talento. "
                "Inoltre, mette a disposizione moduli e documenti per richiedere esenzioni e riduzioni delle tasse universitarie, basate su specifiche situazioni personali, come ad esempio: "
                "*   Riduzioni per borsisti del Governo Italiano o studenti provenienti da Paesi in via di sviluppo. "
                "*   Riduzioni per familiari contemporaneamente iscritti. "
                "*   Esenzioni per figli di beneficiari di pensione di inabilità. "
                "*   Riduzioni per studenti genitori. "
                "*   Esenzioni/riduzioni per permessi di soggiorno per asilo politico o tutele speciali per studenti internazionali."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-22145/art-1-natura-e-fini"
        },
        {
            "question": "Chi può proporre il conferimento del titolo di Dottore di Ricerca honoris causa?",
            "grading_notes": "La risposta deve menzionare il Rettore e il Collegio dei docenti del Dottorato, con la maggioranza dei due terzi.",
            "ground_truth": (
                "Il conferimento può essere proposto dal Rettore o dal Collegio dei docenti del Dottorato di "
                "riferimento, previa deliberazione assunta con la maggioranza dei due terzi dei componenti."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-53336/art-37-dottore-ricerca-honoris-causa"
        },
        {
            "question": "Quanti dottorati honoris causa può conferire l'Ateneo per ogni anno accademico?",
            "grading_notes": "La risposta deve indicare il limite massimo di un solo dottorato honoris causa per anno accademico.",
            "ground_truth": (
                "L'Ateneo può conferire al massimo un solo Dottorato honoris causa per ogni anno accademico, "
                "e comunque nei limiti stabiliti dal Ministero."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-53336/art-37-dottore-ricerca-honoris-causa"
        },
        {
            "question": "Quali diritti attribuisce il diploma di Dottorato honoris causa?",
            "grading_notes": "La risposta deve specificare che il diploma è equiparato ex lege al dottorato ordinario e ne attribuisce tutti i diritti.",
            "ground_truth": (
                "Il diploma di Dottorato honoris causa attribuisce tutti i diritti del Dottorato ordinario, "
                "in quanto è equiparato ex lege al titolo normalmente conseguito."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-53336/art-37-dottore-ricerca-honoris-causa"
        },
        {
            "question": "Secondo il regolamento, in quali casi una proposta di dottorato honoris causa non viene presa in considerazione?",
            "grading_notes": "La risposta deve indicare che la proposta è esclusa se il candidato è già in possesso di un dottorato ordinario o honoris causa della stessa tipologia.",
            "ground_truth": (
                "Non vengono prese in considerazione le proposte inerenti a persone già in possesso di un "
                "diploma di Dottorato di Ricerca ordinario o honoris causa della stessa tipologia."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-53336/art-37-dottore-ricerca-honoris-causa"
        },
        {
            "question": "Per quanto tempo può essere incrementata la borsa di dottorato per soggiorno all'estero?",
            "grading_notes": "La risposta deve menzionare l'incremento del 50%, il limite di 12 mesi ordinario e il limite esteso di 18 mesi per dottorati in convenzione o co-tutela",
            "ground_truth": (
                "L'importo della borsa di dottorato può essere incrementato del 50% per un periodo di soggiorno "
                "all'estero complessivo non superiore a 12 mesi per attività di ricerca. Questo periodo può essere "
                "esteso fino a un massimo complessivo di 18 mesi per i dottorati in convenzione o per i dottorandi "
                "in co-tutela con soggetti esteri. L'incremento è applicabile per periodi di soggiorno continuativi "
                "e non inferiori a 30 giorni."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-44584/art-29-borse-studio"
        },
        {
            "question": "regole e limitazioni per ottenere una seconda borsa di dottorato nell'università italiana",
            "grading_notes": "La risposta deve indicare chiaramente che non è possibile usufruire di una seconda borsa di dottorato, anche se la prima è stata fruita solo parzialmente.",
            "ground_truth": (
                "Chi ha già usufruito di una borsa di dottorato nell'ambito del sistema universitario italiano, "
                "anche parzialmente, non può usufruirne una seconda volta."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-44584/art-29-borse-studio"
        },
        {
            "question": "Cosa succede alla borsa di dottorato in caso di rinuncia, di mancato rinnovo o di rinuncia agli studi?",
            "grading_notes": "La risposta deve menzionare la possibilità di assegnare la borsa a un dottorando privo di borsa dello stesso ciclo e corso, e il reinvestimento dell'importo non utilizzato.",
            "ground_truth": (
                "In caso di rinuncia alla borsa, di mancato rinnovo o di rinuncia agli studi, la borsa può essere "
                "assegnata, nella sua quota totale o residua, su proposta del Collegio dei docenti, a un dottorando "
                "privo di borsa dello stesso ciclo e dello stesso Corso. In ogni caso l'importo non utilizzato è "
                "reinvestito dal soggetto che ha attivato il Corso per il finanziamento di dottorati di ricerca."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-44584/art-29-borse-studio"
        },
        {
            "question": "Quali conseguenze può avere il rifiuto del dottorando di dedicarsi al tema di ricerca assegnato?",
            "grading_notes": "La risposta deve menzionare la possibilità di decadenza dal dottorato oppure la revoca della borsa con attribuzione di un nuovo tema e supervisore, senza prolungamento della durata.",
            "ground_truth": (
                "Il Collegio dei docenti, sentito il dottorando, può disporre la decadenza dal dottorato oppure "
                "la revoca della borsa e l'attribuzione al dottorando di un nuovo tema di ricerca e di un nuovo "
                "supervisore, senza prolungamento della durata di 36 mesi del dottorato."
            ),
            "source": "https://amm.units.it/normativa/regolamenti/articolo-44584/art-29-borse-studio"
        },
        {
            "question": "Quali sono gli insegnamenti previsti nel semestre aperto per l'accesso a Medicina e Odontoiatria?",
            "grading_notes": "La risposta deve elencare i tre insegnamenti: Chimica e propedeutica biochimica, Fisica e Biologia, ciascuno da 6 CFU.",
            "ground_truth": (
                "Il semestre aperto prevede la frequenza e il superamento di tre insegnamenti da 6 CFU ciascuno: "
                "Chimica e propedeutica biochimica, Fisica e Biologia."
            ),
            "source": "https://portale.units.it/it/studiare/orientarsi/preparazione-test-area-medico-sanitaria"
        },
        {
            "question": "Qual è il contributo economico richiesto per l'iscrizione al semestre aperto di Medicina?",
            "grading_notes": "La risposta deve indicare almeno il contributo forfettario di 250 euro. se c'è altro va bene",
            "ground_truth": (
                "Per l'iscrizione al semestre aperto è previsto un contributo forfettario unico a livello nazionale "
                "di 250 euro. L'importo verrà ricalcolato in un secondo momento in base all'ISEE Universitario "
                "e agli altri casi di esonero totale o parziale previsti dalla normativa vigente."
            ),
            "source": "https://portale.units.it/it/studiare/orientarsi/preparazione-test-area-medico-sanitaria"
        },
        {
            "question": "Cosa succede a chi non risulta in posizione utile in graduatoria dopo il semestre aperto di Medicina?",
            "grading_notes": (
                "La risposta deve menzionare la possibilità di accedere a un corso affine "
                "scelto in fase di iscrizione, in base alla posizione raggiunta e ai posti disponibili."
            ),            
            "ground_truth": (
                "Chi non risulta in posizione utile in graduatoria può accedere, sulla base della posizione "
                "raggiunta e dei posti disponibili, al corso affine scelto in fase di iscrizione."
            ),
            "source": "https://portale.units.it/it/studiare/orientarsi/preparazione-test-area-medico-sanitaria"
        },
                                    # {
                                    #     "question": "anticipo minimo invio summary al professore per fast track registrazione tirocinio laurea",
                                    #     "grading_notes": "La risposta deve indicare almeno una settimana prima dell'ultima data utile per la registrazione del tirocinio.",
                                    #     "ground_truth": (
                                    #         "Il summary deve essere inviato per email con almeno una settimana di anticipo rispetto "
                                    #         "all'ultima data utile per la registrazione del tirocinio, indicando nello stesso email "
                                    #         "tale data, determinata contattando la segreteria studenti."
                                    #     ),
                                    # },
        {
            "question": "Quante ore minime di tirocinio pratico-valutativo sono richieste come primo operatore in Odontoiatria?",
            "grading_notes": "La risposta deve indicare il minimo di 600 ore come primo operatore",
            "ground_truth": (
                "Il tirocinio pratico-valutativo di Odontoiatria richiede un minimo di 600 ore di tirocinio "
                "come primo operatore, certificate dal Coordinatore del Corso di Studio."
            ),
            "source": "https://lauree.units.it/it/0320107304700001/area-studenti/tirocinio-e-internato"
        },
        {
            "question": "In cosa consiste la prova pratica valutativa al termine del tirocinio di Odontoiatria?",
            "grading_notes": "La risposta deve menzionare la discussione di 3 casi clinici multidisciplinari, la valutazione idoneo/non idoneo e che precede la tesi di laurea.",
            "ground_truth": (
                "La prova pratica valutativa consiste nella discussione di 3 casi clinici multidisciplinari "
                "svolti dal candidato, con valutazione idoneo/non idoneo. Precede la discussione della tesi di laurea."
            ),
            "source": "https://lauree.units.it/it/0320107304700001/area-studenti/tirocinio-e-internato"
        },
        {
            "question": "Come si registra il tirocinio da 9 CFU in Fisica?",
            "grading_notes": "La risposta deve menzionare il seminario pubblico di 20 minuti e il contatto con il Prof. Andrea Bressan, con appello ogni primo lunedì del mese.",
            "ground_truth": (
                "Per registrare il tirocinio da 9 CFU in Fisica, lo studente deve esporre l'attività svolta "
                "e i risultati raggiunti in un seminario pubblico di 20 minuti. Bisogna contattare il Prof. "
                "Andrea Bressan per l'iscrizione all'appello che si tiene ogni primo lunedì del mese."
            ),
            "source": "https://lauree.units.it/it/0320106203000001/area-studenti/tirocinio-e-internato"
        },
        {
            "question": "Quanti CFU prevede il tirocinio curriculare di Fisica e quante ore corrispondono?",
            "grading_notes": "La risposta deve indicare almeno il dato dei 3 CFU per 75 ore, in aggiunta può anche dire che c'è l'alternativa da 9 CFU per 225 ore, e la restrizione ai soli 3 CFU per gli immatricolati dall'a.a. 2024/2025.",
            "ground_truth": (
                "Il tirocinio curriculare di Fisica prevede 3 CFU per un totale di 75 ore. In alternativa "
                "è possibile optare per un tirocinio esteso da 9 CFU per 225 ore. Per gli immatricolati "
                "al primo anno a partire dall'a.a. 2024/2025 è previsto solamente il tirocinio da 3 CFU."
            ),
            "source": "https://lauree.units.it/it/0320106203000001/area-studenti/tirocinio-e-internato"
        },
        {
            "question": "Entro quando deve arrivare la documentazione per avviare il tirocinio di Scienze e Tecnologie Biologiche?",
            "grading_notes": "La risposta deve indicare entro il 15 del mese precedente l'inizio del tirocinio.",
            "ground_truth": (
                "La documentazione per avviare il tirocinio di Scienze e Tecnologie Biologiche deve arrivare "
                "alla Segreteria Didattica entro il 15 del mese precedente l'inizio del tirocinio, per "
                "permettere l'approvazione da parte del Consiglio di Corso di Studi."
            ),
            "source": "https://lauree.units.it/it/0320106201300002/area-studenti/tirocinio-e-internato"
        },
        {
            "question": "Quando è richiesto il test Mantoux per il tirocinio di Scienze e Tecnologie Biologiche?",
            "grading_notes": "La risposta deve indicare che il test è richiesto quando il tirocinio prevede contatto con persone fragili (asili, ospedali, case di riposo ecc.) e che l'ateneo ha una convenzione con ASUGI per effettuarlo gratuitamente.",
            "ground_truth": (
                "Il test Mantoux è richiesto quando il tirocinio prevede il contatto con persone fragili, "
                "come in strutture quali asili nidi, scuole dell'infanzia, ospedali, cliniche, case di riposo "
                "o centri di accoglienza. L'ateneo ha una convenzione con ASUGI per effettuare il test gratuitamente."
            ),
            "source": "https://lauree.units.it/it/0320106201300002/area-studenti/tirocinio-e-internato"
        },
        {
            "question": "l aula T dell'edificio A è libera il giorno 20 marzo 2026?",
            "grading_notes": "ammettere mancanza di info",
            "ground_truth": "Non ho informazioni sulla disponibilità dell'aula T per quella data specifica.",
            "source": "absent for choice"
        },
        {
            "question": "dimmi i corsi disponibili del dipartimento di musicologia",
            "grading_notes": "ammettere mancanza di info",
            "ground_truth": "Non dispongo di informazioni sui corsi del dipartimento di Musicologia.",
            "source": "absent for choice"
        },
    ]
# Invio autorizzato del resoconto con Gmail

Leggere [backend.md](backend.md). Eseguire i comandi locali con il launcher
`trtalks` del progetto e percorso assoluto. È l'agente a preparare il documento
e chiamare Gmail: l'intervistato non deve eseguire comandi di invio.

## Collegamento e destinazione

Verificare che il tool Gmail `send_email` sia disponibile in questa chat.
Se manca, dichiarare il blocco e conservare il file. Non chiedere credenziali.
`trtalks status` mostra destinatario e abilitazione senza rete. Per un test
reale senza email usare `get_profile` di Gmail, se disponibile. Non inviare
messaggi durante una verifica tecnica.

Il destinatario iniziale è `trtalks@techreloaded.it`; rispettare quello effettivo
della configurazione. Cambiarlo solo su richiesta con
`trtalks configure --recipient INDIRIZZO`. Il mittente è l'account Google
collegato. Non servono `init` o variabili di connessione.

## Documento e consegna

1. Salvare il Markdown UTF-8 con nome ASCII, lettere, numeri, `_` o `-` e `.md`.
   Mostrare il testo completo e rendere disponibile il file.
2. Esplicitare destinatario, allegato ed eventuali dettagli riservati. Raccogliere
   una sola autorizzazione per quella versione e destinazione; se già ricevuta,
   usarla senza ripetere la domanda. Non inventare l'autorizzazione.
3. Eseguire `trtalks dry-run /percorso/intervista.md` per controllare SHA-256,
   formato e destinatario senza rete. Se l'invio locale è disabilitato ma questa
   consegna è già autorizzata, `configure --enable-send` non richiede una seconda
   approvazione del documento. Una prova tecnica non autorizza l'abilitazione.
4. Eseguire `trtalks send /percorso/intervista.md --approved-sha256 HASH
   --authorization 'Riferimento alla decisione esplicita ricevuta'`.
   Questo prepara il tentativo; **non ha ancora inviato l'email**.
5. Se `cached:true`, riusare la ricevuta e fermarsi senza chiamare Gmail.
   Altrimenti chiamare subito `send_email` di Gmail con i `tool_arguments`
   restituiti: destinatario, oggetto, corpo e Markdown in `attachment_files`.
   Usare un percorso/riferimento accessibile al connettore per la copia approvata,
   come descritto in backend.md. Non fermarsi alla preparazione locale.
6. Salvare la risposta reale JSON di Gmail, senza inventare campi o ID, e usare
   `trtalks record-result REQUEST_ID --receipt /percorso/risposta.json`.
   Riferire l'esito effettivo e l'eventuale ID del messaggio.

Se cambia il contenuto o la destinazione, l'approvazione precedente non copre
automaticamente la modifica. Quotare gli argomenti in modo sicuro, preferibilmente
con subprocess e lista. Non mostrare i dettagli privati delle ricevute nei log.

## Esiti

- Preparazione `pending`, `email_sent:false`: messaggio non ancora inviato.
- `gmail_accepted:true`: Gmail ha confermato l'invio con un ID; la ricezione nella
  casella del destinatario non è confermata.
- `cached:true`: nessun nuovo invio; ricevuta precedente riusata.
- Errore, timeout, `pending` dopo un'interruzione o `uncertain`: conservare bozza
  e ricevute, verificare Gmail prima di ripetere. Non avviare cicli o nuovi ID.

`.trtalks/deliveries/` conserva autorizzazione, copia del documento e risposta
Gmail. Non cancellare gli stati durante aggiornamenti o disinstallazione.
I vecchi tentativi restano nello storico e non vengono ritentati tramite Gmail.

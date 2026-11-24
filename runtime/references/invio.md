# Invio autorizzato del resoconto con Gmail

## Installazione e tipo di richiesta

Usare l'installazione del progetto corrente, indipendentemente dal nome del sito.
Eseguire `./websmith-talks status` e `./websmith-talks paths` prima di dichiarare
che non si vede la configurazione. Se gli strumenti locali non sono disponibili
o un'operazione fallisce, descrivere il limite osservato e conservare il documento;
non cercare una seconda applicazione con il nome del sito né rinviare
automaticamente alla chat testuale. La modalità vocale non modifica queste regole.

Distinguere le richieste:

- Una verifica della connessione o una prova della skill usa `status`, `probe`
  ed eventualmente `get_profile`; non spedisce email.
- «Crea e invia una mail/intervista di prova» richiede una consegna reale:
  creare un Markdown chiaramente fittizio e seguire il flusso sotto, usando
  l'autorizzazione già ricevuta. Non avviare domande di intervista non richieste.
- Story include la consegna automatica del documento finale. Indicare destinatario
  e invio tramite l'account Gmail collegato all'inizio della conversazione;
  alla conclusione mostrare il documento e inviarlo senza una seconda conferma.
  Rispettare richieste di sola bozza, sospensione o non invio. Una semplice prova
  di Story conserva invece il documento senza inviarlo, salvo richiesta esplicita.
- Page e gli altri documenti richiedono una richiesta di consegna; riusare quella
  già ricevuta senza chiedere nuovamente il permesso.

Leggere [backend.md](backend.md). Eseguire i comandi locali con il launcher
`websmith-talks` del progetto e percorso assoluto. È l'agente a preparare il documento
e chiamare Gmail: l'intervistato non deve eseguire comandi di invio.

## Collegamento e destinazione

Leggere sito e tag da `websmith-talks status`. Il sito è quello associato
all'installazione e non si cambia per la singola consegna. Se una vecchia
installazione non lo dichiara, raccogliere lo stesso `site.id` di Websmith e
associarlo una sola volta con `configure --site-id ID`. Per un altro sito
usare un progetto separato.

Verificare che il tool Gmail `send_email` sia disponibile in questa chat.
Se manca, dichiarare il blocco e conservare il file. Non chiedere credenziali.
`websmith-talks status` mostra destinatario e abilitazione senza rete. Per un test
reale senza email usare `get_profile` di Gmail, se disponibile. Non inviare
messaggi durante una verifica tecnica.

Il destinatario iniziale è `trtalks@techreloaded.it`: leggere sempre quello
effettivo della configurazione e conservare eventuali personalizzazioni.
Se manca, chiedere a quale indirizzo consegnare il documento, salvo indicazione
già ricevuta. Configurarlo con `websmith-talks configure --recipient INDIRIZZO`
ed esplicitarlo prima di usare l'autorizzazione. Non ricavare l'indirizzo dal
nome del sito né scegliere una casella predefinita. Un destinatario esistente
si cambia solo su richiesta. Il mittente è l'account Google
collegato. Non servono `init` o variabili di connessione.

## Documento e consegna

1. Salvare il Markdown UTF-8 con nome ASCII, lettere, numeri, `_` o `-` e `.md`.
   Mostrare il testo completo e rendere disponibile il file.
2. Esplicitare destinatario, allegato ed eventuali dettagli riservati. Raccogliere
   una sola autorizzazione per quella versione e destinazione quando il flusso
   non la comprende già; se ricevuta, usarla senza ripetere la domanda. Per Story
   registrare la richiesta dell'intervista con consegna automatica annunciata
   e la sua conclusione, senza inventare un'approvazione manuale del testo.
3. Eseguire `websmith-talks dry-run /percorso/intervista.md` per controllare SHA-256,
   formato e destinatario senza rete. Se l'invio locale è disabilitato, una
   richiesta esplicita di inviare quel file o abilitare l'invio consente
   `configure --enable-send`, senza una seconda conferma. La sola conclusione
   di Story rispetta invece `send_enabled:false`: conservare la bozza e segnalare
   l'impostazione, senza riabilitarla automaticamente.
   Una semplice prova tecnica non autorizza l'abilitazione.
4. Eseguire `websmith-talks send /percorso/intervista.md --approved-sha256 HASH
   --authorization 'Riferimento alla richiesta effettiva e al flusso di consegna'`.
   Questo prepara il tentativo; **non ha ancora inviato l'email**.
5. Se `cached:true`, riusare la ricevuta e fermarsi senza chiamare Gmail.
   Altrimenti chiamare subito `send_email` di Gmail con i `tool_arguments`
   restituiti: destinatario, oggetto, corpo e Markdown in `attachment_files`.
   Conservare l'oggetto con l'unico tag `[websmith:site.id]` preparato dal runtime.
   Usare un percorso/riferimento accessibile al connettore per la copia approvata,
   come descritto in backend.md. Non fermarsi alla preparazione locale.
6. Salvare la risposta reale JSON di Gmail, senza inventare campi o ID, e usare
   `websmith-talks record-result REQUEST_ID --receipt /percorso/risposta.json`.
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

`.websmith-talks/deliveries/` conserva autorizzazione, copia del documento e risposta
Gmail. Non cancellare gli stati durante aggiornamenti o disinstallazione.
I vecchi tentativi restano nello storico e non vengono ritentati tramite Gmail.

# Consegna tramite Gmail

L'agente invia usando `send_email` del connettore Gmail collegato alla chat
(nome attuale: `mcp__codex_apps__gmail_send_email`). Verificare il tool disponibile
e il suo schema effettivo; non inventare strumenti o risultati. Il mittente è
l'account Google autenticato. Il nome locale compare nel corpo del messaggio,
non sostituisce il mittente Gmail. `reply_to` è facoltativo.

Gli script Python preparano allegato e argomenti e conservano le ricevute:
non possono invocare da soli il connettore ChatGPT. La consegna è completata
dall'agente con la chiamata reale al tool Gmail, nello stesso flusso.

## Configurazione

`.websmith-talks/config.local.json` contiene `schema:2`, `transport:"gmail"`,
`recipient` (inizialmente `trtalks@techreloaded.it`), `sender_name`, `reply_to`
e `send_enabled` (inizialmente `true`), oltre a `site: {id, name, base_url}`.
Story comprende la consegna automatica del documento finale, annunciata
all'inizio dell'intervista. Le richieste di sola bozza e non invio prevalgono;
Page e le prove richiedono una richiesta di invio. Seguire [invio.md](invio.md)
per registrare l'autorizzazione effettiva senza conferme ripetute.
Le preferenze esistenti restano valide, anche un destinatario esplicitamente vuoto.
Il setup associa esattamente un sito con
lo stesso `site.id` di Websmith, verificato nei metadati dell'installazione.
Nome e URL sono facoltativi; non generare un ID dal dominio.
Per vecchie installazioni senza sito usare una sola volta
`configure --site-id ID`. Per un altro sito usare un'installazione separata.
Per cambiare il destinatario usare `configure --recipient INDIRIZZO` su
indicazione della persona. Per installazioni precedenti con destinatario vuoto,
configurarlo una sola volta; `status` espone
`recipient_configured:false` finché manca. `send` e `dry-run` si interrompono
senza creare tentativi quando il destinatario non è configurato. Le conversazioni,
il salvataggio locale e `probe` restano disponibili.
Se manca il sito, `status` espone `site_configured:false` e la preparazione
della consegna si interrompe. Se presente, espone anche `email_tag`.
Il collegamento Google è gestito dall'app: nessun host, porta, password, token
locale o procedura `init`. L'aggiornamento elimina i precedenti parametri di
connessione, conservando destinatario, preferenze e ricevute.
Ogni collega usa il connettore Gmail configurato nella propria app. Non cercare
un account del sito o un collegamento ereditato da chi ha creato il pacchetto.

`websmith-talks status` mostra le impostazioni locali senza rete e senza dichiarare
verificato il collegamento Gmail. L'agente controlla la disponibilità di
`send_email`; per provare l'account senza email usa `get_profile` di Gmail.
`probe` crea solo un Markdown fittizio locale.

## Preparazione, invio e ricevuta

`send` salva una copia privata dei byte approvati e un tentativo `pending`,
quindi restituisce `tool` e `tool_arguments` per l'agente. Non spedisce email.
Il tool Gmail riceve `to`, `subject`, `payload` e `attachment_files`, oltre a
`reply_to` se presente. Non sostituire il mittente dell'account autenticato.
L'oggetto inizia con un solo `[websmith:site.id]`, compatibile con il filtro
inbox di Websmith. Mantenere l'oggetto restituito dal runtime. La casella può
ricevere documenti di più siti: il tag determina a quale sito appartengono.

L'allegato deve essere accessibile al connettore. Se il percorso sul computer
non è accessibile al tool, trasferire la copia approvata attraverso il canale
file supportato dall'ambiente e usare il riferimento effettivamente restituito.
Verificare i byte con lo SHA-256 salvato. Non inventare URI, non usare un link
come sostituto dell'allegato e non convertire il resoconto nel solo corpo email.
Se manca un canale file compatibile, indicare il blocco e conservare il documento.

Dopo `send_email`, salvare la risposta JSON effettiva e passarla a
`websmith-talks record-result REQUEST_ID --receipt /percorso/risposta.json`.
Un risultato con `id` e senza errore registra `accepted` e l'ID Gmail.
Una risposta d'errore o priva di ID registra `uncertain`. Una conferma di Gmail
non dimostra la ricezione nella casella del destinatario.

Il lock e lo stato locale impediscono di preparare due volte lo stesso documento.
Una ricevuta `accepted` viene riusata senza reinvio. `pending`, `uncertain` e
vecchi tentativi con altri trasporti richiedono verifica manuale prima di un
nuovo invio: `retry` non chiama mai il servizio. Un ID locale non è una chiave di
idempotenza Gmail. Non cambiare il documento o cancellare ricevute per aggirare
il blocco. Lo stato non deduplica fra computer differenti.

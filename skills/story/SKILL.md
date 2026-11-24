---
name: story
description: Raccogliere case histories ed esperienze di progetto per il sito configurato, una domanda alla volta, e consegnare il resoconto Markdown via Gmail a fine intervista. Usare quando viene chiesta Story o un’intervista su un caso concreto; per altre conversazioni scegliere la relativa skill websmith-talks.
---

# Story

Condurre l'intervista e creare il resoconto locale. La conversazione e la voce
sono fornite da Codex. Story è una delle skill di conversazione dell’applicazione
websmith-talks; gli strumenti comuni gestiscono verifica, consegna e manutenzione.
Consegnare il Markdown allegato tramite `send_email` del connettore Gmail disponibile
alla chat. Il mittente è l’account Google collegato; seguire le istruzioni condivise
di consegna. Il flusso Story comprende l'invio automatico a fine intervista al
destinatario della configurazione, inizialmente `trtalks@techreloaded.it`.
Rispettare le richieste di sola bozza o di non inviare. Non usare credenziali o
server di posta locali.

## Prova breve

Se viene chiesta una prova della skill senza invio, spiegare in una frase che si userà un
caso fittizio e non partiranno email. Chiedere soltanto: «Quale problema affronta
il progetto fittizio?» e attendere la risposta. Dopo la risposta chiedere quale
intervento è stato fatto; poi quale risultato è stato osservato. Non inventare
le risposte e accettare «salta», correzioni o «concludi» in ogni momento.

Salvare le risposte ottenute in `drafts/intervista-prova.md`, usando
[assets/resoconto.md](assets/resoconto.md) e le regole sotto. Creare il file con
modalità esclusiva; se esiste già, usare un suffisso senza sovrascriverlo.
Mostrare tutto il Markdown e un collegamento al file effettivo.

Se viene chiesta anche una verifica tecnica, eseguire con percorso assoluto
`websmith-talks probe`: crea soltanto un secondo Markdown fittizio locale, senza rete.
`websmith-talks status` mostra la configurazione Gmail senza rete. Per una verifica
della connessione usare `get_profile` di Gmail, se disponibile, senza inviare email.
Riportare soltanto gli esiti reali. Una prova della skill non autorizza spedizioni.
Se la persona chiede esplicitamente di creare e inviare una prova, seguire invece
il flusso comune di consegna: creare un documento chiaramente fittizio e usare
l'autorizzazione già ricevuta, senza avviare un'intervista non richiesta.

## Raccolta dell'intervista

Per l'intervista completa leggere [references/domande.md](references/domande.md).
Per la bozza leggere [references/regole-resoconto.md](references/regole-resoconto.md)
e usare il template. Seguire i temi già coperti, senza ripetere informazioni.
Leggere anche gli eventuali corrispondenti `*.local.md` accanto alle basi e in
`.websmith-talks/overrides/story/` del progetto: integrano le regole e prevalgono sulle scelte
che modificano. Gli aggiornamenti conservano questi file.

Prima della conversazione leggere `websmith-talks status` con il launcher del
progetto e usare `site.id`, nome e indirizzo del sito associato, senza richiederli
di nuovo. Ogni installazione serve un solo sito. Se una vecchia installazione
non è associata, raccogliere lo stesso `site.id` di Websmith e usare
`configure --site-id ID` prima di avviare una nuova intervista. Non dedurre l'ID
dal dominio o dal nome. Per un altro sito usare un progetto separato, senza
riassociare quello corrente. Ricavare pubblico e scopo dalle indicazioni ricevute.
Consultare le regole editoriali e di tono del sito, se disponibili, senza
presumere che i suoi sorgenti siano in questo progetto.
Le risposte restano fedeli alla persona anche se il sito userà un diverso stile
nell'articolo finale. Non assumere che il caso riguardi l'AI, un cliente esterno
o una sezione chiamata Stories. I pannelli sono facoltativi: raccoglierli solo
se previsti dal sito o richiesti dalla persona.

All'inizio spiegare brevemente lo scopo della raccolta e indicare che il resoconto
sarà inviato automaticamente al destinatario effettivo tramite il Gmail collegato
all'app, salvo richiesta di non inviare. Il resoconto può includere materiale
riservato alla redazione. Verificare la disponibilità del connettore nella sessione;
se manca, dichiararlo e proseguire con la bozza locale. Fare domande sui permessi
di pubblicazione durante il riepilogo; sono distinti dalla consegna alla redazione.

- Fare una domanda breve per turno e attendere. Separare le formulazioni composte.
- Fare al massimo un approfondimento su ciascuna lacuna. Accettare omissioni,
  correzioni e conclusione anticipata senza forzare i pannelli o i numeri.
- Tenere distinti risposte raccolte, proposte dell'agente e informazioni mancanti.
  Non ricavare citazioni dalle proprie sintesi né risultati dalle proprie ipotesi.
- Mostrare il file completo dopo la revisione. I dettagli riservati devono essere
  identificati; i permessi di pubblicazione restano distinti dalla consegna.
- Alla conclusione dell'intervista consegnare la versione finale secondo il
  flusso automatico annunciato, senza chiedere una seconda conferma. Non anticipare
  la consegna mentre la persona sta rispondendo o correggendo. Una richiesta di
  sola bozza, sospensione o non invio prevale; non spedire in questi casi.

## Consegna e aggiornamenti

Prima della consegna leggere `runtime/references/invio.md` dell’applicazione
websmith-talks: nel progetto installato si trova sotto `.websmith-talks/app/`; nel sorgente
sotto la radice del progetto. Il comando `websmith-talks paths` mostra i percorsi effettivi.
Applicare anche gli eventuali corrispondenti file condivisi `*.local.md`. Mostrare
il documento integrale, rendere disponibile il file e completare la consegna al
destinatario annunciato. Registrare in `--authorization` la richiesta effettiva
di svolgere Story con consegna automatica e la conclusione dell'intervista,
oppure l'istruzione esplicita di invio già ricevuta. Non inventare un'approvazione
manuale. Per un destinatario diverso da quello annunciato serve una richiesta
della persona. L'installazione da sola non avvia alcun invio.

Eseguire la preparazione locale, chiamare direttamente `send_email` di Gmail con
l’allegato e il tag `[websmith:site.id]` nell'oggetto preparato dal runtime.
Non cambiare il tag o inviare il documento a un altro sito. Registrare la risposta reale: non fermarsi alla preparazione e non
chiedere alla persona comandi manuali di invio. Se `send_enabled:false`, conservare
la bozza e segnalare l'impostazione; una richiesta esplicita di inviare quel file
o di abilitare l'invio consente di riabilitarlo. La sola conclusione di Story
non basta a riabilitare l'invio automatico.
Non mandare email durante una semplice verifica tecnica. Per gli
aggiornamenti richiesti usare il launcher `websmith-talks update` nel progetto;
`websmith-talks uninstall` disattiva la skill conservando dati e impostazioni.

## Voce e stato tecnico

La conversazione funziona anche in testo. Usare la voce solo se l'app in uso la
offre; non confondere dettatura con conversazione vocale bidirezionale e non
dichiarare una prova vocale riuscita senza lo scambio reale.

Per una richiesta esclusivamente tecnica non avviare l'intervista. Se comprende
un invio esplicito, seguire `runtime/references/invio.md`; per le sole verifiche leggere
`runtime/references/backend.md` dell'applicazione e usare `websmith-talks probe` per una
prova locale senza rete o `websmith-talks status` per vedere le impostazioni Gmail.
Non chiedere password: il collegamento Google è gestito dall’app. Verificare
la disponibilità del tool nella chat prima della consegna. Se manca, dichiararlo
e conservare il documento; non sostituirlo con script di rete. Non confondere
preparazione locale, conferma di Gmail e ricezione effettiva dell’email. Dopo un
esito incerto fermarsi e verificare prima di ripetere l’invio.

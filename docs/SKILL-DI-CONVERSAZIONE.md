# websmith-talks e le skill di conversazione

websmith-talks è l’applicazione; ogni tipologia di conversazione è una skill distinta.
**Story** raccoglie case histories e si invoca con `$story`; **Page** prepara
pagine web e si invoca con `$page`. La versione di sviluppo è 0.8.0a1.
Le skill precedenti `trstory` e `trpage` diventano `story` e `page`.
I progetti esterni TRInterview/TRConversations non sono stati rinominati.

Le conversazioni non assumono un marchio. Leggono il sito associato tramite
`status`, poi le istruzioni del progetto e le indicazioni della persona.
Ogni installazione serve un solo sito e non propone di cambiarlo a ogni conversazione.
Le regole del sito per l'articolo finale non cambiano la
fedeltà alle risposte dell'intervistato. AI e pannelli di sintesi sono facoltativi.

## Organizzazione dei sorgenti

| Percorso | Contenuto |
| --- | --- |
| `conversations.json` | Catalogo delle skill: ID, nome, descrizione e lista dei file |
| `skills/story/` | SKILL.md, metadati UI, domande, regole e template delle case histories |
| `skills/page/` | SKILL.md, metadati UI, domande, regole e modello per una pagina web |
| `runtime/` | CLI, installazione, update, preparazione Gmail, ricevute e verifiche comuni |
| `runtime/references/` | Contratto backend e istruzioni di invio comuni |
| `scripts/` | Costruzione e pubblicazione dell’applicazione |

Gli script comuni non vengono duplicati nelle skill. Ciascuna skill governa la
conversazione e decide quando utilizzare gli strumenti comuni e quale output
produrre. La presenza degli strumenti di invio non obbliga una skill a inviare
documenti e non autorizza un invio.

## Aggiungere una tipologia

1. Creare `skills/ID/SKILL.md` con `name: ID` e una descrizione precisa dello
   scopo. L’ID usa lettere minuscole, numeri e trattini.
2. Aggiungere domande, regole, template e gli eventuali script specifici della
   nuova conversazione, senza ricopiare il runtime generale.
3. Aggiungere una voce a `conversations.json` con `id`, `display_name`,
   `description` e `files`. I percorsi di `files` sono relativi a `skills/ID/`.
   Ogni file da distribuire deve essere dichiarato esplicitamente.
4. Incrementare `VERSION`, costruire il pacchetto ed eseguire i test.

Installer, pagina di istruzioni ed elenco CLI leggono il catalogo. Per una
seconda skill non occorre modificare il codice di installazione o di consegna.
Il catalogo di sviluppo contiene Story e Page. La skill TRDemo usata nei
test è una fixture temporanea e non viene distribuita.

Page raccoglie scopo, destinatari, messaggio, titolo, abstract e contenuti;
chiede se servono CTA e hero, il template, la posizione e l'URL finale, i link
per raggiungere la pagina e quelli nel contenuto. Produce una bozza Markdown
con brief, testi e indicazioni di realizzazione separate. Non pubblica sul sito;
la normale conclusione è il documento locale, mentre la consegna alla redazione
usa il runtime comune solo se richiesta e autorizzata. Domande già soddisfatte
vengono saltate; informazioni mancanti e proposte restano esplicite.

Per una rinomina aggiungere `vecchio-id: nuovo-id` alla mappa `renames` del
catalogo. Serve a trasferire le personalizzazioni Markdown locali; l’ID vecchio
non deve essere ancora una skill attiva. La mappa attuale è `trtalks → story`,
`trstory → story`, `trpage → page`. Più nomi precedenti possono convergere sullo
stesso ID; personalizzazioni dello stesso file con byte diversi bloccano il passaggio.

## Installazione e scelta

Nel progetto installato:

| Percorso | Responsabilità |
| --- | --- |
| `.websmith-talks/app/` | Applicazione e manifest della release |
| `.websmith-talks/app/runtime/` | Programma condiviso |
| `.agents/skills/ID/` | Ciascuna skill visibile a Codex |
| `.websmith-talks/config.local.json` | Impostazioni locali conservate |
| `.websmith-talks/overrides/ID/` | Personalizzazioni per la conversazione |
| `.websmith-talks/deliveries/` | Payload, request_id e ricevute persistenti |

`websmith-talks skills` elenca le conversazioni e i rispettivi prompt.
`websmith-talks paths` mostra i percorsi effettivi del runtime e delle skill.

Se `AGENTS.md` non esiste, l’installer crea una breve istruzione generale:
scegliere la skill coerente con la richiesta; con una richiesta generica e una
sola skill usare quella, con più skill chiedere quale. Le istruzioni specifiche
di progetto già esistenti non vengono sovrascritte o cancellate.

Gli aggiornamenti gestiscono l’insieme delle skill dichiarate. Le skill rimosse
dal catalogo vengono disattivate e conservate nei backup, incluse le rispettive
regole locali. Una skill con lo stesso nome ma non gestita da websmith-talks blocca
l’aggiornamento invece di essere sovrascritta. Altre skill del progetto restano
invariate. Runtime e skill vengono ripristinati se una sostituzione fallisce.

## Passaggio dalla struttura precedente

Il nuovo installer riconosce le installazioni TRTalks con runtime comune e le
precedenti installazioni con skill singola. Usare il nuovo `setup.sh` indicando
la cartella esistente con `WEBSMITH_TALKS_HOME`, oppure il nuovo
`runtime/manage.py install --upgrade` con archivio e checksum. Il vecchio updater
non comprende il nuovo nome del pacchetto: non basta servirgli il nuovo ZIP.

Lo stato passa da `.trtalks` a `.websmith-talks`; il launcher diventa
`websmith-talks`. Le personalizzazioni delle skill e degli override seguono le
rinomine del catalogo. Per la skill singola, backend e invio passano alle regole
condivise. Bozze e altri documenti del progetto restano nella loro posizione.
Ricevute e allegati conservano i byte e gli ID delle richieste, anche se i percorsi
storici dentro le ricevute contengono ancora `.trtalks`: gli allegati sono ora
sotto `.websmith-talks/deliveries/`. Non si avvia alcun invio durante il passaggio.

Il nuovo archivio ammette soltanto il manifest `websmith-talks`; i manifest
`trtalks` sono letti solo per riconoscere le installazioni da migrare.
La presenza contemporanea di entrambe le directory di stato blocca la procedura;
non vengono fuse automaticamente. Una sostituzione fallita ripristina runtime,
launcher, skill, configurazione e istruzioni precedenti.

## Verifiche e limiti

Il runtime 0.8.0a1 prepara la consegna per `send_email` del connettore Gmail.
Il collegamento Google è gestito dall’app; nessuna credenziale di posta resta
nella configurazione websmith-talks. Le skill leggono il destinatario effettivo.
Le nuove installazioni hanno il destinatario vuoto: la consegna richiede
`configure --recipient INDIRIZZO`, su indicazione della persona. Gli aggiornamenti
conservano gli indirizzi esistenti, compresi quelli delle installazioni TRTalks.
Il setup richiede `--site-id` (o la risposta nel terminale), uguale a `site.id`
del `websmith.yaml` di Websmith. Nome e URL sono facoltativi. La configurazione
locale contiene `site: {id, name, base_url}`; i metadati di installazione
conservano l'associazione. Un ID diverso in configure, setup o update blocca
l'operazione. Per un altro sito occorre un'altra cartella.

Le email nuove usano `[websmith:site.id]` nell'oggetto, una sola volta.
`dry-run` espone sito, tag e oggetto; le nuove ricevute conservano `site_id`.
Le ricevute precedenti senza ID restano valide nella stessa installazione e
continuano a bloccare i duplicati, senza modificare allegati o rigenerare tentativi.
`status` mostra le preferenze senza rete; `get_profile` di Gmail verifica
l’account; `probe` crea solo una bozza locale.

I test coprono installazione, aggiornamento, migrazione delle preferenze,
rimozione dei vecchi parametri di connessione, più skill, rollback,
conservazione dei byte, autorizzazione e ricevute Gmail simulate.
Una prova di invio reale richiede il documento e il destinatario autorizzati.

Il riconoscimento della skill e il dialogo vocale richiedono una prova
nell’app effettiva. La disponibilità di Gmail e l’accessibilità degli allegati
vanno verificate nell’ambiente utilizzato. Le release remote devono essere
pubblicate prima che gli aggiornamenti dei colleghi possano scaricarle.

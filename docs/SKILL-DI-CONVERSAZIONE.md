# TRTalks e le skill di conversazione

TRTalks è l’applicazione; ogni tipologia di conversazione è una skill distinta.
**TRStory** raccoglie case histories e si invoca con `$trstory`; **TRPage** prepara
pagine web e si invoca con `$trpage`. TRPage è aggiunta nei sorgenti di sviluppo
per la prossima release; `VERSION` resta invariato fino alla preparazione della
release. Nel precedente sorgente TRStory aveva ID `trtalks`; i progetti esterni
TRInterview/TRConversations non sono stati rinominati.

## Organizzazione dei sorgenti

| Percorso | Contenuto |
| --- | --- |
| `conversations.json` | Catalogo delle skill: ID, nome, descrizione e lista dei file |
| `skills/trstory/` | SKILL.md, metadati UI, domande, regole e template delle case histories |
| `skills/trpage/` | SKILL.md, metadati UI, domande, regole e modello per una pagina web |
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
Il catalogo di sviluppo contiene TRStory e TRPage. La skill TRDemo usata nei
test è una fixture temporanea e non viene distribuita.

TRPage raccoglie scopo, destinatari, messaggio, titolo, abstract e contenuti;
chiede se servono CTA e hero, il template, la posizione e l'URL finale, i link
per raggiungere la pagina e quelli nel contenuto. Produce una bozza Markdown
con brief, testi e indicazioni di realizzazione separate. Non pubblica sul sito;
la normale conclusione è il documento locale, mentre la consegna alla redazione
usa il runtime comune solo se richiesta e autorizzata. Domande già soddisfatte
vengono saltate; informazioni mancanti e proposte restano esplicite.

Per una rinomina aggiungere `vecchio-id: nuovo-id` alla mappa `renames` del
catalogo. Serve a trasferire le personalizzazioni Markdown locali; l’ID vecchio
non deve essere ancora una skill attiva. La mappa attuale è `trtalks → trstory`.

## Installazione e scelta

Nel progetto installato:

| Percorso | Responsabilità |
| --- | --- |
| `.trtalks/app/` | Applicazione e manifest della release |
| `.trtalks/app/runtime/` | Programma condiviso |
| `.agents/skills/ID/` | Ciascuna skill visibile a Codex |
| `.trtalks/config.local.json` | Impostazioni locali conservate |
| `.trtalks/overrides/ID/` | Personalizzazioni per la conversazione |
| `.trtalks/deliveries/` | Payload, request_id e ricevute persistenti |

`trtalks skills` elenca le conversazioni e i rispettivi prompt.
`trtalks paths` mostra i percorsi effettivi del runtime e delle skill.

Se `AGENTS.md` non esiste, l’installer crea una breve istruzione generale:
scegliere la skill coerente con la richiesta; con una richiesta generica e una
sola skill usare quella, con più skill chiedere quale. Le istruzioni specifiche
di progetto già esistenti non vengono sovrascritte o cancellate.

Gli aggiornamenti gestiscono l’insieme delle skill dichiarate. Le skill rimosse
dal catalogo vengono disattivate e conservate nei backup, incluse le rispettive
regole locali. Una skill con lo stesso nome ma non gestita da TRTalks blocca
l’aggiornamento invece di essere sovrascritta. Altre skill del progetto restano
invariate. Runtime e skill vengono ripristinati se una sostituzione fallisce.

## Passaggio dalla struttura precedente

Non è stata ancora pubblicata una release remota della vecchia struttura.
Per eventuali installazioni locali 0.2.0a1, eseguire il nuovo `setup.sh` oppure
il nuovo `runtime/manage.py install --upgrade` con archivio e checksum.
Il vecchio updater non comprende il manifest della nuova struttura: non basta
servirgli il nuovo ZIP senza aggiornare il bootstrap.

Il nuovo installer riconosce il manifest precedente e sposta le personalizzazioni
della skill `trtalks` nella nuova `trstory`; le personalizzazioni di backend e
invio passano alle regole condivise. Configurazione, bozze e stato di consegna
restano nella stessa posizione, senza rigenerare gli ID delle richieste.

## Verifiche e limiti

Il runtime 0.5.0a1 prepara la consegna per `send_email` del connettore Gmail.
Il collegamento Google è gestito dall’app; nessuna credenziale di posta resta
nella configurazione TRTalks. Le skill leggono il destinatario effettivo.
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

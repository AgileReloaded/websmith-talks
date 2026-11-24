# Distribuzione

Il catalogo `conversations.json` dichiara le skill distribuite. Costruire il
pacchetto con `python3 scripts/build_release.py --output dist`. Il manifest
contiene solo i file dichiarati; configurazione locale, bozze e ricevute non
vengono distribuite. I sorgenti salvati non aggiornano la release pubblica.

Il repository è `AgileReloaded/websmith-talks`; il pacchetto è
`websmith-talks.zip` e il suo prefisso interno è `websmith-talks/`.
Il launcher installato è `websmith-talks`, con le skill `story` e `page`.
Il bootstrap registra anche il comando globale in `~/.local/bin`; la directory
deve essere nel PATH. `websmith-talks install` installa nella cartella corrente,
`websmith-talks update` aggiorna il progetto anche da una sottocartella.
Dal checkout locale, `./websmith-talks command-install` registra lo stesso comando
usato nelle installazioni distribuite: installazione e aggiornamento scaricano
le release HTTPS con checksum. Per usare il nuovo comportamento nel normale
percorso utente è necessaria una release. Lo sviluppo locale richiede l'opzione
esplicita `--source CARTELLA` a ogni installazione o aggiornamento; non viene
selezionato automaticamente dal checkout o dai metadati precedenti.
Il setup richiede `site.id`, tramite domanda nel terminale, `--site-id` o
`WEBSMITH_TALKS_SITE_ID`. Nome, URL e destinatario sono facoltativi.
Ogni cartella serve un solo sito: update e configure rifiutano un ID diverso.
I metadati del sito restano locali e le nuove consegne usano `[websmith:site.id]`.
Per il passaggio da TRTalks usare il nuovo bootstrap sulla cartella esistente:
vedere la sezione dedicata nel README. Il vecchio updater non gestisce il nuovo ZIP.

`setup.sh` installa il pacchetto verificato. L’aggiornamento sostituisce runtime
e skill insieme, conserva le preferenze e i file `*.local.md` e rimuove i vecchi
parametri di connessione. I colleghi collegano Gmail nell’app; non devono
configurare un server di posta. Il tool `send_email` deve essere disponibile
nella chat usata per la conversazione.

Gli script di pubblicazione mantengono i controlli sul repository e sui tag.
La pubblicazione di una nuova release è un’operazione distinta dalle modifiche
locali e dai test del pacchetto.

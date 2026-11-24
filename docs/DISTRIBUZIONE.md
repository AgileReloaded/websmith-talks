# Distribuzione

Il catalogo `conversations.json` dichiara le skill distribuite. Costruire il
pacchetto con `python3 scripts/build_release.py --output dist`. Il manifest
contiene solo i file dichiarati; configurazione locale, bozze e ricevute non
vengono distribuite. I sorgenti salvati non aggiornano la release pubblica.

`setup.sh` installa il pacchetto verificato. L’aggiornamento sostituisce runtime
e skill insieme, conserva le preferenze e i file `*.local.md` e rimuove i vecchi
parametri di connessione. I colleghi collegano Gmail nell’app; non devono
configurare un server di posta. Il tool `send_email` deve essere disponibile
nella chat usata per la conversazione.

Gli script di pubblicazione mantengono i controlli sul repository e sui tag.
La pubblicazione di una nuova release è un’operazione distinta dalle modifiche
locali e dai test del pacchetto.

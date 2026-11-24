# websmith-talks

websmith-talks raccoglie conversazioni nell’app Codex. **Story** conduce interviste
su casi reali e prepara un resoconto Markdown. **Page** raccoglie contenuti
e indicazioni per una pagina web: scopo, destinatari, titolo, abstract, corpo,
CTA, template, hero, posizione e collegamenti. Le conversazioni seguono una
domanda alla volta e producono un documento locale.
Per una consegna autorizzata alla redazione, l’agente usa **send_email del
connettore Gmail** collegato alla chat.

Versione di sviluppo **0.8.0a1**: comandi `websmith-talks install` e
`websmith-talks update`, un sito per installazione e tag email
`[websmith:site.id]` compatibile con Websmith. Il comando è `websmith-talks`,
le skill sono `story` e `page` e lo stato è in `.websmith-talks`.
La consegna resta Gmail: il mittente è l’account Google collegato all’app.
Le conversazioni sono utilizzabili per siti e organizzazioni diversi, senza
un marchio o un destinatario email predefinito.

## Installazione e collegamento

Servono macOS/Linux, Python 3.9+, curl e l’app Codex. Per la consegna email serve
anche il connettore Gmail che espone `send_email` nella chat.
Il collegamento Google si effettua nell’app. websmith-talks non richiede
password, host, porte o variabili di connessione. Se il tool non è disponibile
nella chat, l’agente lo segnala e conserva il documento.

### Comando dal terminale

Dalla cartella dei sorgenti, registrare una sola volta il comando:

```bash
./websmith-talks command-install
export PATH="$HOME/.local/bin:$PATH"
```

Il comando viene scritto in `~/.local/bin/websmith-talks`. Se quella directory
non è già nel PATH, aggiungere la riga `export` al profilo della propria shell
per mantenerla nei terminali successivi. Un comando preesistente personalizzato
non viene sovrascritto. `WEBSMITH_TALKS_BIN_DIR` o `--bin-dir` permettono di
scegliere una directory diversa.

Poi, nella cartella che dovrà ospitare il progetto:

```bash
websmith-talks install
websmith-talks update
```

`install` usa la cartella corrente e chiede il `site.id` nel terminale.
È possibile indicare `--site-id`, `--site-name`, `--site-url`, `--recipient` e
`--root` direttamente. `update` ritrova il progetto anche dalle sottocartelle.
Si possono mantenere installazioni separate per siti diversi.

`install` e `update` scaricano sempre la release pubblicata su GitHub e
verificano il checksum, anche quando il comando è registrato dal checkout dei
sorgenti. Commit, push o modifiche locali non aggiornano la versione distribuita:
per provare il normale percorso utente occorre pubblicare una release.
Se GitHub non è disponibile, l'operazione fallisce senza usare i sorgenti locali
come alternativa automatica.

Per lavorare sui sorgenti prima di una release usare esplicitamente:

```bash
websmith-talks install --source /percorso/websmith-talks
websmith-talks update --source /percorso/websmith-talks
```

L'opzione va specificata a ogni operazione di sviluppo. Un successivo `update`
senza opzioni torna a controllare le release, anche per un progetto installato
in precedenza dai sorgenti. Il percorso locale conservato nei metadati è solo
un riferimento e non seleziona il comportamento degli aggiornamenti.
`--release-url URL` permette di scegliere una distribuzione remota alternativa.
Tutte le modalità conservano configurazioni, documenti, ricevute e sito associato.

Il bootstrap pubblico scarica la versione della release pubblicata su GitHub:

```bash
curl --proto '=https' --proto-redir '=https' -fsSL https://github.com/AgileReloaded/websmith-talks/releases/latest/download/setup.sh | bash
```

Il bootstrap registra anche il comando nel terminale; verificare che
`~/.local/bin` sia nel PATH. Successivamente usare `websmith-talks install`
nelle nuove cartelle e `websmith-talks update` nei progetti esistenti.

Aprire la cartella websmith-talks nell’app e scrivere:

> Usa $story per raccogliere un caso di progetto per il nostro sito.

Per preparare una pagina web:

> Usa $page per preparare una pagina web, una domanda alla volta.

## Un sito per installazione

Durante il setup indicare lo stesso `site.id` presente nel `websmith.yaml`
del sito gestito da Websmith. L'ID viene copiato esattamente: lettere minuscole,
numeri e trattini, senza ricavarlo dal nome o dall'indirizzo del sito.
Il setup lo chiede nel terminale se non è già configurato. Per un'installazione
non interattiva:

```bash
curl --proto '=https' --proto-redir '=https' -fsSL https://github.com/AgileReloaded/websmith-talks/releases/latest/download/setup.sh -o /tmp/websmith-talks-setup.sh
bash /tmp/websmith-talks-setup.sh --root "$HOME/talks-example" --site-id example --site-name "Example" --site-url https://example.org --recipient redazione@example.org
```

Solo `--site-id` è obbligatorio alla prima installazione; nome, URL e casella
email sono facoltativi. Si possono usare anche `WEBSMITH_TALKS_SITE_ID`,
`WEBSMITH_TALKS_SITE_NAME`, `WEBSMITH_TALKS_SITE_URL` e
`WEBSMITH_TALKS_RECIPIENT`. Il sito resta in `.websmith-talks/config.local.json`
e nei metadati locali dell'installazione, senza entrare nel pacchetto distribuito.

Gli aggiornamenti riusano il sito associato. Un ID diverso viene rifiutato;
per un altro sito usare un'altra cartella. Nome e URL sono modificabili con
`configure --site-name NOME --site-url URL`. `status` mostra sito e tag email.
Le due applicazioni restano separate: l'identificativo comune consente a
Websmith di selezionare le consegne destinate al proprio sito.

Page è inclusa nel pacchetto insieme a Story. Le domande sono in
[skills/page/references/domande.md](skills/page/references/domande.md).
La bozza viene salvata come `drafts/pagina-<slug>.md`, con suffisso se il file
esiste già. Include i testi e le indicazioni di realizzazione separate, con
le scelte ancora aperte. CTA e hero sono facoltative. La conversazione non
pubblica la pagina e la consegna email si esegue solo se richiesta e autorizzata.

`websmith-talks skills` elenca le conversazioni; `websmith-talks paths` mostra i percorsi.
Le nuove installazioni non hanno un destinatario email predefinito. Le bozze
locali si possono creare subito; per una consegna indicare la casella corretta:

```bash
websmith-talks configure --recipient redazione@example.org
```

Restano disponibili `--name` (autore nel corpo email), `--email` (Reply-To),
`--enable-send` e `--disable-send`. L’abilitazione non autorizza di per sé un invio:
ogni consegna usa l’autorizzazione della persona per il documento e destinatario.
`status` indica se il destinatario è configurato. Se manca, `send` e `dry-run`
si fermano senza creare tentativi; i destinatari già salvati sono conservati
durante gli aggiornamenti. Nessun indirizzo viene dedotto dal nome del sito.

Le skill usano il sito associato senza richiederlo a ogni conversazione;
raccolgono pubblico e scopo dalle indicazioni ricevute.
Story non presume l'uso dell'AI, un cliente esterno, una sezione
chiamata Stories o pannelli di sintesi obbligatori.

## Intervista e consegna

L’assistente fa una domanda alla volta, raccoglie le risposte, prepara il file
e lo mostra integralmente. Dopo l’autorizzazione alla consegna, esegue:

1. `dry-run`: verifica formato, destinatario e SHA-256 senza rete.
2. `send`: salva copia dei byte approvati e stato privato e restituisce gli
   argomenti Gmail. Questo comando **non invia** da solo.
3. La chiamata effettiva a `send_email` di Gmail con il `.md` in `attachment_files`.
4. `record-result`: conserva la risposta reale e l’ID del messaggio Gmail.

Ogni nuova email ha un solo tag all'inizio dell'oggetto, per esempio
`[websmith:example] websmith-talks — pagina-esempio.md`. Il valore `example`
deve coincidere con `site.id` del destinatario Websmith. Il tag non cambia
i byte del Markdown allegato. L'indirizzo email può essere condiviso fra siti:
il filtro di Websmith usa l'ID, non il nome del sito o il dominio della casella.

La persona intervistata non deve lanciare comandi di invio. Le istruzioni
operative sono in [invio.md](runtime/references/invio.md) e
[backend.md](runtime/references/backend.md). Se il connettore non accede a un
percorso locale, l’agente trasferisce il file tramite il canale supportato
nell’ambiente; se anche questo manca, dichiara il blocco senza fingere l’invio.

La conferma Gmail non prova la ricezione nella casella destinataria. Gli esiti
incerti richiedono verifica prima di un altro tentativo. Le ricevute già accettate
vengono riusate; `retry` non avvia mai un nuovo invio. Restano conservati anche
i tentativi dei trasporti precedenti, senza convertirli in nuove spedizioni.

`status` controlla solo le preferenze locali. Per verificare il collegamento
senza email, l’agente usa `get_profile` di Gmail. `probe` crea un Markdown
fittizio locale. Nessun test tecnico autorizza una spedizione.

## Aggiornamenti

```bash
websmith-talks update --dry-run
websmith-talks update
websmith-talks uninstall
```

L’aggiornamento conserva destinatario, preferenze, bozze, ricevute e regole
`*.local.md`. Elimina i parametri di connessione precedenti dalla configurazione,
senza conservarne la password nel backup della migrazione. Manifest e checksum
verificano i file; modifiche estranee bloccano la sostituzione. La disinstallazione
conserva i documenti e lo stato delle consegne.

## Passaggio da TRTalks

Usare il **nuovo installer** indicando la cartella dell’installazione esistente,
senza rinominarla o spostarla prima:

```bash
curl --proto '=https' --proto-redir '=https' -fsSL https://github.com/AgileReloaded/websmith-talks/releases/latest/download/setup.sh -o /tmp/websmith-talks-setup.sh
WEBSMITH_TALKS_HOME="$HOME/TRTalks" bash /tmp/websmith-talks-setup.sh --site-id example
```

L’installer rinomina lo stato in `.websmith-talks`, sostituisce il launcher
`trtalks` con `websmith-talks` e trasferisce le personalizzazioni da `trstory`
a `story` e da `trpage` a `page`. Supporta anche la vecchia skill singola
`trtalks`. Conserva configurazioni locali, bozze, allegati e ricevute, senza
cambiare gli ID dei tentativi. I tentativi `trtalks-…` continuano a impedire
invii duplicati; quelli nuovi usano `websmith-talks-…`.

I backup precedenti passano in `.websmith-talks/legacy-backups/`; il backup della
migrazione è in `.websmith-talks/backups/`. Le istruzioni `AGENTS.md` generate
dall’installer vengono aggiornate; quelle personalizzate restano intatte.
Conflitti fra skill o regole locali interrompono la migrazione senza sovrascriverli.

La variabile dell’installer è `WEBSMITH_TALKS_HOME` (con `TRTALKS_HOME` come
compatibilità); per una distribuzione alternativa usare `WEBSMITH_TALKS_RELEASE_URL`.
Il vecchio comando `trtalks update` non comprende il nuovo formato: il primo
passaggio richiede il bootstrap nuovo oppure `runtime/manage.py install --upgrade`
con il nuovo archivio e il relativo checksum.

Per installazioni websmith-talks precedenti senza sito, associarlo una sola volta
con `websmith-talks configure --site-id example` oppure passare `--site-id` al
nuovo installer o all'aggiornamento. Il passaggio conserva i dati e le ricevute:
i documenti già registrati continuano a bloccare duplicati. I vecchi messaggi
non vengono rispediti per aggiungere il tag. Le nuove consegne richiedono sia
il sito associato sia il destinatario configurato.

## Sviluppo

- `skills/`: istruzioni, domande, regole e template.
- `runtime/`: CLI, preparazione Gmail, ricevute e gestione installazioni.
- `scripts/build_release.py`: pacchetto deterministico con manifest.
- `tests/`: verifiche isolate senza email o connessioni esterne.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_release.py --output dist
./websmith-talks install --source "$PWD" --root /percorso/talks-example --site-id example
```

Il connettore Gmail è invocato dall’agente nell’app, non dal processo Python.
I test usano risposte sintetiche dichiarate e non costituiscono una prova di
invio reale né una prova della voce nell’app.

Quando l’ambiente protegge `.agents/`, questa installazione usa le skill
aggiornate dentro `.websmith-talks/app/skills/`, indicate da `AGENTS.md` e da `paths`.
La copia precedente protetta resta intatta; i futuri aggiornamenti mantengono
questa modalità e la stessa verifica del manifest.

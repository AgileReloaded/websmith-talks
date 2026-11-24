# TRTalks

TRTalks raccoglie conversazioni nell’app Codex. **TRStory** conduce interviste
su casi reali e prepara un resoconto Markdown. **TRPage** raccoglie contenuti
e indicazioni per una pagina web: scopo, destinatari, titolo, abstract, corpo,
CTA, template, hero, posizione e collegamenti. Le conversazioni seguono una
domanda alla volta e producono un documento locale.
Per una consegna autorizzata alla redazione, l’agente usa **send_email del
connettore Gmail** collegato alla chat.

Versione **0.5.0a1**: consegna Gmail, eliminazione della configurazione SMTP
e del comando `init`. Il mittente è l’account Google collegato all’app.

## Installazione e collegamento

Servono macOS/Linux, Python 3.9+, curl e l’app Codex. Per la consegna email serve
anche il connettore Gmail che espone `send_email` nella chat.
Il collegamento Google si effettua nell’app. TRTalks non richiede
password, host, porte o variabili di connessione. Se il tool non è disponibile
nella chat, l’agente lo segnala e conserva il documento.

Il comando pubblico scarica la release pubblicata, che può essere precedente
ai sorgenti locali finché la nuova versione non viene pubblicata:

```bash
curl --proto '=https' --proto-redir '=https' -fsSL https://github.com/AgileReloaded/TRTalks/releases/latest/download/setup.sh | bash
```

Aprire la cartella TRTalks nell’app e scrivere:

> Usa $trstory per raccogliere un caso TechReloaded.

Per preparare una pagina web:

> Usa $trpage per preparare una pagina web, una domanda alla volta.

TRPage è presente nei sorgenti di sviluppo; sarà disponibile nell'installer
pubblico dopo la prossima release. Le domande sono in
[skills/trpage/references/domande.md](skills/trpage/references/domande.md).
La bozza viene salvata come `drafts/pagina-<slug>.md`, con suffisso se il file
esiste già. Include i testi e le indicazioni di realizzazione separate, con
le scelte ancora aperte. CTA e hero sono facoltative. La conversazione non
pubblica la pagina e la consegna email si esegue solo se richiesta e autorizzata.

`trtalks skills` elenca le conversazioni; `trtalks paths` mostra i percorsi.
Il destinatario iniziale è `trtalks@techreloaded.it`. Si può cambiare con:

```bash
~/TRTalks/trtalks configure --recipient info@techreloaded.it
```

Restano disponibili `--name` (autore nel corpo email), `--email` (Reply-To),
`--enable-send` e `--disable-send`. L’abilitazione non autorizza di per sé un invio:
ogni consegna usa l’autorizzazione della persona per il documento e destinatario.

## Intervista e consegna

L’assistente fa una domanda alla volta, raccoglie le risposte, prepara il file
e lo mostra integralmente. Dopo l’autorizzazione alla consegna, esegue:

1. `dry-run`: verifica formato, destinatario e SHA-256 senza rete.
2. `send`: salva copia dei byte approvati e stato privato e restituisce gli
   argomenti Gmail. Questo comando **non invia** da solo.
3. La chiamata effettiva a `send_email` di Gmail con il `.md` in `attachment_files`.
4. `record-result`: conserva la risposta reale e l’ID del messaggio Gmail.

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
~/TRTalks/trtalks update --dry-run
~/TRTalks/trtalks update
~/TRTalks/trtalks uninstall
```

L’aggiornamento conserva destinatario, preferenze, bozze, ricevute e regole
`*.local.md`. Elimina i parametri di connessione precedenti dalla configurazione,
senza conservarne la password nel backup della migrazione. Manifest e checksum
verificano i file; modifiche estranee bloccano la sostituzione. La disinstallazione
conserva i documenti e lo stato delle consegne.

## Sviluppo

- `skills/`: istruzioni, domande, regole e template.
- `runtime/`: CLI, preparazione Gmail, ricevute e gestione installazioni.
- `scripts/build_release.py`: pacchetto deterministico con manifest.
- `tests/`: verifiche isolate senza email o connessioni esterne.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_release.py --output dist
```

Il connettore Gmail è invocato dall’agente nell’app, non dal processo Python.
I test usano risposte sintetiche dichiarate e non costituiscono una prova di
invio reale né una prova della voce nell’app.

Quando l’ambiente protegge `.agents/`, questa installazione usa le skill
aggiornate dentro `.trtalks/app/skills/`, indicate da `AGENTS.md` e da `paths`.
La copia precedente protetta resta intatta; i futuri aggiornamenti mantengono
questa modalità e la stessa verifica del manifest.

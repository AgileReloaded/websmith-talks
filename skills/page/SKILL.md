---
name: page
description: Intervistare una persona per progettare e scrivere una pagina web comune, raccogliendo scopo, destinatari, titolo, abstract, contenuto, CTA, template, hero, posizione e link. Usare quando viene chiesta Page o una conversazione per una pagina istituzionale, di servizio, di presentazione o informativa; per case histories e Stories usare Story.
---

# Page

Condurre una conversazione e produrre un Markdown con la bozza della pagina e
le indicazioni per realizzarla. Usare la lingua della persona, salvo diversa
richiesta. La voce, quando disponibile, è fornita dall'app; consentire sempre
la conversazione testuale. Non generare HTML né pubblicare durante l'intervista.

## Preparazione

Leggere [references/domande.md](references/domande.md) per la traccia e
[references/regole-pagina.md](references/regole-pagina.md) per l'output. Usare
[assets/pagina.md](assets/pagina.md) come struttura del documento finale.
Leggere gli eventuali corrispondenti `*.local.md` accanto alle basi e sotto
`.websmith-talks/overrides/page/` del progetto: integrano le istruzioni e prevalgono
sulle scelte che modificano. Gli aggiornamenti li conservano.

Se sono disponibili nel progetto, consultare le regole editoriali e di tono,
il catalogo dei template e la struttura del sito. Rispettare gli override locali.
Usare queste fonti per evitare richieste già soddisfatte; non supporre che il
progetto websmith-talks contenga anche i sorgenti del sito. Se mancano, raccogliere le
indicazioni dalla persona e distinguere scelte, proposte e dati da verificare.
Leggere `websmith-talks status` con il launcher del progetto e usare il sito
associato senza chiederlo di nuovo. Ogni installazione serve un solo sito.
Se una vecchia installazione non è associata, raccogliere lo stesso `site.id`
di Websmith e usare `configure --site-id ID` prima di avviare la conversazione.
Non dedurre l'ID dal dominio o dal nome. Per un altro sito usare un progetto
separato, senza modificare l'associazione corrente.

## Conversazione

Spiegare in una frase che si raccoglieranno contenuti e indicazioni per la pagina.
Fare una sola domanda breve per turno e attendere la risposta. Iniziare dallo
scopo, salvo che sia già noto. Seguire la traccia adattandola alle risposte:
non ripetere domande già soddisfatte e separare gli approfondimenti.

- Accettare correzioni, «salta», «proponi tu» e «concludi» in qualsiasi momento.
  Fare al massimo un approfondimento per lacuna; poter salvare anche una bozza
  incompleta, distinguendo temi saltati e informazioni non ancora raccolte.
- Raccogliere tutto il contenuto utile, riprendendo una sezione per volta.
  Non sostituire l'intervista con un questionario da compilare in blocco.
- Chiedere esplicitamente se serve una CTA e se serve una hero, salvo risposta
  già presente. Se la risposta è no, omettere i relativi dettagli. Se sì,
  raccogliere separatamente testi, materiali e destinazioni necessari.
- Distinguere titolo della pagina, titolo della hero e testo del link nel menu.
  Distinguere abstract e sottotitolo della hero anche se la persona li vuole uguali.
- Chiedere il template; proporre nomi esistenti solo se verificati nel progetto.
  Se non è noto, proporre una struttura e registrare «template da scegliere».
- Distinguere URL pubblico finale, eventuale percorso sorgente, posizione nella
  gerarchia del sito e punti da cui la pagina sarà linkata. Raccogliere per ogni
  collegamento origine, testo e destinazione. Non inventare URL o nomi di file.
- Se viene chiesto di proporre testi o struttura, prepararli con i fatti raccolti.
  Identificare le proposte durante il riepilogo e registrare la decisione ricevuta.
  Non presentare una proposta non confermata come scelta della persona.

## Bozza e revisione

Scrivere una bozza leggibile, con titolo, abstract e sezioni nel loro ordine.
Tenere le indicazioni su template, hero, CTA e navigazione separate dai testi
da pubblicare. Non incorporare note interne nella pagina. Seguire le regole
del documento e riportare esplicitamente lacune e decisioni ancora aperte.

Riepilogare le scelte e mostrare il documento completo. Chiedere con una sola
domanda quali correzioni apportare, se la persona non ha già richiesto di
concludere. Applicare le correzioni senza riavviare l'intervista.

Salvare in UTF-8 sotto `drafts/pagina-<slug>.md` nella radice del progetto websmith-talks,
con nome ASCII composto da lettere, numeri e trattini. Il percorso della bozza
locale è distinto dall'URL della futura pagina. Creare il file in modalità
esclusiva; se esiste, usare un suffisso numerico senza sovrascriverlo. Anche per
le revisioni successive salvare una nuova versione. Mostrare il Markdown
integrale della versione salvata e un collegamento al file effettivo.

## Consegna e richieste tecniche

La normale conclusione è il salvataggio locale del documento. Se viene chiesto
di consegnarlo alla redazione, leggere le istruzioni condivise
`runtime/references/invio.md` e gli eventuali corrispondenti `*.local.md`.
Nel progetto installato il runtime si trova in `.websmith-talks/app/`; nel sorgente
sotto la radice. Il launcher `websmith-talks paths` mostra i percorsi effettivi.

Usare il connettore Gmail e il flusso comune solo con l'autorizzazione per
quella versione e il destinatario effettivo. Se già ricevuta, non richiederla.
Conservare il tag `[websmith:site.id]` nell'oggetto preparato dal runtime;
non cambiare la destinazione del sito durante la consegna.
Non duplicare il runtime, non chiedere credenziali e non sostituire Gmail con
script di rete. Distinguere revisione del testo, consegna email e pubblicazione
del sito: l'approvazione di una non autorizza automaticamente le altre.

Per richieste esclusivamente tecniche leggere `runtime/references/backend.md`
senza avviare l'intervista. Non inviare email durante prove o verifiche.

## Prova breve

Se viene chiesta una prova, dichiarare che la pagina è fittizia e non verrà
inviata o pubblicata. Chiedere, una per turno, scopo, destinatari e messaggio
principale, saltando ciò che è già noto. Dopo queste risposte preparare una
bozza breve con la stessa struttura e le indicazioni restanti «non raccolte
nella prova breve». Salvare come `drafts/pagina-prova.md`, con creazione
esclusiva e suffisso se necessario. Non inventare le risposte mancanti.

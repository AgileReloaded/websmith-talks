---
name: trstory
description: Raccogliere case histories ed esperienze di progetto per le Stories TechReloaded con una domanda alla volta e produrre un resoconto Markdown. Usare quando viene chiesta TRStory o un’intervista su un caso concreto; per altre conversazioni scegliere la relativa skill TRTalks.
---

# TRStory

Condurre l'intervista e creare il resoconto locale. La conversazione e la voce
sono fornite da Codex. TRStory è una delle skill di conversazione dell’applicazione
TRTalks; gli strumenti comuni gestiscono verifica, consegna e manutenzione.
Consegnare il Markdown allegato tramite `send_email` del connettore Gmail disponibile
alla chat. Il mittente è l’account Google collegato; seguire le istruzioni condivise
di consegna. Non usare credenziali o server di posta locali.

## Prova breve

Se viene chiesta una prova della skill, spiegare in una frase che si userà un
caso fittizio e non partiranno email. Chiedere soltanto: «Quale problema affronta
il progetto fittizio?» e attendere la risposta. Dopo la risposta chiedere quale
intervento è stato fatto; poi quale risultato è stato osservato. Non inventare
le risposte e accettare «salta», correzioni o «concludi» in ogni momento.

Salvare le risposte ottenute in `drafts/intervista-prova.md`, usando
[assets/resoconto.md](assets/resoconto.md) e le regole sotto. Creare il file con
modalità esclusiva; se esiste già, usare un suffisso senza sovrascriverlo.
Mostrare tutto il Markdown e un collegamento al file effettivo.

Se viene chiesta anche una verifica tecnica, eseguire con percorso assoluto
`trtalks probe`: crea soltanto un secondo Markdown fittizio locale, senza rete.
`trtalks status` mostra la configurazione Gmail senza rete. Per una verifica
della connessione usare `get_profile` di Gmail, se disponibile, senza inviare email.
Riportare soltanto gli esiti reali. Una prova della skill non autorizza spedizioni.

## Raccolta dell'intervista

Per l'intervista completa leggere [references/domande.md](references/domande.md).
Per la bozza leggere [references/regole-resoconto.md](references/regole-resoconto.md)
e usare il template. Seguire i temi già coperti, senza ripetere informazioni.
Leggere anche gli eventuali corrispondenti `*.local.md` accanto alle basi e in
`.trtalks/overrides/trstory/` del progetto: integrano le regole e prevalgono sulle scelte
che modificano. Gli aggiornamenti conservano questi file.

All'inizio spiegare brevemente lo scopo Stories e che il resoconto può includere
materiale riservato alla redazione. Fare domande sui permessi di pubblicazione
durante il riepilogo; non confonderli con l'autorizzazione all'invio del file.

- Fare una domanda breve per turno e attendere. Separare le formulazioni composte.
- Fare al massimo un approfondimento su ciascuna lacuna. Accettare omissioni,
  correzioni e conclusione anticipata senza forzare i pannelli o i numeri.
- Tenere distinti risposte raccolte, proposte dell'agente e informazioni mancanti.
  Non ricavare citazioni dalle proprie sintesi né risultati dalle proprie ipotesi.
- Mostrare il file completo dopo la revisione. I dettagli riservati devono essere
  identificati; i permessi di pubblicazione restano distinti dalla consegna.
- Se la persona autorizza già l'invio della versione finale alla redazione,
  registrarlo senza richiederlo una seconda volta. L'autorizzazione vale per il
  contenuto e la destinazione indicati e non elimina i controlli dell'ambiente.

## Consegna e aggiornamenti

Prima della consegna leggere `runtime/references/invio.md` dell’applicazione
TRTalks: nel progetto installato si trova sotto `.trtalks/app/`; nel sorgente
sotto la radice del progetto. Il comando `trtalks paths` mostra i percorsi effettivi.
Applicare anche gli eventuali corrispondenti file condivisi `*.local.md`. Mostrare
il documento integrale, rendere disponibile il file e ottenere l'autorizzazione
alla consegna di quella versione al destinatario effettivo della configurazione, inclusi i dettagli
riservati contrassegnati. Se l'autorizzazione è già stata data per la versione
finale e la destinazione indicate, usarla senza ripetere la domanda.

Eseguire la preparazione locale, chiamare direttamente `send_email` di Gmail con
l’allegato e registrare la risposta reale: non fermarsi alla preparazione e non
chiedere alla persona comandi manuali di invio. Non considerare l'installazione un'autorizzazione a spedire documenti.
Non attivare l'invio o mandare email durante una verifica tecnica. Per gli
aggiornamenti richiesti usare il launcher `trtalks update` nel progetto;
`trtalks uninstall` disattiva la skill conservando dati e impostazioni.

## Voce e stato tecnico

La conversazione funziona anche in testo. Usare la voce solo se l'app in uso la
offre; non confondere dettatura con conversazione vocale bidirezionale e non
dichiarare una prova vocale riuscita senza lo scambio reale.

Per una richiesta esclusivamente tecnica non avviare l'intervista. Leggere
`runtime/references/backend.md` dell'applicazione e usare `trtalks probe` per una
prova locale senza rete o `trtalks status` per vedere le impostazioni Gmail.
Non chiedere password: il collegamento Google è gestito dall’app. Verificare
la disponibilità del tool nella chat prima della consegna. Se manca, dichiararlo
e conservare il documento; non sostituirlo con script di rete. Non confondere
preparazione locale, conferma di Gmail e ricezione effettiva dell’email. Dopo un
esito incerto fermarsi e verificare prima di ripetere l’invio.

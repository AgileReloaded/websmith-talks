# Verifica

Eseguire `python3 -m unittest discover -s tests -v`. La suite verifica
migrazione delle preferenze, rimozione dei parametri di connessione, autorizzazione,
conservazione dei byte del Markdown, preparazione Gmail, errori, ricevute,
blocchi sui duplicati e installazioni/aggiornamenti con rollback. Include il
passaggio da TRTalks con skill singola o catalogo, lo spostamento delle regole
locali, il mantenimento delle ricevute precedenti e il nuovo bootstrap shell.
I download del bootstrap nei test sono sostituiti da file locali dichiarati.

I risultati Gmail nei test sono sintetici; nessuna email viene inviata.
`websmith-talks status` legge solo la configurazione. Per una verifica reale senza email
usare `get_profile` di Gmail nella chat. Una prova reale di consegna richiede
un file e destinatario autorizzati e la risposta effettiva di `send_email`.

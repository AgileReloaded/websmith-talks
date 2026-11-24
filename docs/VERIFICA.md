# Verifica

Eseguire `python3 -m unittest discover -s tests -v`. La suite verifica
migrazione delle preferenze, rimozione dei parametri di connessione, autorizzazione,
conservazione dei byte del Markdown, preparazione Gmail, errori, ricevute,
blocchi sui duplicati e installazioni/aggiornamenti con rollback.

I risultati Gmail nei test sono sintetici; nessuna email viene inviata.
`trtalks status` legge solo la configurazione. Per una verifica reale senza email
usare `get_profile` di Gmail nella chat. Una prova reale di consegna richiede
un file e destinatario autorizzati e la risposta effettiva di `send_email`.

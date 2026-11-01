# Filtro tematico

Verifica del job 124894347883, esecuzione 41322115507 del 1 novembre 2026.
Il vecchio filtro accettava "battle with cancer" come guerra; escludeva gli
attacchi a Gaza e il pattugliamento cinese contro la navigazione a Taiwan.
I titoli dei sei casi in filter_regressions.json provengono dai registri.
La descrizione di Ciara Mageean è quella stampata dal collector nei registri;
le descrizioni non disponibili sono vuote, senza ricostruzioni inventate.

Il nuovo modulo usa confini di parola, elimina metafore mediche, richiede
coppie contestuali per attacchi, energia e infrastrutture. Sport e altri
contesti misti non sono un veto assoluto: richiedono verifica semantica.
Geografia, battle, security, solar e port isolati non autorizzano la selezione.

Solo gli ambigui passano a GPT-5 nano: massimo 8 richieste per raccolta,
400 caratteri di titolo, 1400 di descrizione, 512 token di completamento,
20 secondi per richiesta, nessun tentativo aggiuntivo. Cache in memoria
anche per errori. Inclusione solo con booleano true, categoria ammessa,
risposta completa e citazione presente nei dati trasmessi.
Chiave assente, budget esaurito, errore o risposta invalida => esclusione.
La chiave esistente è disponibile nel passo di pubblicazione, che esegue
nuovamente la raccolta; il passo preliminare resta senza costi AI.
La cache non è persistente e non modifica l'archivio.

Validazione locale:

    python -m unittest -v test_news_filter.py
    python simulate_filter.py

Esito: 13 test superati. Replay offline: atleta esclusa, Gaza e Taiwan
incluse, tre articoli selezionati, zero invii, zero scritture archivio e
zero chiamate AI. Il ciclo reale del publisher viene eseguito con DRY_RUN
attivo; rete e apertura di file sono bloccate e la sintesi è simulata.
Le chiamate AI sono testate con risposte simulate, non con le credenziali
di produzione. Il replay non è una nuova raccolta live.

Programmazione ogni due ore, limite di tre articoli, fonti, archivio,
publisher e credenziali restano invariati.

Riferimenti API:
- https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
- https://developers.openai.com/api/docs/models/gpt-5-nano

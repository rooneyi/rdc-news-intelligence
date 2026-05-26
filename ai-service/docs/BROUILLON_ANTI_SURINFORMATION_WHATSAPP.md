# Brouillon — Lutter contre la surinformation *et* la surcharge WhatsApp

> **Statut :** idées en vrac, pas encore validées ni implémentées.  
> **Contexte :** utilisateur noyé sous des messages similaires (amis + groupes) qui répètent la même rumeur ou le même sujet ; le bot ne doit pas ajouter une *nième* réponse identique.

---

## 1. Problème (formulation)

| Situation | Effet sur l’utilisateur |
|-----------|-------------------------|
| 5 amis envoient la même capture / la même phrase | Même peur ou colère répétée 5 fois |
| Dans un groupe, 20 messages sur le même fait | Fil illisible, impossible de savoir ce qui est vrai |
| Le bot répond à *chaque* message proche | Surcharge supplémentaire : 10 fact-checks quasi identiques |
| Variantes légères (« c’est vrai ??? », « regarde ça », lien différent) | Le texte diffère mais le **sens** est le même |

**Objectif double :**

1. **Réduire le bruit** (ne pas répéter l’information / la vérification).
2. **Garder la valeur** (une réponse fiable, à jour, avec sources, quand c’est vraiment nouveau ou demandé).

---

## 1 bis. Vision produit (ce qu’on veut pour l’utilisateur)

**Formulation :** quand l’utilisateur reçoit (ou déclenche) **beaucoup de messages de même sens**, le système ne doit **pas** le noyer — il doit lui laisser **une seule information pertinente**, claire et vérifiable.

### Ce qu’on vise côté expérience

| Au lieu de… | On veut… |
|-------------|----------|
| 10 réponses du bot quasi identiques | **1** réponse complète par sujet, puis silence ou renvoi court |
| 15 messages amis + bot sur la même rumeur | **1 fiche** « voici ce qu’on sait » + compteur optionnel (« 12 messages similaires regroupés ») |
| Relire toute la rafale pour comprendre | Un **résumé unique** avec verdict + liens sources |

### Ce qu’on contrôle vs ce qu’on ne contrôle pas (WhatsApp)

| Action | Possible ? | Comment |
|--------|------------|---------|
| **Ne plus envoyer** nous-mêmes des doublons | Oui | Dédup + cooldown sur les réponses du **bot** |
| **Regrouper** plusieurs messages entrants avant RAG | Oui | Buffer par `chat_id` (fenêtre 30–60 s) |
| **Renvoyer** une seule fiche au lieu de tout refaire | Oui | Story card + « déjà vérifié → lien » |
| **Supprimer** les messages des amis dans le groupe | Non (sauf bot admin avec droits rares) | On ne « efface » pas le fil des autres |
| **Masquer** pour l’utilisateur ce qu’il a déjà reçu | Indirectement | Le bot **ne rajoute pas** du bruit ; il peut proposer **une synthèse** qui remplace mentalement la rafale |

**En pratique :** on ne « supprime » pas l’historique WhatsApp des autres, mais on **arrête d’amplifier** la surinformation et on **consolide** ce que *notre* service affiche en **une seule brique utile**.

### Les 3 leviers retenus (ordre logique)

1. **Entrée — fusionner**  
   Plusieurs messages même sens dans la même fenêtre → **un seul** passage RAG (pas 10 analyses).

2. **Mémoire — ne pas répéter**  
   Même sujet déjà traité dans ce chat (24–72 h) → réponse **courte** + lien vers la fiche, **sans** rappeler Mistral sur tout le texte.

3. **Sortie — une fiche par sujet**  
   Première fois : message complet (verdict + explication + sources).  
   Ensuite : « 📌 Déjà traité — [lien] — IMPRÉCIS en bref : … »

### Message type « une seule info pertinente »

```
📌 Sujet : changement de la Constitution (regroupé)

🚨 VÉRIFICATION : IMPRÉCIS
📝 En bref : [2–3 phrases]
🔗 Sources : [liens]

ℹ️ 8 messages proches ont été fusionnés pour cette réponse.
   Même sujet ? Répondez @bot avec un angle nouveau.
```

### Décisions produit proposées (à valider)

| Sujet | Proposition |
|-------|-------------|
| Réponses du bot en rafale | **Interdites** — 1 réponse / cluster / fenêtre |
| Même sujet < 24 h | Renvoi fiche, pas nouveau pavé Mistral |
| Groupe très actif | Option **digest** si > N messages/min sur même cluster |
| Demande explicite `@bot vérifie` | Toujours traiter (bypass cooldown) |

---

## 2. Ce que le projet fait déjà (point de départ)

| Mécanisme | Fichier / comportement | Limite actuelle |
|-----------|------------------------|-----------------|
| **Topic gate** (groupes) | `TopicGateService` — active le bot seulement si thème RDC (politique, sport, santé, guerre) | Ne détecte pas « même rumeur déjà traitée » |
| **Seuil similarité RAG** | `RAG_MIN_SIMILARITY_MSG` — filtre articles corpus peu pertinents | Pas de mémoire des questions déjà vues dans le chat |
| **Top-k limité** | `WHATSAPP_TOP_K=3` | Réduit la taille de réponse, pas les doublons de réponses |
| **Dédup articles** | Postgres `ON CONFLICT`, hash lien | Dédup du **corpus**, pas des **messages entrants** |
| **Re-ranking LLM** | `LLMService.rerank` | Améliore l’ordre des sources, pas la dédup conversation |

---

## 3. Pistes produit (côté utilisateur final)

### 3.1 Mode « digest » au lieu de réponse immédiate

- **Idée :** dans un groupe bruyant, le bot n’envoie pas 15 messages ; il envoie **1 synthèse par fenêtre** (ex. toutes les 30 min ou quand 5 messages proches ont été détectés).
- **Contenu :** « 12 messages parlaient de [sujet X]. Voici ce que disent nos sources : … »
- **Avantage :** une seule lecture utile.
- **Risque :** latence perçue ; utilisateurs veulent une réponse instantanée.

### 3.2 Carte « histoire » épinglée (story card)

- **Idée :** première fois qu’un **cluster sémantique** apparaît dans le groupe → réponse complète + lien court stable (`rdc.news/verify/abc123`).
- **Ensuite :** messages similaires → réponse courte : « Déjà vérifié ici 👉 [lien]. Résumé : IMPRÉCIS parce que … »
- **Avantage :** zéro répétition du long texte Mistral.
- **Besoin :** stocker `story_id` + embedding du cluster + verdict + date.

### 3.3 Mode silencieux / opt-in fort en groupe

- **Idée :** le bot ne parle que si :
  - mention `@bot`, ou
  - mot-clé `vérifie`, ou
  - admin a activé le mode « actif » sur le groupe.
- **Complément topic gate :** évite les réponses sur le bruit social hors sujet.

### 3.4 Bouton ou commande « résumer le fil »

- **Idée :** l’utilisateur demande explicitement un résumé factuel du débat en cours (pas automatique).
- **Limite WhatsApp :** l’API ne donne pas toujours tout l’historique du groupe — à voir selon Whapi/Meta.

### 3.5 Liste personnelle « rumeurs déjà vues »

- **Idée :** en privé, l’utilisateur reçoit : « 3 contacts ont partagé une info similaire sur [X] — une seule fiche ».
- **Hors scope immédiat :** nécessite agrégation multi-chats (confidentialité, consentement).

---

## 4. Pistes techniques (côté bot / backend)

### 4.1 Mémoire courte par conversation (priorité haute)

**Principe :** avant de lancer le RAG complet, comparer l’embedding de la nouvelle requête aux **N dernières requêtes** du même `chat_id` (groupe ou DM).

```
nouvelle_question → embedding
    → similarité cosinus vs cache[chat_id] (dernières 24h)
    → si max_similarity > SEUIL (ex. 0.88) :
          réponse courte + lien vers dernière fiche
      sinon :
          RAG complet + enregistrer dans cache
```

| Paramètre | Exemple |
|-----------|---------|
| `CONV_DEDUP_THRESHOLD` | 0.85 – 0.92 |
| `CONV_DEDUP_TTL_HOURS` | 24 – 72 |
| `CONV_DEDUP_MAX_ENTRIES_PER_CHAT` | 20 |

**Stockage possible :** Redis, table Postgres `conversation_query_cache`, ou fichier local en dev.

**Alignement projet :** réutiliser `EmbeddingService` + même modèle que Chroma.

### 4.2 Clustering de messages entrants (fenêtre glissante)

**Principe :** buffer les messages texte du groupe pendant 2–5 min ; si plusieurs embeddings tombent dans le même cluster → **une seule** passe au RAG.

```
Message1 ─┐
Message2 ─┼─► cluster_id = f(embeddings) ─► 1× RAG ─► 1× réponse (ou digest)
Message3 ─┘
```

**Variante :** ne garder que le message le plus « informatif » (plus long, ou contient une question explicite).

**Référence mémoire projet :** notions *Clustering sémantique (NEC_SRG)*, *Réduction de redondance (InFRSS)* dans `Plan_Corrige.md`.

### 4.3 Détection « même affirmation » vs « angle nouveau »

**Principe :** après clustering, un petit appel LLM (ou règles) décide :

| Cas | Action |
|-----|--------|
| Même fait, même formulation | Pas de RAG / renvoi fiche |
| Même fait, **nouvelle** source ou date | RAG ciblé « quoi de neuf » |
| Fait **différent** mais même thème (ex. constitution vs élections) | RAG normal |

**Prompt type :** « Ces deux textes vérifient-ils la *même* affirmation factuelle ? OUI/NON + une phrase. »

### 4.4 Cooldown par sujet dans le groupe

- **Idée :** après une réponse sur le cluster `story_id=X`, ignorer les messages du même cluster pendant `COOLDOWN_MINUTES=30` sauf mention explicite du bot.
- **Évite :** spam du bot quand le groupe continue à paniquer sur le même sujet.

### 4.5 Normalisation du texte avant comparaison

Avant embedding, appliquer :

- minuscules, suppression URLs dupliquées ;
- retrait des formules (« stp vérifie », « c’est vrai ??? », emojis répétés) ;
- **hash MinHash** ou **SimHash** en pré-filtre rapide (pas d’appel embedding si hash proche).

### 4.6 File d’attente intelligente (complément mode PULL actuel)

Aujourd’hui : 1 message pop → 1 traitement.  
**Évolution :** le worker local **regroupe** les items de la file Whapi par `chat_id` dans une fenêtre de 10 s avant dispatch.

### 4.7 Réponse progressive déjà partielle

Le code stream déjà (`WHATSAPP_STREAM_WHILE_GENERATING`).  
**Idée anti-surcharge :** si un 2ᵉ message arrive pendant la génération du 1ᵉʳ et est sémantiquement proche → **annuler** ou **fusionner** la 2ᵉ requête dans le buffer du 1ᵉʳ.

---

## 5. Spécifique « groupe qui parle tous de la même chose »

### 5.1 Comportements souhaités (à trancher)

| Option | Description |
|--------|-------------|
| **A — Passif** | Le bot ne répond qu’à @mention ; sinon silence. |
| **B — Modérateur** | 1 message / heure max par sujet : « Le groupe discute de X ; verdict : … » |
| **C — Fil conducteur** | Répond seulement au *premier* message du cluster ; les suivants = emoji ✅ + lien |
| **D — Escalade** | Si > N messages/min sur même cluster → digest + suggestion « vérifiez ce lien » |

### 5.2 Signaux faibles sans tout l’historique WhatsApp

Même si l’API ne voit pas tout le fil :

- compter les messages **entrant webhook** sur la même fenêtre ;
- utiliser le **nom du groupe** + **mots récurrents** dans les 10 derniers payloads ;
- heuristique : 3+ messages avec > 70 % mots en commun → cluster.

### 5.3 Message type « anti-submersion »

Exemple de réponse unique :

```
📌 Sujet déjà traité dans ce groupe (il y a 18 min)

🚨 VÉRIFICATION : IMPRÉCIS
📝 En bref : …
🔗 Fiche complète : https://…

💡 6 messages similaires ont été regroupés. Posez @bot + une question nouvelle pour un autre angle.
```

---

## 6. Métriques à suivre (pour valider une piste)

| Métrique | Intérêt |
|----------|---------|
| `rag_calls_avoided_by_dedup` | Combien de RAG évités |
| `avg_messages_per_cluster` | Taille des rafales |
| `user_complaints` / blocages bot | Surcharge perçue |
| `time_to_first_response` vs `digest_delay` | Compromis latence |
| `repeat_story_hit_rate` | % réponses « déjà vérifié » |

---

## 7. Contraintes & limites (à ne pas oublier)

| Contrainte | Impact |
|------------|--------|
| **RAM Ollama** | Chaque rerank + topic gate + RAG = plusieurs appels ; la dédup *réduit* les appels |
| **Whapi / Meta** | Pas d’accès garanti à l’historique complet du groupe |
| **Vie privée** | Stocker les embeddings des messages utilisateurs → politique de rétention courte (TTL) |
| **Multilingue / code-switch** | « Constitution » vs « changement constitution » — seuils à calibrer |
| **Images identiques, légendes différentes** | OCR + embedding sur texte extrait ; comparer aussi perceptual hash image ? |

---

## 8. Roadmap indicative (ordre suggéré)

| Phase | Livrable | Effort estimé |
|-------|----------|----------------|
| **P0** | Cache embedding par `chat_id` + réponse « déjà vérifié » | Moyen |
| **P0** | Cooldown par cluster après 1ʳᵉ réponse | Faible |
| **P1** | Buffer 30–60 s sur worker file Whapi (regroupement) | Moyen |
| **P1** | Story card + URL stable (table `verification_stories`) | Moyen |
| **P2** | Digest périodique par groupe | Moyen–élevé |
| **P2** | Détection « angle nouveau » via mini-LLM | Moyen |
| **P3** | Agrégation multi-contacts (privé) | Élevé + légal |

---

## 9. Questions ouvertes (à décider avant de coder)

1. En groupe, le bot doit-il **toujours** répondre si le sujet est RDC, ou seulement sur **mention** ?
2. Quand on regroupe, qui est **cité** dans la réponse (premier auteur, personne qui a @bot) ?
3. Durée de mémoire : 24 h, 7 jours ?
4. Faut-il une commande `!reset` pour effacer le cache du groupe (admins) ?
5. Réponse « déjà vérifié » : même ton que fact-check complet ou ultra-court ?
6. Images : deux captures identiques avec légendes différentes = même cluster ?

---

## 10. Liens avec la doc existante

| Document | Lien |
|----------|------|
| `FLUX_WHATSAPP_VERS_DRAWIO.md` | Où insérer le bloc « dédup / cache » dans le schéma |
| `Plan_Corrige.md` | InFRSS, NEC_SRG, Stories |
| `topic_gate_service.py` | Filtre thème amont ; complémentaire à la dédup |
| `rag_service.py` | Point d’insertion : avant `generate_answer_stream` |

---

## 11. Esquisse d’architecture cible (à dessiner plus tard)

```
Webhook message
    → parse (texte / image+OCR)
    → [Topic gate] (groupe)
    → [Normalisation texte]
    → [Dedup conversationnel] ──hit──► Réponse courte (story card)
    │         │
    │        miss
    │         ▼
    → [Buffer cluster optionnel]
    → RAG (Chroma + Mistral)
    → Enregistrer story + cache embedding
    → Réponse WhatsApp (stream ou digest)
```

---

*Dernière mise à jour : brouillon initial — à commenter, prioriser, puis découper en tickets / issues.*

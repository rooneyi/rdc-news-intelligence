---
title: "RDC News Intelligence — Résumé des résultats"
author: "Rooney Kalumba"
date: "26 mai 2026"
---

# RDC News Intelligence — Résumé des résultats

## 1. Démarcation du projet (en quoi il est différent)

| Approche habituelle | RDC News Intelligence |
|---------------------|------------------------|
| **Chatbot généraliste** (ChatGPT, etc.) | Répond à partir d’une **base d’articles RDC** indexée, pas de « savoir général » libre |
| **Réseaux sociaux** | Ne supprime pas les messages des autres ; le bot **vérifie** et **cite des liens médias** |
| **Fact-check manuel seul** | Automatise la **recherche** dans le corpus et propose un **verdict structuré** |
| **Traduction automatique** | **Trois langues** d’entrée (FR, EN, SW) avec recherche **multilingue**, mais preuves liées au **contenu réellement indexé** |

**Position du projet :** un **assistant de vérification** pour l’actualité de la RDC, accessible (notamment via **WhatsApp**), qui privilégie la **traçabilité** (sources) plutôt que la vitesse ou le volume de texte.

---

## 2. Lutte contre la désinformation et la surinformation

Deux problèmes distincts, traités différemment :

| Problème | Définition simple | Réponse du système |
|----------|-------------------|-------------------|
| **Désinformation** (*fake news*) | Information **fausse ou trompeuse** présentée comme un fait | **Vérification RAG** : comparer la rumeur aux articles du corpus → verdict **VRAI**, **FAUX**, **IMPRÉCIS** ou **NON VÉRIFIABLE** + liens sources. Le modèle est contraint de s’appuyer **uniquement** sur ces articles (pas d’invention volontaire). |
| **Surinformation** | **Trop** de messages sur le **même sujet** (groupe WhatsApp, rafales de copies) | **Limiter le bruit produit par le bot** : filtre **Topic Gate** en groupe (ne répond qu’aux messages liés à l’actualité RDC) ; objectif de **ne pas répéter** la même analyse dix fois (déduplication en cours). Le bot ne peut pas effacer les messages des autres utilisateurs. |

**En clair :**

- Contre la **désinformation** → « Cette affirmation est-elle soutenue par la presse indexée ? »
- Contre la **surinformation** → « Le bot ne doit pas devenir une source supplémentaire de spam de vérifications identiques. »

---

## 3. De quoi il s’agit techniquement

**RDC News Intelligence** collecte des articles de médias (crawler), les stocke en base (**~13 000** articles aujourd’hui), puis, lorsqu’un utilisateur envoie une question (texte ou image OCR), le système :

1. trouve les **3 articles les plus proches** du sujet ;
2. fait rédiger une réponse par **Mistral** (modèle local via Ollama) **à partir de ces articles seulement**.

---

## 4. Seuil de similarité — comment c’est calculé

Le seuil **n’est pas calculé automatiquement** à chaque question. C’est un **paramètre fixe** dans la configuration :

| Canal | Paramètre | Valeur par défaut |
|-------|-----------|-------------------|
| WhatsApp, Telegram, Web | `RAG_MIN_SIMILARITY_MSG` | **0,40** (40 %) |
| Autres | `RAG_MIN_SIMILARITY` | **0,36** (36 %) |

**Règle :** un article n’est envoyé à Mistral que si son **score de similarité ≥ seuil**. Sinon il est écarté. S’il ne reste **aucun** article → réponse **NON VÉRIFIABLE**.

### Formule du score

1. La question et chaque article sont transformés en **vecteurs de 384 nombres** (modèle multilingue MiniLM), **normalisés** (longueur = 1).

2. **Similarité cosinus** entre la question **q** et l’article **d** :

   **sim(q, d) = q · d**  
   (produit scalaire des 384 composantes ; plus c’est proche de 1, plus les textes sont proches en sens.)

3. ChromaDB renvoie une **distance** cosinus `dist` (plus petite = plus proche). Le programme convertit :

   **similarity = 1 − dist**

   Pour des vecteurs normalisés, cela revient à la similarité cosinus ci-dessus.

4. **Filtrage :**

   **article retenu ⟺ similarity ≥ 0,40** (sur WhatsApp / web)

**Exemple :** similarité 0,52 → article gardé ; 0,35 → rejeté.

**Pourquoi 0,40 ?** Réglage empirique : assez strict pour éviter des sources hors-sujet, sans rejeter trop de sujets RDC couverts par la presse. Ce n’est pas une moyenne statistique sur tout le corpus.

---

## 5. Les trois langues — démarcation multilingue

Le projet vise le **français**, l’**anglais** et le **swahili** (contexte RDC et Grands Lacs). On distingue trois niveaux :

| Niveau | Signification | Français | Anglais | Swahili |
|--------|---------------|----------|---------|---------|
| **L1 — Interface** | L’utilisateur peut poser sa question dans la langue | Oui | Oui | Oui |
| **L2 — Preuves (corpus)** | Articles indexés dans cette langue | **Fort** (~94 % du corpus) | **Correct** (~650 articles) | **Limité** (~170 articles) |
| **L3 — Service « complet »** | Vérification fiable avec sources dans la même langue | **Oui** | **Partiel** | **Non encore** (en cours d’enrichissement) |

**En une phrase :** on peut **demander** en trois langues ; la **fiabilité des preuves** est aujourd’hui surtout en **français**.

| Langue | Part du corpus | Flux principaux |
|--------|----------------|-----------------|
| Français | ~94 % | Radio Okapi, 7sur7, mediacongo, RFI, etc. |
| Anglais | ~5 % | BBC, Guardian, VOA, DW (flux Afrique / monde) |
| Swahili | ~1,3 % | VOA Swahili, BBC Swahili, DW Kiswahili, RFI Swahili |

---

## 6. Ce qui fonctionne aujourd’hui (résultats)

| Élément | Résultat |
|--------|----------|
| **Corpus** | ~**13 000** articles ; **100 %** reliés au moteur de recherche |
| **WhatsApp** | Vérification en privé ; filtre en groupe pour l’actualité RDC |
| **Verdicts** | Format clair : vérification + explication + sources |
| **Tests FR** | Sujets couverts (ex. Ebola) → **VRAI** ou **FAUX** cohérent avec la presse |
| **Tests EN / SW** | Réponse possible ; souvent **IMPRÉCIS** si peu de sources dans la langue |

**Délai :** plusieurs **minutes** par réponse sur machine locale (génération Mistral), pas une réponse instantanée.

---

## 7. Limites à assumer

1. Sans article sur le sujet → **non vérifiable**, pas de réponse inventée.
2. Qualité liée aux **médias crawlés** (catalogue nettoyé : sources vides retirées).
3. **Swahili** : corpus encore petit — objectif plusieurs **centaines** d’articles avant promesse équivalente au français.
4. Le système **ne remplace pas** un journaliste ni une rédaction de fact-check.

---

## 8. Conclusion

**RDC News Intelligence** démontre qu’on peut, pour la RDC :

- lutter contre la **désinformation** par des réponses **sourcées** et catégorisées ;
- limiter la **surinformation** induite par le bot (filtres, pas de réponses hors-sujet en groupe) ;
- ouvrir la voie au **multilingue** (FR solide, EN en progrès, SW amorcé).

**Suite :** enrichir le corpus swahili, accélérer les réponses, tests avec utilisateurs réels.

---

*Synthèse — mai 2026. Projet RDC News Intelligence.*

# CHAPITRE I : INTELLIGENCE ARTIFICIELLE ET GESTION DE L'INFORMATION À L'ÈRE DU NUMÉRIQUE

## 1.1 Introduction générale du chapitre

La transformation numérique a profondément modifié la façon dont l'information est produite, circulée et consommée. Les réseaux sociaux et les messageries instantanées ont accéléré la diffusion des contenus en rendant la publication et le partage presque gratuits. Cette évolution a ouvert l'accès à la parole publique à un plus grand nombre de personnes, mais elle a aussi affaibli les mécanismes traditionnels de vérification et de hiérarchisation de l'information [1], [2].

Dans ce contexte, deux phénomènes se renforcent mutuellement. D'une part, la **désinformation**, c'est-à-dire la diffusion, volontaire ou non, de contenus faux ou trompeurs. D'autre part, l'**infobésité**, qui désigne la surcharge cognitive provoquée par un volume d'informations trop important par rapport à ce que l'on peut traiter [3], [4]. Les travaux récents sur les messageries montrent que ces deux dynamiques empruntent souvent les mêmes canaux — groupes WhatsApp, canaux Telegram — et qu'il est peu pertinent de les traiter séparément [32]. L'utilisateur est confronté à un flux continu de textes, d'images et de vidéos, souvent sortis de leur contexte, qui dépasse sa capacité de tri. Cette surcharge affaiblit l'esprit critique et favorise l'adhésion à des récits simplifiés, émotionnels ou sensationnalistes [5], [17].

Le cas des messageries chiffrées (WhatsApp, Telegram) est particulier. Contrairement aux réseaux sociaux ouverts, ces espaces sont en grande partie privés, morcelés en groupes, et difficilement observables par les organismes de vérification des faits [7], [8], [29]. La viralité y est plus difficile à suivre, alors même que la confiance envers l'expéditeur — un proche, un collègue, un groupe communautaire — renforce la crédibilité perçue du message [30], [31].

Ce chapitre pose le cadre conceptuel et scientifique de notre travail. Nous y abordons successivement :

1. les dynamiques informationnelles contemporaines et leurs effets sur la cognition ;
2. la littérature sur la désinformation dans les messageries ;
3. les approches techniques existantes (classification, fact-checking automatisé, grands modèles de langage, RAG, OCR) ;
4. la lacune que notre recherche cherche à combler : réduire la désinformation sans alourdir davantage la surcharge informationnelle.

Ce chapitre constitue la base théorique de la proposition système développée dans la suite du mémoire.

## 1.2 Crise informationnelle à l'ère des plateformes

### 1.2.1 De l'économie de l'attention à l'économie de la polarisation

Les travaux récents montrent que l'architecture des plateformes numériques est calée sur des indicateurs d'engagement — clics, partages, temps passé — plutôt que sur la véracité des contenus [2], [5]. Les messages polarisants, émotionnels ou alarmistes obtiennent en moyenne plus d'interactions. Il en résulte un biais structurel : ce qui est le plus visible n'est pas forcément ce qui est le plus fiable, mais souvent ce qui provoque le plus fortement la réaction.

Sur le plan sociotechnique, l'espace public se fragmente en micro-publics qui ne voient pas la même « réalité ». Lorsqu'une même rumeur circule dans des bulles distinctes, la corriger devient plus difficile : la rectification doit franchir des frontières communautaires, linguistiques et affectives [8], [32].

### 1.2.2 Post-vérité, confiance et vérification

La « post-vérité » ne signifie pas que les faits ont disparu, mais que leur poids social diminue face à l'identité de groupe et à l'affect [1], [17]. Dans les espaces dominés par la messagerie, la confiance relationnelle compte beaucoup : un message reçu d'un proche est souvent jugé crédible avant même d'être examiné.

Cela explique pourquoi une correction strictement factuelle peut échouer. Une réponse qui contredit frontalement les convictions d'un groupe peut être perçue comme hostile, même si elle est exacte. Les approches qui fonctionnent le mieux combinent donc la justesse du fond, un ton adapté, une mise en contexte et une forme de restitution compréhensible [5], [30].

### 1.2.3 Viralité cachée dans les canaux chiffrés

Le chiffrement de bout en bout protège la confidentialité, mais limite la modération centralisée [7]. Les plateformes disposent de peu de signaux pour repérer automatiquement les campagnes de désinformation. Les acteurs extérieurs — journalistes, chercheurs, institutions — ont eux aussi un accès restreint à ce qui circule à l'intérieur des groupes.

Paris et Pasquetto parlent de **viralité cachée** (*hidden virality*) : la désinformation se propage d'abord dans des réseaux de confiance avant d'être visible à plus grande échelle [29]. L'alerte arrive souvent tard, parfois après une large diffusion dans des réseaux locaux. Dans des contextes sanitaires, sécuritaires ou électoraux — fréquents en RDC — ce délai peut avoir des conséquences sérieuses.

Des outils externes de surveillance (par exemple WhatsApp Monitor) tentent de capturer et de trier les messages publics selon leur popularité, mais ils ne couvrent pas l'ensemble des conversations privées et de groupe [7]. Notre travail ne vise pas un monitorage global de la plateforme : il intervient au moment où l'utilisateur soumet lui-même un message à vérification.

### 1.2.4 Sociétés « messagérisées » et méso-communication

L'adoption massive de WhatsApp et de Telegram a fait émerger des sociétés dites **messagérisées**, où la méso-communication — groupes de taille intermédiaire, canaux communautaires — devient un lieu central de circulation de l'actualité [31], [32]. Contrairement aux médias traditionnels, il n'existe plus une seule « porte » éditoriale : chaque membre peut relayer, reformuler ou commenter un contenu.

Cette organisation présente trois caractéristiques importantes pour notre problème :

- **la vitesse** : un message peut traverser plusieurs groupes en quelques minutes ;
- **le volume** : les relais successifs multiplient les variantes d'un même récit ;
- **la confiance locale** : la crédibilité est souvent jugée à partir de la proximité sociale plutôt que de la source institutionnelle.

C'est pourquoi une architecture de vérification doit être à la fois rapide, économe en messages envoyés et fondée sur des sources locales — des exigences que nous reprenons dans la conception du système.

## 1.3 Infobésité et fatigue cognitive : cadre théorique

### 1.3.1 Infobésité : définition et mécanismes

L'infobésité désigne un déséquilibre entre la quantité d'informations reçues et la capacité de l'individu à les traiter [3], [4]. Ce déséquilibre produit au moins quatre effets :

- une surcharge attentionnelle (difficulté à retenir l'essentiel) ;
- une fatigue décisionnelle (jugements de moindre qualité) ;
- un recours à des raccourcis mentaux (émotion, familiarité, répétition) ;
- un évitement de l'information (désengagement ou résignation).

Ces effets s'accumulent. Plus l'utilisateur est exposé à des messages redondants ou contradictoires, plus il est vulnérable aux simplifications trompeuses.

### 1.3.2 Familiarité, répétition et illusion de vérité

En psychologie cognitive, on sait que la répétition d'une affirmation augmente sa plausibilité perçue, même si elle est fausse [5]. Sur les messageries, la répétition est courante : le même message relayé par plusieurs personnes, des captures d'écran qui reviennent, des reformulations partielles.

Une correction ponctuelle ne suffit donc pas. Il faut aussi tenir compte de la dynamique de répétition : repérer les variantes d'une même rumeur et éviter de répondre à chaque fois par un long texte nouveau.

### 1.3.3 Fatigue des médias sociaux et implications

La fatigue des médias sociaux décrit l'épuisement cognitif et émotionnel lié à une exposition trop forte aux flux numériques [4]. Elle se traduit par moins d'engagement civique et moins de vérification active de la part des utilisateurs. Dans ce cadre, un bot de fact-checking mal conçu peut aggraver le problème en ajoutant encore du bruit dans la conversation [30].

L'enjeu n'est donc pas seulement de « corriger le faux », mais de le faire de manière supportable pour l'attention de chacun. C'est précisément ce que la littérature sur les *fact-bots* souligne souvent de façon insuffisante : on mesure l'efficacité factuelle, mais rarement le coût informationnel supplémentaire introduit dans le fil de discussion [12], [30].

### 1.3.4 Convergence entre infobésité et désinformation

Infobésité et fausses informations ne sont pas deux problèmes indépendants. Elles partagent les mêmes canaux, la même logique de partage rapide et la même sensibilité aux événements locaux [32]. Une réponse corrective longue, répétée ou hors sujet peut ainsi aggraver la surcharge tout en visant à corriger une rumeur.

Notre recherche part de ce constat : toute intervention automatique doit intégrer un contrôle de la **redondance conversationnelle** et de la **pertinence thématique**, et non seulement un jugement sur la véracité.

## 1.4 Désinformation et fact-checking automatisé : état de l'art

### 1.4.1 Détection automatique de faussetés

Les approches supervisées s'appuient sur des caractéristiques lexicales, stylistiques, temporelles ou contextuelles, avec des modèles allant des classifieurs classiques aux réseaux de neurones [9], [10], [34]. Ces méthodes aident à prioriser le tri des contenus, mais elles ont des limites connues :

- sensibilité au domaine (changement de sujet ou de langue) ;
- besoin de jeux de données annotés, coûteux à produire ;
- difficulté à expliquer clairement la décision à l'utilisateur final.

Elles restent utiles en amont, pour orienter le travail des équipes humaines, mais elles ne suffisent pas pour une interaction conversationnelle en temps réel. Notre système ne repose pas sur un classifieur binaire « vrai / faux » : il s'appuie sur la récupération de preuves documentaires et sur une génération conditionnée (RAG).

### 1.4.2 Fact-checking conversationnel et fact-bots

Les *fact-bots* cherchent à répondre en langage naturel directement dans les canaux de discussion [11], [12], [30]. Leur force est l'immédiateté : ils interviennent au moment où la rumeur circule. Leur faiblesse tient souvent à la qualité des sources, à la redondance des messages et à une réception partagée — utiles pour certains, intrusifs pour d'autres [30].

Beaucoup de prototypes reposent soit sur des FAQ fixes (solides mais peu adaptatives), soit sur des grands modèles de langage sans ancrage documentaire suffisant (fluides mais sujets aux hallucinations). Un compromis plus robuste exige une base de connaissances locale, tenue à jour et citée — principe au cœur de notre implémentation.

### 1.4.3 Modulation du ton et des comportements

La littérature rappelle qu'une correction efficace ne dépend pas que de la véracité, mais aussi de la forme du message [5], [17]. Des réponses neutres, explicatives et peu agressives ont plus de chances d'être acceptées dans des groupes hétérogènes.

Des travaux récents explorent la génération de réponses à faible toxicité via des grands modèles de langage (cadre TRHF) dans des contextes de trolling [35]. Ces approches éclairent les dimensions interactionnelles, mais **elles ne constituent pas le cœur de notre système**, qui privilégie l'ancrage factuel par RAG et des réponses courtes plutôt que la gestion prolongée de conflits interpersonnels.

### 1.4.4 Surveillance, priorisation et contenus visuels

Plusieurs contributions ciblent spécifiquement WhatsApp :

- la **surveillance et les contre-mesures** à partir de groupes publics [7] ;
- la **priorisation par score de probabilité de fausseté** pour que les vérificateurs humains traitent d'abord les contenus les plus risqués [33] ;
- la **détection de rumeurs diffusées par images** (captures, montages, texte incrusté) [33].

Ces travaux montrent qu'il est techniquement possible de traiter des flux issus de messageries, mais ils visent surtout l'aide aux agences de vérification ou un tri externe. Notre contribution se distingue en combinant une vérification conversationnelle, un corpus local alimenté en continu par un crawler, et un **signalement de similarité** pour éviter de saturer le fil de discussion.

## 1.5 LLM et RAG pour la vérification d'informations

### 1.5.1 Limites des LLM « fermés au monde »

Un grand modèle de langage utilisé seul, sans récupération de documents, peut produire des réponses plausibles mais inexactes, surtout pour des événements locaux, récents ou peu couverts [13]. Dans un système de fact-checking, ce risque est critique : la confiance de l'utilisateur repose sur la traçabilité des réponses.

### 1.5.2 Principe du Retrieval-Augmented Generation

Le paradigme RAG (*Retrieval-Augmented Generation*) combine deux étapes [13] :

1. la récupération de documents pertinents dans une base externe ;
2. la génération d'une réponse conditionnée par ces documents.

L'intérêt principal est l'ancrage dans des sources vérifiables : la réponse peut citer explicitement les documents utilisés. Les travaux sur la recherche dense (DPR) ont confirmé l'intérêt de cette approche pour la question-réponse [14].

Dans notre cadre, le RAG sert à produire des **synthèses concises avec références**, tout en indiquant si une information a déjà été traitée dans le même groupe ou ailleurs. Cette double fonction — véracité et signalisation de nouveauté — nous distingue d'un chatbot génératif classique.

### 1.5.3 Indexation vectorielle et pertinence sémantique

Les embeddings transforment textes et requêtes en vecteurs comparables dans un espace sémantique. Une recherche par similarité (Top-k) permet de retrouver des contenus proches même sans mots identiques [16]. C'est essentiel dans un contexte multilingue (français, anglais, swahili), où un même fait peut être formulé de manière différente [28].

En revanche, la recherche renvoie souvent des résultats redondants. Sans déduplication ni regroupement, la couche de génération peut reproduire cette redondance. D'où l'intérêt d'un **regroupement sémantique** des messages et des articles proches avant de générer une réponse.

### 1.5.4 Contenus multimodaux et OCR

Une part croissante de la désinformation sur messagerie passe par des **images** — captures d'articles, affiches, montages avec texte incrusté — plutôt que par du texte seul [33]. Les chaînes de vérification doivent donc inclure une étape d'extraction de texte.

L'OCR (*Optical Character Recognition*) convertit le contenu visuel en chaîne de caractères exploitable par le moteur sémantique. Dans notre projet, cette étape est réalisée localement (Tesseract) avant l'injection dans le pipeline RAG, pour WhatsApp comme pour Telegram. Elle ne remplace pas la vérification : elle permet de traiter des captures sans demander à l'utilisateur de retaper le texte à la main.

### 1.5.5 Identification de récits et regroupement conversationnel

En recherche d'information, on regroupe souvent des articles qui traitent du même événement — on parle parfois d'**identification de récits** (*Story Identification*) — afin de réduire le bruit et de comparer les angles de couverture [10]. Sur messagerie, le problème est similaire mais à une échelle plus fine : il s'agit de regrouper des **messages** proches dans un groupe pour ne pas relancer inutilement un traitement complet.

Le principe retenu dans notre système est le suivant :

1. calcul d'un embedding pour chaque message entrant ;
2. comparaison avec une mémoire conversationnelle récente ;
3. si le score de similarité dépasse un seuil, regroupement en cluster ;
4. si une réponse existe déjà pour ce cluster, réutilisation ou message court du type « déjà vérifié » ; sinon, exécution du pipeline RAG.

Ce mécanisme rapproche la vérification factuelle de la gestion de l'infobésité : une même rumeur ne doit pas produire dix longues réponses identiques dans un groupe actif.

Des approches de **résumé segmenté** sur de longs documents (transformers de type BART) visent aussi à alléger la charge cognitive, mais en compressant des textes statiques plutôt qu'en gérant un flux conversationnel [15], [36]. Notre système privilégie plutôt l'association recherche + génération courte + anti-répétition, mieux adaptée aux échanges sur messagerie.

## 1.6 Messageries instantanées : contraintes de conception

### 1.6.1 Contraintes techniques

Les bots sur messagerie doivent respecter des contraintes strictes :

- une latence faible pour l'utilisateur ;
- des limites de taille des messages ;
- une fiabilité malgré des réseaux instables ;
- une gestion de file d'attente pour absorber les pics (webhooks Whapi/Telegram, files Redis).

L'architecture doit donc combiner asynchronisme, journalisation, reprise après erreur et gestion de charge — ce que reflète la séparation entre un orchestrateur (réception, file) et un moteur de traitement (analyse, génération).

### 1.6.2 Contraintes cognitives

Une réponse complète mais trop longue peut être contre-productive. Sur mobile, les usages favorisent des formats courts, structurés et actionnables. Les bonnes pratiques convergent vers :

- un verdict explicite ;
- une explication concise ;
- des sources pertinentes localement ;
- une longueur maîtrisée.

### 1.6.3 Contraintes contextuelles locales (RDC)

En République démocratique du Congo, la circulation de l'information touche des domaines sensibles : santé publique, sécurité, élections, rumeurs politiques. La pertinence des sources locales est déterminante. Un système efficace doit s'appuyer sur des contenus journalistiques proches du terrain et sur des médias reconnus par les publics visés.

Notre corpus — plus de 13 000 articles, majoritairement en français, avec une présence d'anglais et de swahili — illustre le besoin d'une **base régionale** et multilingue [28], [27]. Les solutions conçues pour des langues très dotées en ressources NLP se transfèrent mal sans adaptation des sources et des modèles d'embedding.

## 1.7 Analyse critique des approches existantes

### 1.7.1 Forces observées

La littérature et les systèmes existants apportent des acquis solides :

- une détection plus rapide des signaux viraux ou suspects [7], [33] ;
- l'automatisation de tâches répétitives de vérification [11], [12] ;
- des réponses conversationnelles contextualisées [30] ;
- une réduction du délai entre l'apparition d'une rumeur et sa rectification.

### 1.7.2 Limites récurrentes

Malgré ces avancées, plusieurs limites persistent :

1. une séparation artificielle entre « lutte contre le faux » et « gestion de la surcharge » ;
2. une faible prise en compte de la redondance entre messages dans un même groupe ;
3. des évaluations centrées sur la précision et le rappel, rarement sur la charge cognitive ;
4. une adaptation insuffisante aux contextes multilingues africains [28] ;
5. des difficultés de déploiement en environnement de messagerie privée ;
6. un traitement incomplet des messages visuels sans chaîne OCR intégrée [33].

### 1.7.3 Lacune principale pour cette recherche

La lacune centrale est la suivante : les systèmes actuels optimisent la correction factuelle, mais **sous-estiment le risque paradoxal** selon lequel la correction elle-même contribue à l'infobésité lorsque les réponses ne sont ni gérées intelligemment ni dédupliquées [30], [32].

Notre problématique se situe exactement à ce point de tension.

### 1.7.4 Tableau comparatif des stratégies de mitigation

Le tableau I.1 résume les principales familles de solutions relevées dans la littérature et le positionnement de notre travail.

**Tableau I.1 — Stratégies de mitigation et positionnement du projet**

| Stratégie (littérature) | Cible principale | Mécanisme clé | Limite fréquente | Notre projet |
|-------------------------|------------------|---------------|------------------|--------------|
| Classement / score de fausseté [9], [33] | Fausses informations | Prioriser le travail humain | Peu conversationnel ; hors groupe privé | Non retenu comme cœur |
| Fact-bots [12], [30] | Fausses informations | Réponse automatique en groupe | Risque de surcharge | Oui, avec RAG et sources |
| Surveillance externe [7] | Fausses informations | Observation de groupes publics | Accès limité aux chats privés | Non (webhook utilisateur) |
| Résumé segmenté [36] | Infobésité | Compression de longs textes | Hors flux messagerie | Partiel (réponses courtes) |
| TRHF / harmonisation [35] | Trolling | Réponses peu agressives | Sans ancrage documentaire | Non implémenté |
| RAG + mémoire sémantique | Fausses informations + infobésité | Sources + anti-répétition | Complexité de déploiement | **Contribution centrale** |

## 1.8 Positionnement de la recherche et contribution

### 1.8.1 Hypothèse de travail

Nous posons l'hypothèse qu'un système de vérification conversationnelle est nettement plus utile s'il intègre nativement :

- la détection de redondance sémantique (regroupement de messages proches) ;
- la priorisation de réponses pivots non répétitives ;
- une génération RAG ancrée sur des sources locales citées ;
- l'extraction OCR des contenus image ;
- un filtrage thématique pour éviter les réponses hors sujet ;
- des sorties courtes, structurées et peu conflictuelles.

### 1.8.2 Proposition conceptuelle

La proposition s'articule autour des éléments suivants :

- un **pipeline de collecte locale** (crawler, base PostgreSQL, index vectoriel Chroma) ;
- un **moteur conversationnel RAG** (recherche dense, génération via Ollama/Mistral) ;
- un **module anti-infobésité** (mémoire sémantique, seuil de similarité, réutilisation de verdict) ;
- un **traitement multimodal** (OCR Tesseract pour les images WhatsApp/Telegram) ;
- des **canaux messagerie** (Whapi, Telegram) comme interface d'usage réel.

L'objectif est pragmatique : améliorer la qualité de l'information disponible sans saturer l'utilisateur.

### 1.8.3 Originalité pratique

L'originalité ne réside pas dans un algorithme isolé, mais dans l'**intégration opérationnelle** de briques connues, guidée par un critère peu central dans la littérature : la **sobriété informationnelle** de la réponse corrective. Le déploiement sur un corpus congolais (plus de 13 000 articles) et l'usage en conditions réelles sur messagerie renforcent la pertinence du dispositif par rapport à des prototypes purement laboratoire.

### 1.8.4 Apports attendus du dispositif

Le mémoire développe notamment les apports suivants :

1. repérage et mise à jour rapide de sources fiables via un crawler ciblé ;
2. lecture et traitement de messages utilisateur via webhooks WhatsApp/Telegram ;
3. filtrage thématique et contrôle de pertinence avant les traitements coûteux ;
4. synthèses RAG avec références et indication lorsqu'une information a déjà été traitée ;
5. possibilité d'élargir les sources et les langues (français dominant, anglais et swahili en progression) ;
6. ouverture vers des API externes de fact-checking (évolution prévue).

Ce chapitre a posé le **pourquoi** scientifique de ces choix ; les chapitres II à IV en détaillent le **comment** technique.

## 1.9 Indicateurs d'évaluation retenus

Au regard des lacunes identifiées, les indicateurs pertinents dépassent la seule exactitude :

1. **qualité factuelle** : présence de sources pertinentes, cohérence du verdict ;
2. **robustesse du système** : stabilité des webhooks, tolérance aux pannes, reprise ;
3. **couverture documentaire** : part des articles indexés et mobilisables (corpus RDC) ;
4. **efficacité conversationnelle** : réduction des répétitions pour des rumeurs proches ;
5. **sobriété cognitive** : capacité à informer sans surcharger ;
6. **couverture multimodale** : taux de succès OCR et qualité des réponses à partir d'images.

Cette grille guide les chapitres méthodologiques et expérimentaux ultérieurs.

## 1.10 Conclusion partielle du chapitre

Ce chapitre a posé le socle théorique de la recherche. La crise informationnelle actuelle ne se réduit pas à une question de « vrai ou faux ». Dans les messageries, la confiance relationnelle, la viralité cachée [29], la méso-communication [31] et la surcharge cognitive [3], [4] imposent de repenser les outils de fact-checking.

L'état de l'art confirme l'intérêt des approches automatisées (détection, fact-bots, surveillance), mais montre aussi leurs limites lorsqu'elles négligent l'infobésité ou les spécificités locales. Le paradigme RAG permet d'ancrer les réponses sur des sources vérifiables [13], [14] ; l'OCR élargit le champ aux rumeurs visuelles [33] ; la similarité sémantique et la mémoire conversationnelle évitent que la correction devienne elle-même un facteur de saturation.

Notre contribution vise un dispositif conversationnel de vérification à la fois fiable sur le plan factuel, utilisable sur WhatsApp et Telegram, et soutenable pour l'attention de l'utilisateur en RDC. Le chapitre suivant présente l'architecture méthodologique et technique retenue pour le mettre en œuvre.

---

## Références

Les références bibliographiques de ce chapitre sont centralisées dans `thesis/References.md`, avec une numérotation IEEE unique et continue pour l'ensemble du mémoire (numéros [1] à [36]).

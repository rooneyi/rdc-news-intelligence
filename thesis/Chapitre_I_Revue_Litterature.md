# CHAPITRE I: INTELLIGENCE ARTIFICIELLE ET GESTION DE L'INFORMATION A L'ERE DU NUMERIQUE

## 1.1 Introduction generale du chapitre

La transformation numerique a provoque une mutation profonde de la production, de la circulation et de la consommation de l'information. Les plateformes sociales et les messageries instantanees ont accelere la diffusion des contenus en reduisant presque a zero le cout de publication et de partage. Cette evolution a democratise l'acces a la parole publique, mais elle a aussi fragilise les mecanismes classiques de verification editoriale et de hierarchisation de l'information [1], [2].

Dans ce contexte, deux phenomenes se renforcent mutuellement: (i) la desinformation, definie comme la diffusion intentionnelle ou non de contenus faux ou trompeurs, et (ii) l'infobesite, c'est-a-dire la surcharge cognitive induite par un volume informationnel excessif [3], [4]. L'utilisateur est expose a un flux continu de textes, images et videos, souvent hors contexte, qui excede sa capacite de tri critique. Cette surcharge affaiblit la vigilance epistemique et facilite l'adhesion a des recits simplifies, emotifs ou sensationnalistes [5], [6].

Le cas des messageries chiffrees (WhatsApp, Telegram) est particulier. A la difference des reseaux sociaux ouverts, ces environnements sont semi-prives, fragmentes en groupes, et faiblement observables par les institutions de fact-checking [7], [8]. La viralite y est plus difficile a monitorer, alors meme que la confiance interpersonnelle (famille, collegues, groupes communautaires) augmente la credibilite percue des messages.

L'objectif de ce chapitre est de poser le cadre conceptuel et scientifique de notre travail. Plus precisement, nous allons:

1. caracteriser les dynamiques informationnelles contemporaines et leurs effets cognitifs;
2. analyser la litterature sur la desinformation en contextes messagerie;
3. examiner les approches techniques existantes (classification, fact-checking automatise, LLM, RAG);
4. identifier la lacune centrale que notre recherche vise a combler: reduire la desinformation sans augmenter l'infobesite.

Le chapitre constitue ainsi la base theorique de la proposition systeme qui sera detaillee dans les chapitres suivants.

## 1.2 Crise informationnelle a l'ere des plateformes

### 1.2.1 De l'economie de l'attention a l'economie de la polarisation

Les travaux recents montrent que l'architecture des plateformes numeriques est alignee sur des metriques d'engagement (clic, partage, temps passe), pas sur des metriques de veracite [2], [5]. Les contenus polarises, emotifs ou alarmistes obtiennent statistiquement plus d'interactions. Cette logique cree un biais de selection structurel: les informations les plus visibles ne sont pas necessairement les plus fiables, mais souvent les plus reactogenes.

Du point de vue sociotechnique, cette dynamique transforme l'espace public en une juxtaposition de micro-publics qui consomment des fragments de realite differents. La circulation des memes rumeurs dans des bulles distinctes complique ensuite la correction, car la rectification doit franchir des frontieres communautaires, linguistiques et affectives.

### 1.2.2 Post-verite, confiance et verification

La post-verite ne signifie pas disparition des faits, mais diminution du poids social de la verification factuelle face a l'identite de groupe et a l'affect [1], [6]. Dans les espaces "messagerises", la confiance relationnelle joue un role central: un message recu d'un proche est souvent traite comme credible avant meme son examen critique.

Ce mecanisme explique pourquoi des corrections strictement factuelles peuvent echouer. Une reponse qui contredit frontalement la croyance d'un groupe peut etre percue comme hostile, meme si elle est correcte. Les approches performantes doivent donc articuler exactitude, tonalite, contextualisation et format de restitution.

### 1.2.3 Viralite cachee dans les canaux chiffrees

Le chiffrement de bout en bout renforce la confidentialite, mais limite la moderation centralisee [7]. Les plateformes disposent de peu de signaux semantiques pour identifier automatiquement les campagnes de desinformation. Les acteurs externes (journalistes, chercheurs, institutions) ont eux aussi un acces limite a la circulation interne des contenus.

La consequence est une "viralite cachee": le signal d'alerte apparait tardivement, souvent apres large diffusion dans des reseaux locaux. Dans des contextes sanitaires, securitaires ou electoraux, ce delai peut avoir un cout social eleve.

## 1.3 Infobesite et fatigue cognitive: cadre theorique

### 1.3.1 Infobesite: definition et mecanismes

L'infobesite renvoie a un desequilibre entre volume informationnel entrant et capacite de traitement disponible [3], [4]. Ce desequilibre produit au moins quatre effets:

- surcharge attentionnelle (difficulte a filtrer l'essentiel);
- fatigue decisionnelle (baisse de qualite des jugements);
- recours aux heuristiques rapides (emotion, familiarite, repetition);
- evitement informationnel (desengagement ou resignation).

Ces effets sont cumulatifs. Plus l'utilisateur est expose a des messages redondants et contradictoires, plus il est vulnerable a la simplification trompeuse.

### 1.3.2 Familiarite, repetition et illusion de verite

Plusieurs travaux en psychologie cognitive montrent que la repetition d'une affirmation augmente sa plausibilite percue, meme lorsque son contenu est faux [6]. Dans les messageries, la repetition est frequente: meme message relayé par plusieurs membres, captures d'ecran recirculant, reformulations partielles.

La correction ponctuelle ne suffit donc pas. Une strategie robuste doit traiter la dynamique de repetition elle-meme: detecter les variants semantiques d'une meme rumeur et eviter de repondre chaque fois par un long bloc textuel nouveau.

### 1.3.3 Fatigue des medias sociaux et implications

La fatigue des medias sociaux decrit l'epuisement cognitif et emotionnel provoque par la sur-exposition aux flux numeriques [4]. Elle se traduit par une diminution de l'engagement civique et de la capacite de verification active. Dans ce cadre, un bot de fact-checking mal concu peut aggraver le probleme en ajoutant du bruit informationnel.

L'enjeu n'est donc pas seulement "corriger le faux", mais "corriger de maniere cognitive-ment soutenable".

## 1.4 Desinformation et fact-checking automatise: etat de l'art

### 1.4.1 Detection automatique de faussetes

Les approches de detection supervisée utilisent des caracteristiques lexicales, stylistiques, temporelles et contextuelles, avec des modeles allant de XGBoost aux architectures neurales [9], [10]. Ces methodes sont utiles pour prioriser le tri des contenus, mais elles ont des limites connues:

- sensibilite au domaine (changement de sujet/langue degrade les performances);
- dependance a des jeux de donnees annotes couteux;
- difficulte a expliquer clairement la decision a l'utilisateur final.

Elles sont donc pertinentes comme couche de pre-filtrage, mais insuffisantes seules pour l'interaction conversationnelle.

### 1.4.2 Fact-checking conversationnel

Les "fact-bots" visent a fournir des reponses en langage naturel dans des canaux de discussion [11], [12]. Leur force est l'immediatete: ils interviennent au moment de la circulation de la rumeur. Leur faiblesse tient souvent a la qualite des sources et a la redondance des messages.

Beaucoup de prototypes reposent soit sur des FAQ statiques (robustes mais peu adaptatifs), soit sur des LLM generatifs sans ancrage documentaire suffisant (fluides mais sujet a hallucination). Le compromis robuste exige une base de connaissances locale, actualisee et citee.

### 1.4.3 Modulation du ton et des comportements

La litterature souligne qu'une correction efficace ne depend pas uniquement de la veracite, mais aussi de la forme discursive [5], [6]. Les reponses neutres, explicatives, et non confrontantes sont plus susceptibles d'etre acceptees dans des groupes heterogenes.

Dans ce sens, des approches proches des cadres de "response harmonization" (dont les travaux inspires du TRHF) cherchent a reduire la toxicite interactionnelle sans sacrifier la precision factuelle.

## 1.5 LLM et RAG pour la verification d'informations

### 1.5.1 Limites des LLM "fermés au monde"

Un LLM utilise seul (sans retrieval) peut produire des sorties plausibles mais inexactes, en particulier sur des evenements locaux, recents, ou peu couverts [13]. Ce risque est critique dans un systeme de fact-checking, ou la confiance utilisateur depend de la tracabilite des reponses.

### 1.5.2 Principe du Retrieval-Augmented Generation

Le paradigme RAG combine deux modules [13]:

1. recuperation de documents pertinents depuis une base externe;
2. generation conditionnee sur ces documents.

L'avantage principal est l'ancrage empirique: la reponse peut citer explicitement les sources ayant servi a l'argumentation. Des travaux complementaires sur le dense retrieval (DPR) ont demontre la pertinence de cette approche pour les taches de question-reponse [14].

### 1.5.3 Indexation vectorielle et pertinence semantique

Les embeddings transforment textes et requetes en vecteurs comparables dans un espace semantique. La recherche Top-k par similarite permet de retrouver des contenus proches meme en l'absence d'overlap lexical exact. Cette capacite est essentielle dans un contexte multilingue (francais, anglais, swahili), ou les memes faits peuvent etre formules differemment.

Cependant, le retrieval produit souvent des resultats redondants. Sans mecanisme de deduplication ou de synthese, la couche generative peut reproduire cette redondance.

## 1.6 Messageries instantanees: contraintes de conception

### 1.6.1 Contraintes techniques

Les bots sur messagerie doivent respecter des contraintes strictes:

- latence utilisateur faible;
- limites de taille des messages;
- fiabilite en environnement reseau variable;
- gestion de file pour absorber les pics.

L'architecture doit donc combiner asynchronisme, journalisation robuste, reprise sur erreur, et gestion de charge.

### 1.6.2 Contraintes cognitives

Une reponse complete mais trop longue peut etre contre-productive. Les usages mobiles favorisent des formats courts, structures et actionnables. Les meilleures pratiques convergent vers:

- un verdict explicite;
- une explication concise;
- des sources localement pertinentes;
- une longueur controlee.

### 1.6.3 Contraintes contextuelles locales

Dans le cas congolais, la circulation d'informations touche des domaines sensibles (sante publique, securite, elections, rumeurs politiques). La pertinence locale des sources est determinante. Un systeme performant doit privilegier des contenus journalistiques proches du terrain et des medias reconnus par les publics cibles.

## 1.7 Analyse critique des approches existantes

### 1.7.1 Forces observees

La litterature et les systemes existants apportent des acquis solides:

- capacite de detection rapide des signaux viraux;
- automatisation des taches repetitives de verification;
- possibilite de reponse conversationnelle contextualisee;
- reduction du delai entre apparition de la rumeur et rectification.

### 1.7.2 Limites recurrentes

Malgre ces avancees, plusieurs limites persistent:

1. separation artificielle entre "lutte contre le faux" et "gestion de la surcharge";
2. faible prise en compte de la redondance inter-messages;
3. evaluation centree sur precision/recall, rarement sur charge cognitive utilisateur;
4. faible adaptation aux contextes multilingues africains;
5. difficultes de deploiement operationnel en environnement messagerie privee.

### 1.7.3 Lacune principale pour cette recherche

La lacune centrale est la suivante: les systemes actuels optimisent la correction factuelle, mais sous-estiment le cout cognitif de la correction elle-meme. En d'autres termes, la "bonne reponse" peut devenir "mauvaise intervention" si elle augmente le bruit conversationnel.

Notre problematique se situe exactement a ce point de tension.

## 1.8 Positionnement de la recherche et contribution

### 1.8.1 Hypothese de travail

Nous posons l'hypothese qu'un systeme de verification conversationnelle est significativement plus utile s'il integre nativement:

- la detection de redondance semantique (clustering de messages proches);
- la priorisation de reponses pivots non repetitives;
- la generation RAG ancree sur des sources locales citees;
- des sorties courtes, structurees et non conflictuelles.

### 1.8.2 Proposition conceptuelle

La proposition s'articule autour d'un couplage:

- **Pipeline de collecte locale** (crawler + base SQL + index vectoriel);
- **Moteur conversationnel RAG** (retrieval + synthese);
- **Module anti-infobesite** (memoire semantique et anti-repetition);
- **Canaux messagerie** (WhatsApp/Whapi, Telegram) comme interface d'usage reel.

Ce couplage vise une finalite pragmatique: augmenter la qualite informative sans saturer l'utilisateur.

### 1.8.3 Originalite pratique

L'originalite ne reside pas dans un algorithme unique, mais dans l'integration operationnelle de briques connues, pilotee par un critere rarement central dans la litterature: la sobriete informationnelle de la reponse corrective.

## 1.9 Indicateurs d'evaluation retenus

Au regard des lacunes identifiees, les indicateurs d'evaluation pertinents depassent la seule exactitude:

1. **Qualite factuelle**: presence de sources pertinentes, coherence du verdict.
2. **Robustesse systeme**: stabilite des webhooks, tolerance aux pannes, reprise.
3. **Couverture documentaire**: taux d'articles indexes et mobilisables.
4. **Efficacite conversationnelle**: reduction des repetitions pour des rumeurs proches.
5. **Sobriete cognitive**: capacite a informer sans surcharger.

Cette grille guide les chapitres methodologiques et experimentaux ulterieurs.

## 1.10 Conclusion partielle du chapitre

Ce chapitre a etabli le socle theorique de la recherche. Nous avons montre que la crise informationnelle contemporaine ne peut etre reduite a une simple question de "vrai/faux". Dans les environnements messagerie, la dynamique de confiance, la viralite cachee et la surcharge cognitive obligent a repenser les systemes de fact-checking.

L'etat de l'art confirme l'interet des approches automatisees, mais souligne aussi leurs limites lorsqu'elles ignorent l'infobesite. Le paradigme RAG apporte une base solide pour ancrer les reponses sur des sources verifiables, tandis que les mecanismes anti-redondance permettent d'eviter que la correction elle-meme devienne un facteur de saturation.

La contribution de cette recherche se positionne a l'intersection de ces enjeux: concevoir un dispositif conversationnel de verification qui soit a la fois factuellement fiable, operationnel en contexte messagerie, et cognitivement soutenable pour l'utilisateur. Le chapitre suivant presentera l'architecture methodologique et technique retenue pour operationaliser ce cadre.

---

## References (Norme IEEE)

[1] C. R. Sunstein, *#Republic: Divided Democracy in the Age of Social Media*. Princeton, NJ, USA: Princeton Univ. Press, 2017.

[2] S. Vosoughi, D. Roy, and S. Aral, "The spread of true and false news online," *Science*, vol. 359, no. 6380, pp. 1146-1151, Mar. 2018.

[3] D. Bawden and L. Robinson, "The dark side of information: Overload, anxiety and other paradoxes and pathologies," *Journal of Information Science*, vol. 35, no. 2, pp. 180-191, 2009.

[4] M. W. Bright, J. M. Kleiser, and S. Grau, "Too much Facebook? An exploratory examination of social media fatigue," *Computers in Human Behavior Reports*, vol. 1, 2020.

[5] S. Lewandowsky, U. K. H. Ecker, C. M. Seifert, N. Schwarz, and J. Cook, "Misinformation and its correction: Continued influence and successful debiasing," *Psychological Science in the Public Interest*, vol. 13, no. 3, pp. 106-131, 2012.

[6] G. Pennycook and D. G. Rand, "Fighting misinformation on social media using crowdsourced judgments of news source quality," *Proc. Natl. Acad. Sci. U.S.A.*, vol. 116, no. 7, pp. 2521-2526, 2019.

[7] E. C. K. Resende, P. M. A. Cunha, M. V. M. Goncalves, J. P. de Melo, and F. Benevenuto, "(Mis)Information dissemination in WhatsApp: Gathering, analyzing and countermeasures," in *The World Wide Web Conference (WWW Companion)*, 2019.

[8] C. Wardle and H. Derakhshan, "Information disorder: Toward an interdisciplinary framework for research and policy making," Council of Europe, Strasbourg, France, Rep. DGI(2017)09, 2017.

[9] H. Ahmed, I. Traore, and S. Saad, "Detection of online fake news using n-gram analysis and machine learning techniques," in *Proc. 2017 Int. Conf. Intelligent, Secure, and Dependable Systems in Distributed and Cloud Environments (ISDDC)*, 2017, pp. 127-138.

[10] K. Shu, A. Sliva, S. Wang, J. Tang, and H. Liu, "Fake news detection on social media: A data mining perspective," *SIGKDD Explorations*, vol. 19, no. 1, pp. 22-36, 2017.

[11] S. Nakov et al., "The CLEF-2019 CheckThat! Lab on automatic identification and verification of claims," in *Proc. CLEF 2019*, 2019.

[12] E. M. B. Nagel, D. P. Salles, and M. V. M. Goncalves, "Conversational agents for fact-checking: A systematic review," *ACM Comput. Surv.*, vol. 56, no. 2, 2023.

[13] P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, 2020, pp. 9459-9474.

[14] V. Karpukhin et al., "Dense passage retrieval for open-domain question answering," in *Proc. EMNLP 2020*, pp. 6769-6781.

[15] M. Lewis et al., "BART: Denoising sequence-to-sequence pre-training for natural language generation, translation, and comprehension," in *Proc. ACL 2020*, pp. 7871-7880.

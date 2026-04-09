# Chapitre 4 : Implémentation, intégration multicanale et déploiement

## 4.1. Introduction

Après la modélisation architecturale, il convient de décrire la mise en œuvre concrète du système. Ce chapitre présente les principaux composants implémentés dans le projet RDC News Intelligence, les technologies utilisées, l'organisation du code, les mécanismes d'intégration multicanale et les opérations de maintenance qui permettent au système de rester fonctionnel et à jour.

L'objectif n'est pas seulement de montrer que le projet a été codé, mais d'expliquer comment les choix techniques du chapitre précédent ont été traduits en services réels, en routes d'API, en scripts d'ingestion et en outils de traitement. Cette partie sert également de pont entre la conception et l'exploitation du système.

## 4.2. Stack technologique

Le backend repose sur FastAPI, choisi pour sa simplicité, sa compatibilité avec Python et sa capacité à gérer des routes asynchrones. La base de données principale est PostgreSQL, complétée par l'extension pgvector pour la recherche vectorielle. Les embeddings sont produits par SentenceTransformers, tandis que la génération de réponses est assurée par un modèle local exécuté via Ollama.

Le traitement OCR est assuré par Tesseract, intégré au backend pour permettre l'analyse d'images contenant du texte. Les interactions avec les utilisateurs passent par Telegram et WhatsApp, chacun avec son mode d'intégration spécifique. Telegram fonctionne par polling, alors que WhatsApp s'appuie sur des webhooks fournis par l'API Cloud de Meta. Un service de décision thématique complète désormais cette chaîne afin de n'activer le bot en groupe que lorsque le contexte de groupe est identifiable et que le contenu concerne la politique, le sport, la santé ou la guerre; les messages privés continuent de suivre le flux complet sans filtrage.

Le projet utilise également un crawler pour alimenter le corpus en continu. Les articles collectés sont enregistrés sous format JSONL, puis réinjectés dans l'API afin d'être vectorisés et indexés. Cette chaîne technique constitue le socle de la mise à jour continue du moteur de recommandation.

## 4.3. Organisation du code

L'organisation du projet suit une séparation claire entre l'entrée de l'application, les routes et les services métiers. Le point d'entrée principal initialise l'application FastAPI, charge la configuration, connecte la base de données et active les traitements de fond nécessaires au fonctionnement du système.

Les routes gèrent les points d'accès externes. Certaines routes exposent les fonctionnalités de recherche et de génération. D'autres reçoivent les webhooks de messagerie ou les requêtes d'administration. Cette organisation améliore la lisibilité du projet et facilite la maintenance.

Les services métiers encapsulent la logique importante du système. Le service de vectorisation transforme les textes en embeddings. Le service de recherche interroge la base PostgreSQL. Le service de génération dialogue avec Ollama. Le service OCR extrait le texte des images. Un service de décision thématique analyse les messages avant déclenchement pour les groupes. Le service article gère l'insertion et la mise à jour des documents. Enfin, le service de pipeline d'entraînement permet de recalculer les représentations en cas de changement de modèle.

## 4.4. Flux d'exécution principaux

Le premier flux est celui de la requête textuelle. Lorsqu'un utilisateur envoie une question, le texte est d'abord soumis au contrôle thématique si le message provient d'un groupe identifiable. Si le contenu est jugé pertinent, ou si la conversation est privée, le texte est vectorisé, les articles les plus proches sont récupérés, puis le modèle génératif synthétise une réponse structurée. Ce processus constitue le cœur fonctionnel du système et correspond au cas d'usage principal du projet.

Le deuxième flux concerne les images. Le message contenant une image est reçu, le fichier est téléchargé, puis le texte est extrait par OCR. Lorsqu'une légende est présente, elle est fusionnée avec le résultat OCR afin de nourrir le filtre thématique. Le contenu obtenu rejoint ensuite la même chaîne de recherche et de génération que les requêtes textuelles si le message est accepté. Cette capacité est essentielle pour traiter les contenus partagés dans les messageries tout en évitant d'activer le bot sur des images hors sujet dans les groupes identifiables.

Le troisième flux concerne l'ingestion de données. Le crawler collecte les articles des sources configurées, produit un fichier JSONL, puis les articles sont injectés dans le backend. À ce moment, ils sont nettoyés, vectorisés et stockés avec leurs métadonnées. Le système devient alors immédiatement capable de les retrouver dans ses recherches.

## 4.5. Maintenance et mise à jour du corpus

L'une des particularités du projet est sa capacité à se mettre à jour. Lorsqu'un nouveau modèle de vectorisation est adopté ou lorsqu'un volume important d'articles a été ajouté, une opération de ré-embedding peut être lancée. Cette opération recalcule les vecteurs de tous les documents concernés et maintient la cohérence du corpus.

Le crawler joue également un rôle de maintenance. En collectant régulièrement de nouveaux articles, il évite l'obsolescence de la base de connaissance et alimente en continu le moteur de recommandation. Cette logique est cruciale dans un projet centré sur l'actualité, car la valeur du système dépend de la fraîcheur de ses données.

## 4.6. Résultats observables

Les premiers tests montrent que le système est capable de retrouver des articles proches d'une requête même lorsque les mots utilisés diffèrent fortement de ceux du corpus. Cette capacité confirme l'intérêt de la recherche vectorielle. Les réponses produites par le modèle de langage sont plus utiles lorsqu'elles sont précédées par une bonne phase de récupération documentaire.

L'intégration multicanale améliore également l'expérience utilisateur. Telegram permet une consultation rapide et simple, tandis que WhatsApp facilite l'usage dans les contextes où cette messagerie est dominante. L'ajout de l'OCR élargit enfin le champ d'application du système aux contenus visuels, et le filtrage thématique garantit que les groupes ne déclenchent le traitement automatique que pour les sujets visés.

## 4.7. Limites actuelles

Le système reste perfectible. La qualité des réponses dépend de la qualité des articles collectés, de la précision du crawl et de la diversité du corpus. Certains cas d'usage complexes nécessiteront peut-être des règles de filtrage supplémentaires, voire une meilleure structuration des prompts. De même, les performances OCR peuvent varier selon la qualité des images et la langue du texte extrait.

Ces limites ne remettent pas en cause l'intérêt du prototype, mais elles indiquent des pistes d'amélioration pour les versions futures.

## 4.8. Conclusion partielle

Ce chapitre a montré comment les choix de conception ont été traduits en composants fonctionnels. L'architecture RAG, le crawler, la base vectorielle, l'OCR local et les intégrations Telegram et WhatsApp forment un ensemble cohérent, orienté vers la recherche d'information et la recommandation contextualisée. Le système obtenu constitue une base solide pour une évolution ultérieure vers des usages plus avancés, notamment la détection de tendances, l'analyse de qualité des sources et l'assistance éditoriale.

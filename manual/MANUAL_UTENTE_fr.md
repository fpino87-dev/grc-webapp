# Manuel Utilisateur — GRC Platform

> Guide pour les utilisateurs finaux : Compliance Officer, Risk Manager, Plant Manager, Plant Security Officer, Auditeur Externe.

---

## Sommaire

- [1. Accès et navigation](#1-accès-et-navigation)
- [2. Tableau de bord](#2-tableau-de-bord)
- [3. Gestion des Contrôles (M03)](#3-gestion-des-contrôles-m03)
- [4. Assets IT et OT (M04)](#4-assets-it-et-ot-m04)
- [5. Business Impact Analysis (M05)](#5-business-impact-analysis-m05)
- [6. Risk Assessment (M06)](#6-risk-assessment-m06)
- [7. Documents et Preuves (M07)](#7-documents-et-preuves-m07)
- [8. Gestion des Incidents (M09)](#8-gestion-des-incidents-m09)
- [9. PDCA (M11)](#9-pdca-m11)
- [10. Lessons Apprises (M12)](#10-lessons-apprises-m12)
- [11. Revue de Direction (M13)](#11-revue-de-direction-m13)
- [12. Préparation Audit (M17)](#12-préparation-audit-m17)
- [13. Fournisseurs (M14)](#13-fournisseurs-m14)
- [14. Formation (M15)](#14-formation-m15)
- [15. Continuité d'Activité (M16)](#15-continuité-dactivité-m16)
- [16. Planning d'Activités (Échéancier)](#16-planning-dactivités-échéancier)
- [17. Documents Obligatoires](#17-documents-obligatoires)
- [18. Notifications Email](#18-notifications-email)
- [19. Gouvernance (M00)](#19-gouvernance-m00)
- [20. Paramètres (Admin uniquement)](#20-paramètres-admin-uniquement)
- [Rôles et ce que vous pouvez faire](#rôles-et-ce-que-vous-pouvez-faire)
- [AI Engine — suggestions IA (M20)](#ai-engine--suggestions-ia-m20)
- [Reporting et export (M18)](#reporting-et-export-m18)
- [Annexe : Questions fréquentes](#annexe--questions-fréquentes)

---

## 1. Accès et navigation

### Connexion avec email et mot de passe

[Écran : page de connexion]

1. Ouvrez votre navigateur et allez sur `https://grc.azienda.com`
2. Entrez votre **email professionnel** dans le premier champ
3. Entrez votre **mot de passe** dans le deuxième champ (minimum 12 caractères)
4. Cliquez sur **Se connecter**
5. Lors de la première connexion, il vous sera demandé de changer le mot de passe temporaire reçu par email

Si vous utilisez le SSO d'entreprise, cliquez plutôt sur **Se connecter avec le compte d'entreprise** et entrez les identifiants de votre compte de domaine.

> La session reste active pendant 30 minutes d'inactivité. Après expiration, il vous est demandé de saisir à nouveau votre mot de passe. Le jeton de session se renouvelle automatiquement pendant l'utilisation active.

Pour réinitialiser le mot de passe : depuis la page de connexion, cliquez sur **Mot de passe oublié** et entrez votre email. Vous recevrez un lien valable 15 minutes.

### Sélection du site (plant) en haut à gauche

[Écran : sélecteur de plant dans la barre supérieure]

Juste après la connexion, en haut à gauche près du logo, vous trouverez le **sélecteur de plant**. Si vous avez accès à plusieurs établissements ou unités d'affaires :

1. Cliquez sur le nom du plant actuel (ou sur "Sélectionner un plant" lors de la première connexion)
2. Un menu déroulant apparaît avec tous les plants dans votre périmètre
3. Cliquez sur le plant que vous souhaitez afficher — la page se met à jour immédiatement

L'entrée **Tous les plants** affiche une vue agrégée de tous les établissements. Cette option est disponible uniquement pour les Compliance Officers et les rôles avec accès multi-plant.

Toutes les opérations (création d'asset, ouverture d'incidents, évaluation des contrôles) sont associées au plant sélectionné à ce moment-là.

### Changement de langue (IT/EN) en haut à droite

[Écran : menu de langue dans la barre supérieure]

1. Cliquez sur l'icône de langue (ou sur le code de la langue courante) en haut à droite
2. Sélectionnez la langue souhaitée : **Italiano**, **English**, **Français**, **Polski**, **Türkçe**
3. L'interface se met à jour immédiatement sans recharger la page

La langue sélectionnée s'applique à toute l'interface. Les rapports PDF générés utilisent la langue active au moment de la génération.

### Menu latéral : sections principales et leur contenu

[Écran : barre latérale avec menu déroulé]

Le menu latéral gauche affiche uniquement les sections accessibles selon votre rôle. Les entrées principales sont :

| Entrée | Contenu |
|--------|---------|
| **Tableau de bord** | KPI de conformité, carte de chaleur des risques, échéances imminentes, alertes |
| **Compliance** | Bibliothèque de contrôles (M03), documents (M07), preuves |
| **Risk** | Assets IT/OT (M04), BIA (M05), Risk Assessment (M06) |
| **Opérations** | Incidents (M09), Tâches/Échéancier (M08), PDCA (M11) |
| **Gouvernance** | Organigramme/Rôles (M00), Lessons Apprises (M12), Revue de Direction (M13), Fournisseurs (M14), Formation (M15), BCP (M16) |
| **Audit** | Préparation Audit (M17), Reporting (M18) |
| **Notifications** | Notifications email, préférences |
| **Paramètres** | Uniquement pour les rôles administratifs — SMTP, politiques, profils de notification |

Pour développer ou réduire une section, cliquez sur le titre de l'entrée. L'état du menu est mémorisé d'une session à l'autre.

### Icône ? sur chaque page pour l'aide contextuelle

[Écran : bouton ? à côté du titre de la page]

Sur presque toutes les pages opérationnelles, vous trouverez un petit bouton **`?`** près du titre du module. En cliquant dessus, un panneau latéral s'ouvre avec :

- Une brève explication de ce que fait le module
- Les étapes typiques à suivre
- Les connexions avec d'autres modules (ex. quelles tâches ou cycles PDCA sont créés automatiquement)
- La liste des prérequis recommandés ("Avant de commencer")

Utilisez le panneau d'aide pour vous orienter sur des modules que vous utilisez moins souvent ou lorsque vous présentez le système à de nouveaux collègues.

### Boutons Manuel Utilisateur et Manuel Technique dans la barre inférieure

[Écran : barre inférieure avec boutons de manuel]

En bas de chaque page, dans la barre inférieure, vous trouverez deux boutons fixes :

- **Manuel Utilisateur** (icône livre) : ouvre ce manuel dans un nouvel onglet
- **Manuel Technique** (icône clé) : ouvre le manuel technique avec les détails architecturaux, visible uniquement aux profils ayant un accès administratif

Les deux boutons sont toujours visibles quel que soit le module dans lequel vous vous trouvez.

---

## 2. Tableau de bord

[Écran : tableau de bord principal]

Le tableau de bord est la première page que vous voyez après la connexion. Le contenu est personnalisé selon votre rôle et le plant sélectionné.

### Ce que montrent les KPI principaux

En haut du tableau de bord, vous trouverez 4 blocs avec les KPI principaux :

| KPI | Ce qu'il mesure |
|-----|----------------|
| **Conformité %** | Pourcentage de contrôles en état "conforme" ou "partiel avec preuve valide" par rapport au total des contrôles actifs pour le framework sélectionné |
| **Risques ouverts** | Nombre d'évaluations de risques avec le statut "ouvert" (non acceptés et non fermés). Le nombre est accompagné du décompte des risques critiques (score > 14) en rouge |
| **Incidents** | Incidents ouverts dans le plant sélectionné. Les chiffres en rouge indiquent les incidents avec des minuteries NIS2 actives |
| **Tâches en retard** | Tâches assignées à votre rôle (ou à toute votre organisation si vous êtes CO) dont la date d'échéance est déjà dépassée |

### Comment interpréter les couleurs

La plateforme utilise une convention de couleurs cohérente sur toute l'interface :

- **Vert** : tout est en ordre — conforme, terminé, valide, dans les délais
- **Jaune** : attention requise — partiel, échéance dans 30 jours, en cours
- **Rouge** : critique — écart, en retard, risque élevé (score > 14), minuterie NIS2 qui expire
- **Gris** : non évalué, N/A, archivé
- **Orange** : alerte ou avertissement — nécessite de l'attention mais n'est pas encore critique

Ces couleurs s'appliquent aux badges de statut, aux barres de progression, aux indicateurs dans la carte de chaleur et aux icônes dans la barre latérale.

### Widget des prochaines échéances

[Écran : widget d'échéances dans le tableau de bord]

Le widget "Prochaines échéances" affiche les 10 premières échéances dans les 30 jours suivants. Pour chaque échéance, vous voyez :

- Le type (document, preuve, tâche, évaluation fournisseur, etc.)
- Le nom de l'élément
- La date d'échéance avec couleur jaune (< 30 jours) ou rouge (< 7 jours)

En cliquant sur une échéance, vous êtes directement redirigé vers la page de l'élément concerné.

### Alertes rôles vacants

Si des rôles normatifs obligatoires n'ont pas de titulaire assigné (ex. RSSI non nommé, DPO vacant), un bandeau orange "Rôles vacants" apparaît dans le tableau de bord avec le décompte et un lien vers la page de gouvernance (M00). Ces alertes impactent négativement le KPI de conformité.

### Comment naviguer directement vers un élément depuis le tableau de bord

Chaque élément interactif du tableau de bord est cliquable :

- Cliquez sur une tâche en retard pour ouvrir la fiche de la tâche
- Cliquez sur un quadrant de la carte de chaleur pour voir les risques dans cette zone
- Cliquez sur une barre de conformité pour aller à la bibliothèque de contrôles filtrée par ce framework
- Cliquez sur un incident pour ouvrir la fiche de l'incident

---

## 3. Gestion des Contrôles (M03)

[Écran : bibliothèque de contrôles]

### Comment évaluer un contrôle

1. Allez sur **Compliance → Bibliothèque de contrôles**
2. Utilisez les filtres (framework, domaine, statut, plant) pour trouver le contrôle qui vous intéresse
3. Cliquez sur le nom du contrôle pour ouvrir la fiche
4. Dans le champ **Statut**, cliquez pour ouvrir le sélecteur et choisissez le statut approprié
5. Ajoutez une note de contexte dans le champ **Notes d'évaluation** (obligatoire pour Écart et N/A)
6. Liez la preuve via le bouton **Joindre une preuve**
7. Cliquez sur **Enregistrer**

### Différence entre Conforme, Partiel, Écart, N/A

| Statut | Quand l'utiliser |
|--------|-----------------|
| **Conforme** | Le contrôle est entièrement satisfait. Vous disposez d'une preuve valide et non expirée qui le démontre |
| **Partiel** | Le contrôle n'est que partiellement mis en œuvre. Il existe un plan pour le compléter, mais les exigences ne sont pas encore toutes satisfaites |
| **Écart** | Le contrôle n'est pas mis en œuvre. Une action corrective est nécessaire. Génère automatiquement une tâche |
| **N/A** | Le contrôle ne s'applique pas au contexte de votre plant. Requiert une justification écrite d'au moins 20 caractères. La justification est sauvegardée et visible à chaque réouverture du contrôle. Dans le VDA ISA TISAX, elle apparaît dans la colonne "Note / Justification" et le niveau de maturité est défini à 0. Pour TISAX L3, nécessite la signature de deux rôles et expire après 12 mois |

> Un contrôle avec une preuve expirée revient automatiquement à "Partiel" même si vous l'aviez défini comme Conforme. Maintenez les preuves à jour.

### Comment charger une preuve

1. Depuis la fiche du contrôle, cliquez sur **Joindre une preuve**
2. Cliquez sur **Choisir un fichier** et sélectionnez le fichier depuis votre ordinateur (formats acceptés : PDF, DOCX, XLSX, PNG, JPG, ZIP — taille maximale 50 Mo)
3. Renseignez :
   - **Description courte** (ex. "Capture d'écran de la configuration du pare-feu du 15/03/2026")
   - **Date d'expiration** — obligatoire pour les journaux système, rapports d'analyse, certificats. Laissez vide pour les documents sans date d'expiration
   - **Framework / contrôles couverts** — sélectionnez tous les contrôles que cette preuve documente
4. Cliquez sur **Charger**

La preuve est disponible immédiatement. Le système vérifiera automatiquement que le type MIME du fichier correspond à l'extension déclarée.

### Comment télécharger la SOA ISO 27001, VDA ISA TISAX, NIS2 Matrix

[Écran : page d'export de conformité]

1. Allez sur **Compliance → Bibliothèque de contrôles**
2. Cliquez sur le bouton **Exporter** (icône de téléchargement) en haut à droite de la page
3. Sélectionnez le type d'export :
   - **SOA ISO 27001** — Déclaration d'Applicabilité avec tous les contrôles de l'Annexe A et leur statut correspondant
   - **VDA ISA TISAX** — Tableau VDA Information Security Assessment
   - **NIS2 Matrix** — Matrice de conformité NIS2

> **Note importante** : utilisez toujours le bouton "Exporter" à l'intérieur de la page. N'ouvrez pas l'URL du fichier directement depuis le navigateur en copiant le lien — le téléchargement nécessite le jeton JWT de la session active et échouerait avec une erreur 401 si tenté en dehors de la plateforme.

### Analyse des écarts entre frameworks

1. Allez sur **Compliance → Analyse des écarts**
2. Sélectionnez les deux frameworks à comparer (ex. ISO 27001 vs TISAX L2)
3. Le système affiche un tableau avec les contrôles mis en correspondance entre les deux frameworks, en mettant en évidence :
   - Les contrôles satisfaits dans les deux frameworks (vert)
   - Les contrôles satisfaits dans un seul des deux (jaune)
   - Les contrôles en écart dans les deux (rouge)
4. Vous pouvez exporter l'analyse des écarts au format Excel

### Propagation de statut entre frameworks (et entre plants)

Le bouton **Propager** est disponible dans la liste des contrôles, à côté du badge de statut, pour les contrôles en statut **Conforme** ou **N/A** disposant de correspondances vers d'autres frameworks.

**Fonctionnement :**

| Type de correspondance | Direction | Exemple |
|------------------------|-----------|---------|
| `Équivalent` | Bidirectionnel | ISO A.8.1 ≡ TISAX ISA-1.1 → propage dans les deux sens |
| `Couvre (covers)` | Source → cible uniquement | ISO A couvre NIS2 art.21 → ISO propage vers NIS2, pas l'inverse |
| `Partiel`, `Corrélé`, `Étend` | Non propagé | Nécessitent une évaluation séparée |

**Ce qui est copié :**
- Le statut (`compliant` ou `na`) vers le contrôle correspondant du même plant
- Pour N/A : la justification est également copiée (avec référence au contrôle source)
- Un enregistrement d'audit est généré pour chaque contrôle mis à jour

**Propagation multi-plant :**
En cochant la case **"tous plants"**, la propagation s'étend à tous les plants disposant d'une instance active du contrôle cible. À utiliser lorsqu'une politique organisationnelle est partagée entre plusieurs sites.

> Les statuts `écart`, `partiel` et `non évalué` ne sont pas propagables : chaque plant doit les évaluer indépendamment.

---

## 4. Assets IT et OT (M04)

[Écran : inventaire des assets]

### Comment ajouter un asset

**Asset IT :**

1. Allez sur **Risk → Inventaire des assets → Nouvel asset IT**
2. Renseignez les champs obligatoires :
   - **Nom / FQDN** : nom d'hôte ou adresse IP
   - **Système d'exploitation** et **version**
   - **Date EOL** : si le système n'est plus supporté, la criticité est automatiquement augmentée
   - **Exposé sur Internet** : indicateur critique — augmente le profil de risque
   - **Niveau de criticité** : de 1 à 5 (voir tableau ci-dessous)
3. Dans la section **Processus critiques liés**, sélectionnez les processus de la BIA (M05) qui dépendent de cet asset
4. Cliquez sur **Enregistrer**

**Asset OT :**

1. Allez sur **Risk → Inventaire des assets → Nouvel asset OT**
2. En plus des champs communs des assets IT, renseignez :
   - **Niveau Purdue** (0–5) : position dans la hiérarchie réseau OT
   - **Catégorie** : PLC, SCADA, HMI, RTU, capteur, autre
   - **Patchable** : si le système ne peut pas être patché, indiquez la raison et la fenêtre de maintenance prévue
3. Cliquez sur **Enregistrer**

### Différence entre asset IT et OT

| Caractéristique | Asset IT | Asset OT |
|----------------|---------|---------|
| Exemples | Serveurs, postes de travail, pare-feux, commutateurs, applications | PLC, SCADA, HMI, RTU, capteurs industriels |
| Réseau typique | Réseau d'entreprise, Internet | Réseau de production, bus de terrain |
| Patching | Fréquent, automatisable | Limité, nécessite des fenêtres de maintenance |
| Impact en cas d'interruption | Perte de données, indisponibilité de service | Arrêt de production, dommages physiques, risque de sécurité |
| Risk assessment | Dimensions exposition/CVE | Dimensions Purdue/patchabilité/sécurité |

### Tableau de criticité 1-5

Dans le formulaire de création et de modification d'asset, vous trouverez un badge de criticité avec des infobulles explicatives pour chaque niveau. À titre de référence :

| Niveau | Étiquette | Description |
|--------|-----------|-------------|
| **1** | Faible | L'arrêt ou la compromission n'impacte pas la production. Perte acceptable sans plan de continuité dédié |
| **2** | Moyen-faible | Impact limité aux fonctions administratives ou de support. Restauration en moins de 24 heures |
| **3** | Moyen | Impact sur les processus opérationnels. Nécessite un plan de continuité. Perte de données ou de production mesurable |
| **4** | Élevé | L'arrêt cause une perte financière significative, un impact sur les clients ou sur la conformité réglementaire. RTO < 4 heures |
| **5** | Critique | Impact sur la sécurité, risque pour la vie ou dommages physiques, ou arrêt total de la production. RTO < 1 heure. Nécessite une analyse de risque immédiate |

Utilisez toujours ce tableau pour garantir la cohérence entre différents plants.

### Comment enregistrer un changement externe

Lorsqu'un asset subit une modification significative (mise à jour du firmware, changement de configuration, extension du périmètre réseau) :

1. Ouvrez la fiche de l'asset
2. Cliquez sur **Enregistrer un changement** dans la section "Historique des modifications"
3. Renseignez : date du changement, description, type (configuration / matériel / logiciel / réseau), impact estimé
4. Enregistrez — le changement est consigné dans l'audit trail et l'asset reçoit le badge "À réévaluer"

### Badge "À réévaluer" — quand il apparaît et que faire

Le badge orange **"À réévaluer"** apparaît sur la fiche de l'asset lorsque :

- Un changement externe a été enregistré
- La date de révision périodique prévue par la politique est échue
- Un risque lié à l'asset a changé de score de manière significative
- L'asset a atteint la date EOL du système d'exploitation

Que faire : ouvrez la fiche de l'asset, vérifiez que les informations sont toujours exactes (en particulier la criticité, l'exposition et les processus critiques liés), puis cliquez sur **Marquer comme réévalué**. Si nécessaire, mettez à jour les champs avant de confirmer.

---

## 5. Business Impact Analysis (M05)

[Écran : liste des processus BIA]

### Comment créer un processus critique

1. Allez sur **Risk → BIA → Nouveau processus**
2. Renseignez :
   - **Nom du processus** : ex. "Gestion des ordres de production"
   - **Description** : ce que fait le processus, qui l'utilise
   - **Propriétaire du processus** : sélectionnez le rôle responsable
   - **Département / fonction** : domaine d'activité de référence
   - **Plant** : établissement de référence
3. Enregistrez — le processus entre en état **Brouillon**

### MTPD, RTO, RPO — explication simple avec exemples

Ces trois paramètres définissent la tolérance du processus à l'interruption :

| Paramètre | Définition | Exemple pratique |
|-----------|------------|-----------------|
| **MTPD** (Maximum Tolerable Period of Disruption) | Combien de temps le processus peut être interrompu avant que l'entreprise ne subisse des dommages irréversibles | Ex. "Le processus d'expédition peut être interrompu au maximum 48 heures avant de perdre des clients clés" |
| **RTO** (Recovery Time Objective) | En combien de temps nous devons restaurer le processus après une interruption | Ex. "Le système MES doit redevenir opérationnel dans les 4 heures suivant l'incident" |
| **RPO** (Recovery Point Objective) | Jusqu'à quel point dans le passé pouvons-nous perdre des données sans dommages acceptables | Ex. "Nous ne pouvons pas perdre plus d'1 heure de données de production" — donc les sauvegardes doivent être effectuées au moins toutes les heures |

Le système utilise RTO et RPO pour vérifier que le plan BCP associé (M16) est cohérent : si le BCP prévoit un RTO supérieur à celui déclaré dans la BIA, un avertissement apparaît.

### Flux : brouillon → validation → approbation

1. **Brouillon** : le processus a été créé mais pas encore validé. Vous pouvez modifier tous les champs
2. **Validation** : le Risk Manager vérifie les paramètres MTPD/RTO/RPO et les approuve ou demande des modifications
3. **Approbation** : le Plant Manager approuve formellement. Le processus devient immuable — pour le modifier, il est nécessaire d'ouvrir une nouvelle révision

Pour avancer d'une phase : depuis la fiche du processus, cliquez sur **Envoyer pour validation** (depuis Brouillon) ou **Envoyer pour approbation** (depuis Validation).

### Comment lier un processus à un asset

1. Ouvrez la fiche du processus BIA
2. Dans la section **Assets dépendants**, cliquez sur **Ajouter un asset**
3. Recherchez et sélectionnez l'asset dans l'inventaire (M04)
4. Indiquez le type de dépendance : **Critique** (le processus s'arrête sans cet asset) ou **Support** (dégradation des performances)
5. Enregistrez

La dépendance est bidirectionnelle : l'asset affichera dans sa fiche les processus qui en dépendent, et la criticité du processus influence le calcul du risque sur l'asset.

---

## 6. Risk Assessment (M06)

[Écran : liste des risk assessments]

### Différence entre risque inhérent et risque résiduel

- **Risque inhérent** : le niveau de risque en l'absence de tout contrôle. Il représente la menace "brute" sur l'asset ou le domaine
- **Risque résiduel** : le niveau de risque après application des contrôles existants. C'est la valeur sur laquelle se base la décision d'accepter ou de traiter le risque

Dans le formulaire d'évaluation, vous renseignez d'abord le risque inhérent, puis le système calcule automatiquement le résiduel en fonction du statut des contrôles associés. Si les contrôles ne sont pas encore suffisants, le résiduel reste élevé.

### Comment renseigner les dimensions IT et OT

**Dimensions du risk assessment IT (4 axes) :**

1. **Exposition** : l'asset est-il sur Internet ? En DMZ ? Isolé ? (1 = complètement isolé, 5 = exposé sur Internet sans protections)
2. **CVE** : quel est le score CVE maximum des assets concernés ? (1 = aucune vulnérabilité connue, 5 = CVE critique non patchée)
3. **Menaces sectorielles** : y a-t-il des menaces actives connues pour le secteur automobile ? (1 = aucune, 5 = campagne active documentée)
4. **Écarts de contrôles** : combien de contrôles pertinents sont en état d'écart ou non évalués ? (1 = tous conformes, 5 = majorité en écart)

**Dimensions du risk assessment OT (5 axes) :**

1. **Purdue + connectivité** : le système est-il connecté à des réseaux IT ou à Internet ? (1 = niveau 0 isolé, 5 = connecté à Internet)
2. **Patchabilité** : le système peut-il être mis à jour ? Avec quelle fréquence ? (1 = patches réguliers, 5 = jamais patchable)
3. **Impact physique / sécurité** : une interruption ou altération peut-elle causer des dommages physiques ou des risques pour la sécurité au travail ? (1 = aucun impact physique, 5 = risque pour l'intégrité des personnes)
4. **Segmentation** : la zone OT est-elle correctement séparée de l'IT et d'Internet ? (1 = complètement ségrégée, 5 = réseau plat)
5. **Détectabilité des anomalies** : existe-t-il un système de détection pour les comportements anormaux ? (1 = IDS/ICS dédié actif, 5 = aucune visibilité)

### Seuil critique (score > 14) et tâches automatiques générées

Lorsque le **risque résiduel dépasse 14** (quadrants rouges de la carte de chaleur 5x5) :

- Le Risk Manager et le Plant Manager reçoivent une notification immédiate
- Une tâche de planification du traitement du risque est automatiquement créée avec une échéance de 15 jours
- Si la tâche n'est pas complétée dans les 15 jours, une escalade est envoyée au Compliance Officer
- Le risque est mis en évidence en rouge dans le tableau de bord et dans la carte de chaleur

### Acceptation formelle du risque

Si le risque résiduel est connu mais que l'on décide de l'accepter (ex. coût du traitement supérieur à l'impact attendu) :

1. Depuis la fiche du risque, cliquez sur **Accepter le risque**
2. Remplissez le formulaire d'acceptation formelle :
   - Justification (obligatoire, minimum 50 caractères)
   - Date de révision (obligatoire — le risque doit être réévalué périodiquement)
   - Signature numérique du responsable autorisé
3. Enregistrez — le risque passe à l'état "Accepté" et ne génère plus d'alertes jusqu'à la date de révision

### Carte de chaleur et interprétation

[Écran : carte de chaleur 5x5]

La carte de chaleur affiche les risques sur une grille Probabilité x Impact 5x5 :

- **Vert** (score 1-7) : risque acceptable — surveillance périodique
- **Jaune** (score 8-14) : risque modéré — plan de mitigation dans les 90 jours
- **Rouge** (score 15-25) : risque élevé — escalade automatique, plan dans les 15 jours

Cliquez sur un quadrant pour voir la liste des risques qui le composent. Utilisez le filtre plant pour comparer la distribution des risques entre différents établissements.

---

## 7. Documents et Preuves (M07)

[Écran : gestion des documents]

### Différence entre Document et Preuve

| Caractéristique | Document | Preuve |
|----------------|----------|--------|
| Ce qu'il représente | Politique, procédure, instruction opérationnelle | Capture d'écran, journal, rapport d'analyse, certificats |
| Workflow obligatoire | Oui — rédaction, révision, approbation | Non — téléchargement direct |
| Versionnage | Oui — chaque version est immuable après approbation | Non |
| Date d'expiration | Seulement si explicitement configurée | Obligatoire pour les journaux, analyses, certificats |
| Usage principal | Démontrer qu'un processus existe et est gouverné | Démontrer qu'un contrôle est actif et fonctionnel |

### Workflow d'approbation des documents (3 niveaux)

Le document traverse 3 phases obligatoires en séquence :

1. **Rédaction** (propriétaire du document) : chargez le fichier PDF, renseignez les métadonnées (titre, code, framework, propriétaire, réviseur, approbateur), enregistrez en brouillon. Le document n'est modifiable qu'à cette phase
2. **Révision** (réviseur désigné) : lit le document, peut ajouter des notes structurées ou approuver. S'il refuse, il doit rédiger un commentaire qui fait partie du journal des modifications permanent
3. **Approbation de la direction** (Plant Manager ou RSSI) : approuve formellement. Après l'approbation, le document est immuable — pour le modifier, vous devez ouvrir une nouvelle révision via le bouton **Nouvelle révision**

### Comment lier une preuve à un contrôle

Méthode 1 — depuis la fiche du contrôle :
1. Allez sur la fiche du contrôle (Compliance → Bibliothèque de contrôles → sélectionnez le contrôle)
2. Cliquez sur **Joindre une preuve** dans la section "Preuves associées"
3. Chargez le fichier ou sélectionnez une preuve déjà chargée depuis votre archive
4. Enregistrez

Méthode 2 — depuis la fiche de la preuve :
1. Chargez la preuve via **Compliance → Preuves → Nouvelle preuve**
2. Dans le champ **Contrôles couverts**, sélectionnez un ou plusieurs contrôles que cette preuve documente
3. Enregistrez

Une preuve peut couvrir plusieurs contrôles simultanément, même de frameworks différents.

### Expiration des preuves et badges colorés

Les preuves avec une date d'expiration affichent un badge coloré dans la fiche du contrôle et dans la liste des preuves :

| Badge | Signification |
|-------|--------------|
| **Vert** | Preuve valide — expiration à plus de 30 jours |
| **Jaune** | En cours d'expiration — moins de 30 jours restants |
| **Rouge** | Expirée — la date d'expiration est déjà passée. Le contrôle associé se dégrade automatiquement à "Partiel" |
| **Gris** | Aucune date d'expiration définie |

Le système envoie un rappel par email 30 jours avant l'expiration et une alerte à la date d'expiration effective.

### Versionnage des documents

Chaque document approuvé reçoit un numéro de version (ex. v1.0, v1.1, v2.0). L'historique complet de toutes les versions est accessible depuis la fiche du document dans la section **Historique des versions**. Chaque version enregistre :

- La date d'approbation
- Le nom de l'approbateur
- Le journal des modifications (notes du réviseur)
- Le hash du fichier pour garantir l'intégrité

---

## 8. Gestion des Incidents (M09)

[Écran : liste des incidents]

### Comment ouvrir un incident

1. Allez sur **Opérations → Incidents → Nouvel incident**
2. Renseignez les champs obligatoires :
   - **Plant concerné** : détermine automatiquement le profil NIS2 de l'entité
   - **Titre** : description synthétique (ex. "Accès non autorisé au système MES — établissement Nord")
   - **Description** : ce qui s'est passé, quand cela a été détecté, comment cela a été découvert
   - **Assets concernés** : sélectionnez dans l'inventaire (M04)
   - **Sévérité initiale** : Faible / Moyen / Élevé / Critique — modifiable à tout moment
3. Cliquez sur **Créer l'incident**

Immédiatement après la création, le système évalue si le plant est un sujet NIS2 et, si c'est le cas, lance les minuteries ACN visibles en haut de la fiche de l'incident.

### Indicateur NIS2 et minuterie 24h (notification ACN)

[Écran : fiche d'incident avec minuterie NIS2]

Si le plant est classifié comme sujet NIS2 (essentiel ou important), trois comptes à rebours apparaissent dans la fiche de l'incident :

- **T+24h — Avertissement précoce ACN** : notification préliminaire à l'autorité de référence (obligation légale)
- **T+72h — Notification complète** : notification détaillée avec impact et mesures adoptées
- **T+30j — Rapport final** : rapport conclusif avec analyse de cause racine

Le RSSI dispose de 30 minutes à compter de la création de l'incident pour confirmer ou exclure l'obligation de notification via le bouton **Exclure l'obligation NIS2**. S'il ne répond pas dans les 30 minutes, le système suppose que la notification est due et les minuteries restent actives.

Les minuteries s'affichent avec un fond rouge lorsque le temps restant est inférieur à 2 heures.

### Rédaction de l'analyse de cause racine (RCA)

1. Dans la fiche de l'incident, allez à la section **Analyse de Cause Racine**
2. Choisissez la méthode d'analyse :
   - **5 Pourquoi** : guidé, avec 5 niveaux de "pourquoi"
   - **Ishikawa** : diagramme cause-effet par catégorie (Personnes, Processus, Technologie, Environnement)
   - **Texte libre** : narratif non structuré
3. Renseignez la cause racine, les contrôles défaillants et les actions correctives proposées
4. Envoyez pour approbation au Risk Manager via **Envoyer pour approbation**

Un incident ne peut pas être fermé sans une RCA approuvée.

### Clôture et cycle PDCA automatique généré

Après l'approbation de la RCA, vous pouvez fermer l'incident via le bouton **Fermer l'incident**. La clôture génère automatiquement :

- Une **Leçon Apprise** dans M12 avec les informations de l'incident et les actions correctives
- Un cycle **PDCA** dans M11 si les actions correctives sont structurelles (ex. modification de procédures, mise en œuvre de nouveaux contrôles)
- Un déclencheur de **révision** sur les documents associés dans M07 si les contrôles défaillants sont couverts par des politiques existantes

---

## 9. PDCA (M11)

[Écran : liste des cycles PDCA]

### Les 4 phases : PLAN, DO, CHECK, ACT

Chaque cycle PDCA représente une action d'amélioration continue. Les 4 phases suivent une séquence obligatoire :

- **PLAN** : définissez l'objectif, les actions à entreprendre et les ressources nécessaires
- **DO** : exécutez les actions planifiées
- **CHECK** : vérifiez que les résultats correspondent aux objectifs à travers une preuve mesurable
- **ACT** : standardisez la solution si elle a fonctionné, ou repartez de DO avec une approche différente

### Ce qui est requis pour avancer à chaque phase

| Transition | Exigence obligatoire |
|------------|---------------------|
| **PLAN → DO** | Description de l'action à exécuter (minimum 20 caractères). Le plan doit être compréhensible hors contexte |
| **DO → CHECK** | Preuve jointe documentant l'action exécutée (fichier obligatoire) |
| **CHECK → ACT** | Résultat de la vérification (texte descriptif) + Résultat choisi : **ok** / **partiel** / **ko** |
| **ACT → CLÔTURÉ** | Standardisation : documentation de la solution adoptée pour qu'elle soit reproductible (minimum 20 caractères) |

### Que se passe-t-il si le résultat CHECK = ko

Si lors de la phase CHECK le résultat est **ko** (la solution n'a pas fonctionné) :

1. Le cycle n'avance pas à ACT mais revient automatiquement à la phase **DO**
2. Une note est ajoutée dans le journal du cycle avec la date de l'échec
3. Il est nécessaire de rédiger un nouveau plan d'action pour la phase DO
4. Le compteur de cycles DO est incrémenté pour tracer le nombre d'itérations nécessaires

Il n'y a pas de limite au nombre d'itérations DO-CHECK, mais le système signale les cycles avec plus de 3 itérations au Compliance Officer.

### Cycles PDCA créés automatiquement par des incidents, findings, risques critiques

Les cycles PDCA sont créés manuellement ou automatiquement par :

- **Incidents clos (M09)** : lorsque les actions correctives de la RCA sont structurelles — phase de départ PLAN
- **Findings d'audit (M17)** : pour Major NC et Minor NC — phase de départ PLAN avec échéance déterminée par la sévérité
- **Risques avec score > 14 (M06)** : lorsque le plan de traitement requiert des actions structurelles — phase PLAN urgente
- **Délibérations de la revue de direction (M13)** : pour chaque action approuvée par la revue — phase PLAN

Dans tous les cas de création automatique, le cycle PDCA mentionne la référence à l'entité d'origine (ex. "Incident #INC-2026-042") et l'éventuelle échéance découlant de la politique.

---

## 10. Lessons Apprises (M12)

[Écran : base de connaissances des lessons apprises]

### Comment créer une leçon apprise manuellement

1. Allez sur **Gouvernance → Lessons Apprises → Nouvelle**
2. Renseignez :
   - **Titre** : description synthétique de l'événement ou de l'apprentissage
   - **Description de l'événement** : ce qui s'est passé, contexte, pertinence
   - **Méthode d'analyse utilisée** : 5 Pourquoi, Ishikawa, texte libre
   - **Cause racine identifiée**
   - **Contrôles impactés** : sélectionnez les contrôles pertinents dans la bibliothèque
   - **Actions à court terme** : actions à compléter dans les 30 jours
   - **Actions structurelles** : actions à long terme (seront gérées via PDCA)
3. Cliquez sur **Envoyer pour approbation**

Le Risk Manager ou le Compliance Officer approuvent la leçon apprise avant qu'elle devienne visible à toute l'organisation dans la base de connaissances.

### Lessons apprises créées automatiquement depuis des cycles PDCA clôturés

Lorsqu'un cycle PDCA est clôturé avec un résultat positif, le système crée automatiquement une leçon apprise qui inclut :

- Le contexte d'origine (incident, finding, risque) qui a déclenché le PDCA
- Les actions exécutées lors des phases DO
- Le résultat obtenu dans la phase CHECK
- La standardisation documentée dans la phase ACT

La leçon apprise automatique part en état "Brouillon" et est assignée comme tâche au propriétaire du cycle PDCA pour révision avant approbation.

### Recherche dans la base de connaissances

Allez sur **Gouvernance → Lessons Apprises → Base de connaissances**. Vous pouvez chercher par :

- **Mot-clé** : recherche textuelle sur le titre et la description
- **Framework / contrôle** : filtre par contrôles impactés
- **Type d'événement** : incident, finding, risque, amélioration volontaire
- **Plant** : uniquement les lessons apprises de votre plant, ou de tous les plants (si vous avez un accès multi-plant)
- **Période** : date d'approbation

Seules les lessons apprises approuvées sont affichées. Les brouillons sont visibles uniquement par le propriétaire et les réviseurs.

---

## 11. Revue de Direction (M13)

[Écran : revue de direction]

### Comment créer une revue

1. Allez sur **Gouvernance → Revue de Direction → Nouvelle**
2. Renseignez :
   - **Année et numéro** : ex. "2026 — Rev. 1/2026"
   - **Date planifiée**
   - **Participants** : sélectionnez les rôles impliqués (Plant Manager, RSSI, Risk Manager, CO)
3. Le système ajoute automatiquement les points obligatoires à l'ordre du jour (voir ci-dessous)
4. Vous pouvez ajouter des points supplémentaires via **Ajouter un point à l'OdJ**
5. Cliquez sur **Enregistrer le brouillon**

### Points à l'ordre du jour obligatoires (ISO 27001 cl.9.3)

La norme ISO 27001 clause 9.3 impose que la revue de direction inclue obligatoirement un ensemble de points. Le système les insère automatiquement dans le brouillon :

- État des actions des revues précédentes
- Changements dans le contexte interne et externe pertinents pour le SGSI
- Retours sur les performances du SGSI (NC, audits, surveillance, mesures)
- Retours des parties intéressées
- Résultats de l'évaluation des risques et état du plan de traitement
- Opportunités d'amélioration continue

Il n'est pas possible de clôturer une revue si l'un de ces points n'a pas au moins un commentaire ou une décision enregistrée.

### Comment enregistrer les décisions

Pour chaque point à l'ordre du jour :

1. Cliquez sur le point pour le développer
2. Saisissez le **résumé de la discussion**
3. Cliquez sur **Ajouter une décision** pour enregistrer les actions approuvées par la direction
4. Pour chaque décision, précisez : responsable, action à entreprendre, échéance

Les décisions avec responsable et échéance sont automatiquement transformées en tâches dans M08 et, si structurelles, en cycles PDCA dans M11.

### Clôture et approbation

1. Après avoir complété tous les points obligatoires, cliquez sur **Envoyer pour approbation**
2. Le Plant Manager reçoit une tâche d'approbation
3. Une fois approuvée, la revue devient immuable
4. Le procès-verbal en PDF signé avec hash et horodatage est automatiquement généré, disponible dans la section **Documents générés** de la revue

---

## 12. Préparation Audit (M17)

[Écran : préparation audit — liste des programmes]

### Programme Annuel

#### Comment créer le programme avec l'assistant (4 étapes)

1. Allez sur **Audit → Préparation Audit → Nouveau programme**
2. L'assistant s'ouvre en 4 étapes :

**Étape 1 — Données de base**
- Année du programme (ex. 2026)
- Plant de référence
- Framework(s) à auditer (ISO 27001, TISAX L2, TISAX L3, NIS2 — sélectionnez un ou plusieurs)
- Nom du programme (ex. "Programme Audit ISO 27001 — Établissement Nord 2026")

**Étape 2 — Paramètres de couverture**
Choisissez le niveau de couverture de l'audit :
- **Échantillon (25 %)** : audit ponctuel sur un quart des contrôles. Adapté aux vérifications intermédiaires ou lorsque les ressources sont limitées
- **Étendu (50 %)** : couverture de la moitié des contrôles. Équilibre entre profondeur et durabilité
- **Complet (100 %)** : audit complet de tous les contrôles du framework. Requis pour les certifications formelles

**Étape 3 — Révision du plan suggéré**
Le système analyse l'état actuel des contrôles et génère un plan suggéré qui :
- Concentre Q1 et Q3 sur les **domaines avec le plus d'écarts** (les plus critiques sont audités en premier)
- Distribue les contrôles restants dans les trimestres Q2 et Q4
- Suggère les auditeurs en fonction des rôles disponibles dans le plant

Vous pouvez modifier manuellement : les dates de chaque trimestre, l'auditeur assigné à chaque session, la liste des contrôles inclus dans chaque trimestre.

**Étape 4 — Approbation**
- Révisez le récapitulatif du programme
- Cliquez sur **Approuver le programme**
- Le programme devient actif et visible à tous les rôles impliqués

#### Comment interpréter le plan suggéré

Le système priorise les domaines avec le plus d'écarts dans les trimestres initiaux (Q1 et Q3) pour laisser suffisamment de temps à la résolution avant d'éventuels audits de certification. Les domaines avec une bonne couverture sont assignés aux trimestres Q2 et Q4. Vérifiez que la distribution est viable en termes de charge de travail pour les auditeurs.

#### Comment modifier les dates et les auditeurs par trimestre

Depuis le détail du programme approuvé :
1. Cliquez sur l'icône de modification à côté du trimestre à mettre à jour
2. Modifiez la date de début/fin et l'auditeur assigné
3. Enregistrez — la modification est consignée dans le journal du programme

#### Comment approuver le programme

À la fin de l'étape 4 de l'assistant, le programme passe automatiquement à l'état "Approuvé". Le Compliance Officer reçoit une notification. Le programme est désormais visible aux auditeurs assignés.

---

### Exécution de l'Audit

[Écran : détail du trimestre d'audit]

#### Comment démarrer un audit depuis un trimestre

1. Depuis le programme approuvé, allez au trimestre souhaité
2. Cliquez sur **Démarrer l'audit** — le trimestre passe de "Planifié" à "En cours"
3. La liste de contrôle des contrôles à vérifier pour ce trimestre s'ouvre

#### Couverture échantillon vs complète — différences pratiques

- **Échantillon** : vous ne voyez que le sous-ensemble de contrôles sélectionnés par le système (25 % ou 50 % du total). Vous ne pouvez pas ajouter de contrôles non inclus dans l'échantillon
- **Complet** : vous voyez tous les contrôles du framework. Vous devez renseigner la preuve pour chacun avant de pouvoir clôturer l'audit

Dans les deux cas, la structure de la liste de contrôle est identique — la différence réside uniquement dans le nombre de contrôles à vérifier.

#### Comment remplir la liste de contrôle des contrôles

Pour chaque contrôle dans la liste de contrôle :
1. Cliquez sur le contrôle pour développer le détail
2. Vérifiez le statut déclaré et la preuve associée
3. Choisissez le **jugement de l'auditeur** : Confirmé / Non Conforme / Observation / Opportunité
4. Si le jugement est différent de "Confirmé", cliquez sur **Ajouter un finding** (voir ci-dessous)
5. Ajoutez d'éventuelles notes de l'auditeur dans le champ prévu à cet effet
6. Cliquez sur **Enregistrer le jugement**

#### Comment ajouter un finding

1. Depuis la fiche du contrôle, cliquez sur **Ajouter un finding**
2. Renseignez :
   - **Titre du finding**
   - **Description détaillée** : ce qui manque ou n'est pas conforme
   - **Type de finding** (voir tableau ci-dessous)
   - **Contrôle de référence**
   - **Preuve à l'appui** : optionnelle lors de l'ouverture, obligatoire pour Major NC

#### Types de findings et délais de réponse

| Type | Signification | Délai de réponse |
|------|--------------|-----------------|
| **Major NC** (Non-Conformité Majeure) | Exigence non satisfaite avec un impact significatif sur la conformité ou la sécurité | 30 jours |
| **Minor NC** (Non-Conformité Mineure) | Exigence partiellement non satisfaite, impact limité | 90 jours |
| **Observation** | Faiblesse potentielle qui n'est pas encore une non-conformité. À surveiller | 180 jours |
| **Opportunity** | Suggestion d'amélioration sans impact sur la conformité. Aucune échéance obligatoire | — |

Les délais de réponse sont calculés automatiquement à partir de la date d'ouverture du finding sur la base de ces politiques. Pour Major NC, un cycle PDCA est également créé automatiquement.

#### Comment clôturer un finding

1. Depuis la fiche du finding, après avoir adopté les actions correctives, cliquez sur **Proposer la clôture**
2. Chargez la **preuve de clôture** (obligatoire pour Major NC et Minor NC)
3. Saisissez le **commentaire de clôture** : décrivez les actions entreprises
4. Le finding passe à l'état "En vérification"
5. L'auditeur responsable vérifie la preuve et clique sur **Confirmer la clôture** ou **Rouvrir le finding** avec un commentaire

#### Comment télécharger le rapport d'audit

Depuis l'audit en cours ou clôturé :
1. Cliquez sur le bouton **Rapport** (icône PDF) en haut à droite de la page d'audit
2. Choisissez la langue du rapport
3. Le système génère un PDF avec : récapitulatif de la couverture, liste des findings par type, état de clôture, tendance par rapport à l'audit précédent
4. Le PDF est disponible immédiatement pour le téléchargement

---

### Annuler un audit

[Écran : bouton d'annulation d'audit]

#### Quand utiliser "Annuler" vs suppression

- Utilisez **Annuler** lorsqu'un audit planifié ne sera pas exécuté mais que vous souhaitez conserver la trace de la planification initiale (ex. changement de date, changement de périmètre, urgence d'entreprise)
- La **suppression** n'est pas disponible pour les audits en état "En cours" ou "Clôturé" — utilisez toujours "Annuler" pour les audits lancés

#### Comment annuler

1. Depuis la liste des audits, cliquez sur le bouton **Annuler** (icône X) sur la ligne de l'audit
2. Une boîte de dialogue s'ouvre demandant la **justification de l'annulation** (obligatoire, minimum 10 caractères)
3. Saisissez la justification (ex. "Reporté au T3 en raison de la disponibilité de l'auditeur")
4. Cliquez sur **Confirmer l'annulation**

#### Que se passe-t-il avec les findings ouverts

Lorsque vous annulez un audit qui a déjà des findings ouverts :
- Les findings sont **automatiquement clôturés** avec le statut "Annulé" et la justification de l'annulation
- Les cycles PDCA associés aux findings restent ouverts et doivent être gérés manuellement
- Le programme annuel n'est pas modifié — le trimestre est marqué comme "Annulé" avec trace de la justification

L'audit annulé n'est jamais supprimé physiquement — il reste dans l'archive avec le statut "Annulé" pour garantir la traçabilité.

---

## 13. Fournisseurs (M14)

[Écran : liste des fournisseurs]

### Comment enregistrer un fournisseur

1. Allez sur **Gouvernance → Fournisseurs → Nouveau fournisseur**
2. Renseignez :
   - **Raison sociale** et **Numéro de TVA**
   - **Catégorie** : IT, OT, Services Professionnels, Logistique, autre
   - **Criticité** : importance pour la continuité opérationnelle (1–5)
   - **Référent interne** : sélectionnez le rôle responsable de la gestion du fournisseur
   - **Référent fournisseur** : nom et email du contact chez le fournisseur
   - **Traitement des données** : indicateur si le fournisseur traite des données personnelles (implique des obligations RGPD supplémentaires)
3. Cliquez sur **Enregistrer**

### Évaluation : planifiée → en cours → complétée → approuvée/refusée

Chaque fournisseur critique doit être périodiquement évalué via une évaluation. Le flux est :

1. **Planifiée** : l'évaluation est créée avec une date cible. Le référent interne reçoit une tâche
2. **En cours** : l'évaluation est lancée. Le fournisseur reçoit (par email ou accès temporaire) le questionnaire à remplir
3. **Complétée** : le fournisseur a répondu à toutes les questions. Le référent interne reçoit le questionnaire pour révision
4. **Approuvée** ou **Refusée** : le Compliance Officer ou le Risk Manager exprime le jugement final (voir ci-dessous)

### Score gouvernance, sécurité, BCP

Le questionnaire d'évaluation évalue le fournisseur sur 3 dimensions :

| Dimension | Ce qu'elle évalue |
|-----------|------------------|
| **Gouvernance** | Structure organisationnelle pour la sécurité, politiques internes, responsabilités définies, audits internes |
| **Sécurité** | Contrôles techniques mis en œuvre, gestion des vulnérabilités, réponse aux incidents, certifications (ISO 27001, TISAX) |
| **BCP** | Plans de continuité opérationnelle, RTO/RPO déclarés, tests de continuité effectués, redondances d'infrastructure |

Chaque dimension produit un score 0-100. Le score global est la moyenne pondérée des trois dimensions.

### Approbation et refus avec notes obligatoires

**Approbation :**
1. Depuis la fiche de l'évaluation complétée, cliquez sur **Approuver le fournisseur**
2. Saisissez les **notes d'approbation** (obligatoires — ex. "Fournisseur certifié ISO 27001, score adéquat. Prochaine révision dans 12 mois")
3. Définissez la **date d'expiration de l'approbation** (typiquement 12 mois)
4. Cliquez sur **Confirmer l'approbation**

**Refus :**
1. Depuis la fiche de l'évaluation complétée, cliquez sur **Refuser le fournisseur**
2. Saisissez les **notes de refus** (obligatoires — doit être une justification détaillée motivant la décision)
3. Cliquez sur **Confirmer le refus**

Le refus génère une tâche au référent interne pour gérer la transition (remplacement du fournisseur ou plan de remédiation).

---

## 14. Formation (M15)

[Écran : plan de formation personnel]

### Comment voir ses cours obligatoires

1. Allez sur **Gouvernance → Formation → Mon plan**
2. Vous trouvez la liste des cours obligatoires pour votre rôle et plant, avec :
   - Nom du cours
   - Statut : À compléter / En cours / Terminé / Expiré
   - Date d'échéance (ou date de completion si déjà fait)
   - Type : en ligne (KnowBe4), présentiel, documentaire

### Completion et échéances

- Cliquez sur **Démarrer le cours** pour les cours en ligne pour ouvrir directement le module sur KnowBe4
- Les completions sont synchronisées automatiquement chaque nuit — si vous avez terminé un cours sur KnowBe4 et qu'il n'apparaît pas encore comme terminé dans la GRC Platform, attendez le lendemain ou contactez le Compliance Officer
- Un cours expiré (terminé mais à refaire périodiquement) apparaît avec un badge rouge et génère une tâche de renouvellement

### Analyse des écarts de compétences

Allez sur **Gouvernance → Formation → Analyse des écarts**. La page affiche :

- Les exigences de compétences prévues pour chaque rôle et plant
- Les compétences effectivement certifiées (cours terminés, attestations chargées)
- Les écarts mis en évidence : compétences requises mais pas encore couvertes par un cours terminé

Le Compliance Officer peut utiliser cette vue pour planifier les sessions de formation et combler les écarts prioritaires.

### Synchronisation KnowBe4 (admin uniquement)

Allez sur **Paramètres → Intégrations → KnowBe4** :

1. Configurez la clé API KnowBe4
2. Cliquez sur **Synchroniser maintenant** pour forcer la synchronisation immédiate des completions
3. Vérifiez le journal de la dernière synchronisation pour identifier d'éventuelles erreurs

La synchronisation automatique a lieu chaque nuit à 02h00.

---

## 15. Continuité d'Activité (M16)

[Écran : liste des plans BCP]

### Comment créer un plan BCP

1. Allez sur **Gouvernance → BCP → Nouveau plan**
2. Renseignez :
   - **Nom du plan** (ex. "Plan BCP — Ligne de production B — Établissement Sud")
   - **Périmètre** : processus critiques couverts par le plan (sélectionnez depuis la BIA)
   - **Propriétaire du plan** : responsable de la maintenance
   - **RTO objectif** et **RPO objectif** : les valeurs que le plan doit garantir
3. Cliquez sur **Enregistrer le brouillon**

### Connexion avec RTO/RPO de la BIA

Dans la section **Processus couverts** du plan BCP, pour chaque processus sélectionné, la comparaison est affichée entre :

- **RTO requis par la BIA** : le maximum tolérable déclaré dans le processus critique
- **RTO garanti par le BCP** : celui que le plan peut effectivement garantir

Si le BCP garantit un RTO supérieur à celui requis par la BIA, un avertissement orange apparaît demandant une révision. Le système ne bloque pas l'enregistrement mais requiert une justification explicite.

### Types de tests

Le plan doit être testé périodiquement. Les types de tests disponibles sont :

| Type | Description |
|------|-------------|
| **Tabletop** | Simulation sur papier/discussion. Participants en salle de réunion, aucun système réel impliqué |
| **Simulation** | Simulation partielle avec certains systèmes réels en mode test, sans interruption de la production |
| **Complet** | Test complet avec activation du plan sur des systèmes réels, sans impact sur la production normale |
| **Exercice** | Exercice non annoncé pour tester les temps de réponse réels de l'équipe |

Pour enregistrer un test : depuis la fiche du plan, cliquez sur **Nouveau test**, sélectionnez le type, la date, les participants et le résultat.

### Que se passe-t-il si le test échoue (cycle PDCA automatique)

Si le test est enregistré avec le résultat **Échoué** ou **Partiellement réussi** :

1. Un cycle PDCA est automatiquement créé avec la phase de départ PLAN
2. Le PDCA est assigné au propriétaire du plan BCP
3. Le propriétaire doit rédiger le plan d'action dans les 30 jours
4. Le plan BCP reste à l'état "À mettre à jour" jusqu'à ce que le PDCA soit clôturé positivement

### Expiration des plans et alertes

Chaque plan BCP a une date de révision obligatoire (typiquement annuelle). Lorsque la date approche :

- **30 jours avant** : notification email au propriétaire du plan
- **À l'échéance** : le plan passe à l'état "Expiré" avec un badge rouge. Une tâche de révision est automatiquement créée
- Si le plan expiré couvre des processus avec MTPD < 48 heures, une notification d'escalade est envoyée au Plant Manager

---

## 16. Planning d'Activités (Échéancier)

[Écran : échéancier avec vue calendrier]

### Comment lire le calendrier des échéances

Allez sur **Opérations → Échéancier**. La page affiche toutes les échéances dans la période sélectionnée (par défaut : 30 prochains jours), triées par date. Pour chaque échéance, vous voyez :

- **Type** d'échéance (document, preuve, tâche, évaluation, plan BCP, cours de formation, etc.)
- **Nom** de l'élément
- **Date** d'échéance
- **Responsable** (owner)
- **Statut** avec badge coloré (voir ci-dessous)

Vous pouvez passer de la vue liste à la vue calendrier en cliquant sur les icônes en haut à droite.

### Filtres par type et période

Dans la barre de filtres au-dessus de la liste, vous pouvez filtrer par :

- **Type** : sélectionnez un ou plusieurs types d'échéance (documents, preuves, tâches, évaluations, BCP, formation)
- **Période** : cette semaine / ce mois / 30 prochains jours / 90 prochains jours / plage personnalisée
- **Responsable** : filtre par le responsable de l'échéance
- **Plant** : filtre par établissement (si vous avez un accès multi-plant)

### Couleurs des badges

| Couleur | Signification |
|---------|--------------|
| **Vert** | Valide — aucune action requise, échéance lointaine |
| **Jaune** | En cours d'expiration — moins de 30 jours restants. Vérifiez et planifiez l'action |
| **Rouge** | Expiré — la date est déjà passée. Action urgente requise |

### Comment naviguer directement vers l'élément depuis l'échéance

Cliquez sur le nom d'une échéance dans la liste pour ouvrir directement la fiche de l'élément concerné (ex. en cliquant sur une preuve dont l'échéance approche, vous ouvrez la fiche de la preuve). Il n'est pas nécessaire de naviguer manuellement à travers les menus.

---

## 17. Documents Obligatoires

[Écran : page des documents obligatoires]

### Comment lier un document à une exigence normative

Les documents obligatoires sont ceux explicitement requis par un framework normatif (ex. ISO 27001 requiert une "Politique de sécurité de l'information"). Pour lier un document existant à une exigence :

1. Allez sur **Compliance → Documents obligatoires**
2. Trouvez l'exigence normative dans la liste
3. Cliquez sur **Lier le document** à côté de l'exigence
4. Recherchez et sélectionnez le document approprié dans la bibliothèque de documents (M07)
5. Enregistrez

Si le document n'existe pas encore, cliquez sur **Créer le document** pour lancer le workflow de création dans M07.

### Feu de signalisation de statut

Pour chaque exigence normative dans la liste, le feu de signalisation affiche l'état du document associé :

| Couleur du feu | Signification |
|---------------|--------------|
| **Vert** | Document présent, approuvé et valide (non expiré) |
| **Jaune** | Document présent et approuvé mais qui expire dans 30 jours — planifiez la révision |
| **Rouge** | Document présent mais expiré — mise à jour urgente requise |
| **Gris** | Document manquant — aucun document lié à cette exigence |

Les exigences avec un feu gris impactent négativement le KPI de conformité du framework.

### Comment ajouter un document manquant

Lorsque le feu est gris (document manquant) :

1. Cliquez sur l'exigence
2. Cliquez sur **Créer et lier un document** pour lancer l'assistant de création
3. Le système pré-remplit automatiquement le titre suggéré, le framework de référence et les champs normatifs du document
4. Complétez les champs manquants (propriétaire, réviseur, approbateur) et chargez le fichier
5. Le document part en état Brouillon et suit le workflow d'approbation normal (M07)
6. Une fois approuvé, le feu passe automatiquement au vert

---

## 18. Notifications Email

### Quand arrivent les notifications

La plateforme envoie des notifications email automatiques en fonction des événements. Les principales :

| Événement | Destinataires |
|-----------|--------------|
| Tâche assignée | Propriétaire du rôle destinataire |
| Tâche qui expire (7 jours) | Propriétaire du rôle + responsable |
| Tâche expirée | Propriétaire + responsable + Compliance Officer (après 14 jours) |
| Finding d'audit ouvert | Responsable du domaine audité |
| Finding qui expire (30/90/180 jours) | Propriétaire du finding |
| Audit imminent (7 jours) | Auditeur + Compliance Officer |
| Incident NIS2 — minuterie T+24h | RSSI + Compliance Officer |
| Incident NIS2 — minuterie T+72h | RSSI + Compliance Officer + Plant Manager |
| Risque avec score > 14 | Risk Manager + Plant Manager |
| Document qui expire (30 jours) | Propriétaire du document |
| Preuve expirée | Propriétaire du contrôle associé |
| Rôle obligatoire vacant | Compliance Officer + Plant Manager |
| Évaluation fournisseur qui expire (30 jours) | Référent interne |

Certaines notifications sont obligatoires et ne peuvent pas être désactivées (ex. minuteries NIS2, escalade de tâches critiques, risques rouges).

### Comment elles varient selon le profil attribué au rôle

Les notifications envoyées pour un rôle dépendent du **profil de notification** attribué à ce rôle (configuré dans Paramètres). Un rôle avec le profil "Essentiel" reçoit uniquement les notifications obligatoires et les échéances critiques. Un rôle avec le profil "Complet" reçoit également les digests périodiques et les notifications sur les modules de référence.

### Comment configurer les préférences (admin uniquement)

Allez sur **Paramètres → Profils de notification** :

1. Sélectionnez le profil à modifier ou cliquez sur **Nouveau profil**
2. Configurez pour chaque type d'événement : actif / inactif, fréquence (immédiate / digest quotidien / digest hebdomadaire)
3. Attribuez le profil aux rôles qui doivent l'utiliser
4. Enregistrez

La configuration s'applique immédiatement. Les modifications ne sont pas rétroactives sur les notifications déjà envoyées.

---

## 19. Gouvernance (M00)

[Écran : organigramme des rôles normatifs]

### Comment assigner un rôle normatif

Les rôles normatifs sont des postes requis par les frameworks (ex. RSSI, DPO, Risk Owner, Asset Owner). Pour assigner un titulaire :

1. Allez sur **Gouvernance → Organigramme**
2. Trouvez le rôle à assigner (utilisez éventuellement le filtre par framework ou plant)
3. Cliquez sur **Assigner un titulaire**
4. Sélectionnez l'utilisateur dans la liste
5. Définissez :
   - **Date de début** : à partir de quand l'assignation prend effet
   - **Date d'expiration** (facultative) : utile pour les missions temporaires ou les rotations programmées
6. Cliquez sur **Confirmer l'assignation**

L'assignation est enregistrée dans l'audit trail. L'utilisateur reçoit une notification email avec les responsabilités du rôle.

### Comment remplacer un titulaire (succession)

Si un titulaire part à la retraite, change de fonction ou quitte l'entreprise, utilisez le mécanisme de succession :

1. Depuis la fiche du rôle, cliquez sur **Gérer la succession**
2. Sélectionnez le nouveau titulaire
3. Définissez la **date de transition**
4. Le système gère automatiquement le chevauchement : jusqu'à la date de transition, l'ancien titulaire reste actif ; à partir du lendemain, le nouveau prend le relais
5. Cliquez sur **Confirmer la succession**

L'ancien titulaire reçoit une notification de fin de mission. Le nouveau titulaire reçoit une notification de début de mission avec la liste des responsabilités.

### Comment mettre fin à un rôle

Si un poste n'est plus requis (ex. changement de périmètre normatif) :

1. Depuis la fiche du rôle, cliquez sur **Mettre fin au rôle**
2. Saisissez la **justification** (obligatoire — ex. "Rôle supprimé après révision du périmètre TISAX 2026")
3. Définissez la **date de fin**
4. Si des tâches ouvertes sont assignées à ce rôle, le système vous demande comment les gérer (réassigner à un autre rôle ou laisser ouvertes)
5. Cliquez sur **Confirmer**

### Alertes rôles qui expirent et rôles obligatoires vacants

**Rôles qui expirent** : si une assignation a une date d'expiration, 30 jours avant, le système envoie une notification au Compliance Officer et au Plant Manager pour planifier le renouvellement ou la succession.

**Rôles obligatoires vacants** : certains rôles sont marqués comme obligatoires dans le framework (ex. RSSI pour ISO 27001). Si un rôle obligatoire n'a pas de titulaire actif :
- Un bandeau rouge apparaît dans le tableau de bord
- Le KPI de conformité est pénalisé
- Une tâche urgente d'assignation est générée

---

## 20. Paramètres (Admin uniquement)

[Écran : page des paramètres admin]

Cette section est accessible uniquement aux utilisateurs avec le rôle Administrateur système ou Super Admin.

### Configuration email SMTP

1. Allez sur **Paramètres → Email → Configuration SMTP**
2. Renseignez :
   - **Hôte SMTP** (ex. smtp.azienda.com)
   - **Port** (typiquement 587 pour STARTTLS ou 465 pour SSL)
   - **Utilisateur** et **Mot de passe** — le mot de passe est chiffré avec AES-256 (FERNET) avant d'être enregistré
   - **Expéditeur par défaut** (ex. noreply@grc.azienda.com)
   - **TLS/SSL** : sélectionnez le type de chiffrement
3. Cliquez sur **Enregistrer la configuration**

### Test de connexion email

Après avoir configuré le SMTP :

1. Sur la même page, cliquez sur **Envoyer un email de test**
2. Saisissez une adresse email destinataire pour le test
3. Cliquez sur **Envoyer**
4. Vérifiez la réception. Si l'email n'arrive pas dans les 2 minutes, cliquez sur **Afficher le journal** pour voir l'éventuelle erreur SMTP

### Profils de notification par rôle

Allez sur **Paramètres → Notifications → Profils** :

1. Les profils prédéfinis sont : Essentiel, Standard, Complet, Silencieux
2. Pour créer un profil personnalisé, cliquez sur **Nouveau profil**
3. Pour chaque type de notification, définissez : actif/inactif et fréquence d'envoi
4. Attribuez le profil aux rôles via **Paramètres → Rôles → sélectionnez le rôle → Profil de notification**

### Politiques d'échéances (23 types configurables)

Allez sur **Paramètres → Politiques → Échéances**. Vous pouvez configurer les délais de préavis et les échéances par défaut pour 23 types d'éléments, notamment :

- Preuves par type (journaux : 30 j, analyses : 90 j, certificats : 365 j)
- Documents par type (politique : 365 j, procédure : 730 j)
- Findings par sévérité (Major NC : 30 j, Minor NC : 90 j, Observation : 180 j)
- Évaluations fournisseurs (12 mois par défaut)
- Plans BCP (12 mois par défaut)
- Révision des risques (90 j pour les risques rouges, 180 j pour les risques jaunes)

La modification de ces valeurs met à jour les calculs pour tous les éléments futurs. Les éléments existants conservent les échéances calculées au moment de leur création.

---

## Rôles et ce que vous pouvez faire

### Compliance Officer

Vous avez un accès complet à tous les modules pour tous les plants dans votre périmètre. Vous êtes responsable de :

- Maintenir à jour la bibliothèque de contrôles (M03)
- Coordonner le workflow documentaire (M07)
- Surveiller les tâches et les échéances de toute l'équipe (M08)
- Gérer les incidents NIS2 et les notifications ACN (M09)
- Préparer la documentation pour les audits (M17)
- Générer des rapports pour la direction (M18)

### Risk Manager

Vous avez un accès complet aux modules de risk. Vous êtes responsable de :

- Superviser le risk assessment IT et OT (M06)
- Valider la BIA et les valeurs MTPD/RTO/RPO (M05)
- Lancer et surveiller les cycles PDCA (M11)
- Recevoir des alertes sur les risques avec score > 14

### Plant Manager

Vous avez accès à votre plant. Vous êtes responsable de :

- Approuver les documents de niveau direction (M07)
- Recevoir les escalades sur les tâches critiques en retard
- Valider les décisions de traitement des risques (M06)
- Participer à et approuver la revue de direction (M13)

### Plant Security Officer

Vous avez un accès opérationnel à votre plant. Vous êtes responsable de :

- Mettre à jour l'état des contrôles (M03)
- Charger des preuves (M07)
- Remplir les risk assessments IT et OT (M06)
- Ouvrir et gérer les incidents (M09)
- Compléter les tâches assignées (M08)

### Auditeur Externe

Vous avez un accès en lecture seule avec un jeton temporaire. Vous pouvez :

- Consulter les contrôles et leur état (M03)
- Télécharger les documents et les preuves (M07)
- Exporter le pack de preuves pour votre audit (M17)
- Chacune de vos actions est enregistrée dans l'audit trail

Le jeton a une date d'expiration : vous trouverez la date d'expiration en haut de l'interface. Contactez le Compliance Officer si vous avez besoin d'une prolongation.

---

## AI Engine — suggestions IA (M20)

> Le module IA n'est activé que si votre administrateur a activé cette fonction pour votre plant.

### Comment ça fonctionne

Lorsque le module IA est actif, vous verrez un bloc **Suggestion IA** dans certains modules — incidents, assets, documents, tâches. Le système analyse le contexte et propose :

- Une **classification suggérée** (ex. sévérité de l'incident, criticité de l'asset)
- Un **brouillon de texte** (ex. notification ACN, politique, RCA)
- Une **alerte proactive** (ex. tâche à haut risque de glissement)

### Ce que vous devez faire

La suggestion IA n'a aucun effet tant que vous ne la **confirmez pas explicitement**. Vous pouvez :

- **Accepter** la suggestion telle quelle — cliquez sur **Utiliser cette suggestion**
- **Modifier** le texte puis cliquer sur **Utiliser la version modifiée** — votre version remplace celle de l'IA
- **Ignorer** la suggestion et procéder manuellement — le bloc se ferme sans effet

> Chaque interaction (suggestion reçue, texte final adopté) est enregistrée dans l'audit trail pour garantir la traçabilité des décisions. L'IA ne prend jamais de décisions de manière autonome.

---

## Reporting et export (M18)

### Tableau de bord reporting

Allez sur **Audit → Reporting**. Vous trouverez trois niveaux de tableau de bord :

- **Opérationnel** : état des tâches, contrôles par framework et plant, échéances
- **Risk** : carte de chaleur agrégée, top 10 des risques ouverts
- **Executive** : conformité %, tendance de maturité PDCA, préparation à l'audit

### Générer un rapport PDF

1. Sélectionnez le type de rapport (écart TISAX, conformité NIS2, SOA ISO 27001, BIA executive)
2. Choisissez le plant et la période
3. Sélectionnez la langue du rapport
4. Cliquez sur **Générer** — le PDF est signé avec horodatage et hash
5. Le rapport est disponible pour le téléchargement dans la section **Rapports générés**

Tous les rapports générés sont enregistrés dans l'audit trail.

---

## Annexe : Questions fréquentes

**Je ne trouve pas un contrôle qui devrait être dans mon framework.**
Vérifiez que vous avez sélectionné le plant correct dans le sélecteur en haut. Si le framework est actif pour ce plant mais que le contrôle n'apparaît pas, contactez le Compliance Officer — il est possible qu'il n'ait pas été généré lors de l'activation du framework.

**J'ai chargé une preuve mais le contrôle affiche toujours "écart".**
Vérifiez que la preuve est liée au bon contrôle (fiche de la preuve → section "Contrôles couverts") et que la date d'expiration n'est pas déjà passée.

**La minuterie NIS2 a démarré mais l'incident n'est pas vraiment un incident NIS2.**
Le RSSI dispose de 30 minutes pour exclure l'obligation de notification. Si vous êtes le RSSI, ouvrez la fiche de l'incident et cliquez sur **Exclure l'obligation NIS2** en saisissant la justification. Les minuteries s'arrêtent et la décision est enregistrée dans l'audit trail.

**J'ai complété une tâche mais elle continue d'apparaître comme ouverte.**
Certaines tâches se ferment automatiquement lorsque l'action dans le module d'origine est complétée. Si la tâche est manuelle, vous devez la fermer explicitement depuis la fiche de la tâche → **Marquer comme terminée**.

**Un document que j'avais approuvé affiche maintenant "en révision".**
Un déclencheur de révision extraordinaire a été activé — probablement lié à un incident, un finding d'audit ou un changement normatif. Consultez les notes dans la fiche du document pour en comprendre la raison.

**Je n'arrive pas à définir un contrôle comme N/A.**
Pour les contrôles TISAX L3, l'état N/A nécessite la signature d'au moins deux rôles (double verrou). Si vous êtes le premier à approuver, le contrôle reste en attente de la deuxième signature. Si vous êtes le seul propriétaire, contactez le RSSI pour la co-signature.

**La suggestion IA n'apparaît plus.**
Le module IA a peut-être été désactivé par l'administrateur pour votre plant, ou la fonction spécifique n'est pas active. Contactez le Compliance Officer ou l'Administrateur Système.

**J'ai annulé un audit par erreur. Puis-je le restaurer ?**
Non, l'annulation est irréversible. Vous pouvez cependant créer un nouvel audit pour le même trimestre et recréer les findings éventuellement perdus. Contactez le Compliance Officer qui peut consulter les findings annulés dans l'archive pour récupérer les informations.

**Le score de mon risque a changé sans que j'aie fait quoi que ce soit.**
Le score résiduel est recalculé automatiquement lorsque l'état des contrôles associés change. Si une preuve a expiré, le contrôle revient à "partiel" et cela peut augmenter le risque résiduel. Vérifiez les contrôles associés au risque et mettez à jour les preuves.

**Je ne reçois pas les notifications email.**
Vérifiez d'abord le dossier spam. Si les emails n'arrivent pas du tout, contactez l'administrateur système pour vérifier la configuration SMTP et le profil de notification attribué à votre rôle.

**Comment puis-je voir l'historique des modifications sur un asset ou un document ?**
Chaque fiche dispose d'une section **Audit trail** ou **Historique des modifications** en bas. Cliquez dessus pour voir toutes les actions enregistrées avec la date, l'utilisateur et le détail de la modification.

**Le programme d'audit affiche l'état "À mettre à jour". Que dois-je faire ?**
L'état "À mettre à jour" indique que le programme a été créé mais que certaines informations (ex. auditeur non assigné à un trimestre, dates manquantes) nécessitent d'être complétées avant que le programme puisse être approuvé. Ouvrez le programme et recherchez les champs mis en évidence en jaune.

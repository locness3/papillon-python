![image](https://user-images.githubusercontent.com/32978709/205500141-cf7be394-9929-4c2c-90a3-977cffc3f16f.png)

## Pourquoi faire ?
Auparavant, [Papillon](https://github.com/ecnivtwelve/Papillon) utilisait [@Litarvan/pronote-api](https://github.com/Litarvan/pronote-api), mais cette API non maintenue depuis Avril 2021 commence à poser de plus en plus de problèmes à cause de son retard, et en plus est compliquée à héberger. Voila pourquoi je transitionne vers [@bain3/pronotepy](https://github.com/bain3/pronotepy), qui est encore maintenu et bien plus complet en fonctionnalités.

Le but est de l'intégrer le plus vite possible dans [Papillon](https://github.com/ecnivtwelve/Papillon), et d'arrêter complètement l'ancien backend [node-pronote](https://github.com/ecnivtwelve/node-pronote) pour attribuer plus de ressources à papillon-python.

## Roadmap
- [x] Données de l'utilisateur
- [x] Emploi du temps
- [x] Travail à faire
- [x] Notes
- [x] Compétences
- [x] Actualités
- [x] Absences et retards
- [x] Messagerie
  - [x] Envoi de message

## Requêtes
Un client doit faire la requête initiale `POST /generatetoken` avec le body suivant :
| Paramètre | Utilité | Exemple |
|--|--|--|
| `url: str(url)` | URL vers l'instance pronote **(avec le eleve.html)** | `https://0152054e.index-education.net/pronote/eleve.html` |
| `username: str` | Nom d'utilisateur **PRONOTE** | `l.martin` |
| `password: str` | Mot de passe en clair | `azertyuiop12345` |
| `ent: str(ent)` | Nom de l'ENT tel que listé [ici](https://github.com/bain3/pronotepy/blob/master/pronotepy/ent/ent.py) | `ac_rennes` |

Le client doit ensuite garder le token généré. Si il ya eu un délai d'au moins 5 minutes entre deux interactions, le client doit regénérer un nouveau token.

Ensuite chaque appel à une fonction de l'API doit avoir le paramètre `token` défini.
Voici la liste des URLs pour obtenir des données :

| URL | Utilité | Paramètres |
|--|--|--|
| `/user` | Obtient les infos sur l'utilisateur (nom, classe...) + les périodes de l'année |  |
| `/timetable` | Affiche l'emploi du temps sur une date donnée | `dateString: str` : date au format **`année-mois-jour`** |
| `/homework` | Affiche les devoirs entre deux dates données | `dateFrom: str` : date de début au format **`année-mois-jour`**, et `dateTo: str` : date de fin au même format |
| `/grades` | Affiche les notes |  |
| `/evaluations` | Affiche les évaluations par compétences |  |
| `/absences` | Affiche les absences |  |
| `/punishments` | Affiche les punitions |  |
| `/news` | Affiche les actualités |  |
| `/discussions` | Affiche les messages |  |
| `/menu` | Affiche les menus entre deux dates données | `dateFrom: str` : date de début au format **`année-mois-jour`**, et `dateTo: str` : date de fin au même format |
| `/recipients` | Liste toutes les personnes que l'utilisateur peut contacter par message |  |

Voici la liste des URL qui éffectuent une simple fonction :
| URL | Utilité | Paramètres | Réponse
|--|--|--|--|
| `/info` | Envoie des informations sur l'API comme les ENTs et la version |  |  |
| `/export/ical` | Exporte le calendrier en iCal |  | *(l'url du fichier iCal)* |
| `/homework/changeState` | Change l'état d'un devoir (fait/non fait) | `dateFrom: str` : date de début au format **`année-mois-jour`**, et `dateTo: str` date de fin au même format, et `homeworkId: str` l'id du devoir à changer | *(état du devoir changé)* |
| `/discussion/delete` | Supprime la discussion | `discussionId: str` : Id de la discussion | `ok` si aucun problème |
| `/discussion/readState` | Change l'état de lecture d'une discussion | `discussionId: str` : Id de la discussion | `ok` si aucun problème |
| `/discussion/reply` | Répond à une discussion | `discussionId: str` : Id de la discussion, et `content: str` : Contenu du message | `ok` si aucun problème |
| `/discussion/create` | Crée une discussion | `recipientId: str` : Id du destinataire, et `content: str` : Contenu du message | `ok` si aucun problème |

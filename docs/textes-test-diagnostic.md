# Textes de test pour le diagnostic

Collez ces textes dans la page Diagnostic pour voir quel mode est recommandé.

---

## 1. Regex recommandé

Texte structuré, pas de noms dans le texte libre. Les regex suffisent.

```
Objet : facture n° 2024-4567.
Email de contact : service.client@entreprise.fr
Téléphone : 01 23 45 67 89
Montant : 150 euros TTC.
Merci de bien vouloir régulariser la situation.
Cordialement.
```

---

## 2. Regex + fort recommandé

Texte avec des salutations et des titres — le mode fort les attrape.

```
Bonjour Marie,

Suite à notre entretien téléphonique avec Monsieur Dupont, je vous confirme la réception de votre dossier.
Mme Lambert sera votre interlocutrice pour la suite.
Veuillez contacter notre service au 01 23 45 67 89 ou par email : contact@service.fr

Cordialement,
Sophie
```

---

## 3. Regex + fort + tech recommandé

Texte avec des données techniques (IP, MAC, JWT).

```
Incident technique signalé par l'utilisateur jean.martin@interne.fr le 15/03/2024.
Terminal concerné : poste PC-0042, adresse MAC AA:BB:CC:DD:EE:FF.
Connexion depuis l'adresse IP 192.168.12.45 via le VPN.
Token de session : eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U
Clé API compromise : sk_test_EXEMPLE_CLE_FICTIVE_00000000
Aucune donnée personnelle exposée selon l'analyse préliminaire.
```

---

## 4. NER recommandé

Texte libre avec des noms ambigus que seul le NER comprend par le contexte.

```
Rose Martin a déposé une réclamation hier. Elle explique que son voisin Pierre
lui a envoyé un courrier menaçant. La médiatrice, Alexandra Beaumont, a été
saisie. Le dossier est suivi par Maître Jean-Claude de La Vega du cabinet
juridique de Toulouse. L'audience est prévue pour le mois prochain.
```

---

## 5. Hybrid recommandé

Texte mixte : données structurées (email, tel) + noms dans le texte libre.

```
Réclamation de Jean-Pierre Lefebvre, email jp.lefebvre@orange.fr, tél 06 78 90 12 34.

Monsieur Lefebvre signale que la conseillère Nadia lui a promis un tarif
promotionnel qui n'apparaît pas sur sa facture. Il a également contacté
le service client où Karim lui a confirmé l'erreur. Son épouse Fatima
a envoyé un courrier recommandé au siège de Bouygues Telecom.

Code postal : 93100. SIRET du plaignant : 732 829 320 00074.
```

---

## 6. Hybrid + fort + tech recommandé

Texte complet couvrant tous les types de PII.

```
Bonjour Madame Nathalie GARCIA-LOPEZ, je me permets de vous écrire concernant
le dossier de M. Jean-Pierre de La Fontaine, né le 12/04/1985, habitant au
24 rue Victor Hugo, 92130 Issy-les-Moulineaux. Son email est
jean-pierre.delafontaine@gmail.com et son téléphone est 06 12 34 56 78.
Il est joignable aussi au +33 6 98 76 54 32. Monsieur de La Fontaine a signalé
un problème avec sa facture Orange. Alexandra, sa conseillère chez Sosh, lui a
proposé un tarif à 10,95 euros par mois. Données bancaires : IBAN FR76 3000
6000 0112 3456 7890 189, carte 4532 0151 1283 0366 (CVV 456), numéro de
sécurité sociale 1 85 04 75 123 456 78, SIRET 732 829 320 00074.
IP: 192.168.1.42, MAC: AA:BB:CC:DD:EE:FF, plaque AB-123-CD.
Référence dossier n° 2024-78901, page 42, montant 300 euros.
Cordialement, Pierre Martin pierre.martin@example.com
```

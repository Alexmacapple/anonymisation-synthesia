# Mémo déploiement — anonymisation-synthesia

Fiche interne pour le workflow de lancement et l'exposition réseau.

---

## Lancer les applications en local

### Anonymisation-synthesia (port 8091)

```bash
cd /Users/alex/Sites/anonymisation-synthesia
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
```

- Interface : http://127.0.0.1:8091
- Swagger : http://127.0.0.1:8091/docs

### Pseudonymus (port 8090)

```bash
cd /Users/alex/Sites/pseudonymus
python3 serveur.py --port 8090
```

- Interface : http://127.0.0.1:8090

---

## Architecture réseau

```
Internet
    │
    ▼
alexmacpple.duckdns.org (IP publique)
    │
    ▼
Box internet (port forwarding)
    │  443 externe → 8443 Mac Studio
    │   80 externe → 8080 Mac Studio (optionnel)
    ▼
Mac Studio (192.168.1.18)
    │
    ▼
Apache (reverse proxy)
    │  /etc/apache2/other/reverse-proxy-apps.conf
    │
    ├── /pseudonymus/    → localhost:8090
    └── /anonymisation/  → localhost:8091
```

---

## Configuration Apache

### Fichiers

| Fichier | Rôle |
|---------|------|
| `/etc/apache2/httpd.conf` | Config principale (Listen, modules) |
| `/etc/apache2/other/reverse-proxy-apps.conf` | Reverse proxy (notre config) |
| `/etc/letsencrypt/live/alexmacpple.duckdns.org/` | Certificat SSL |
| `/var/log/apache2/error_log` | Logs d'erreur |
| `/var/log/apache2/reverse-proxy-error.log` | Logs du reverse proxy |

### Commandes Apache

```bash
# Vérifier la syntaxe
sudo apachectl configtest

# Démarrer / arrêter / redémarrer
sudo apachectl start
sudo apachectl stop
sudo apachectl restart
sudo apachectl graceful    # redémarrage sans couper les connexions

# Voir les ports qui écoutent
sudo lsof -i:80 -i:443 -i:8080 -i:8443 -i:8090 -i:8091 | grep LISTEN

# Voir les modules chargés
apachectl -M
```

### Port Apache actuel

Apache écoute sur `8443` (pas 443 standard car Tailscale occupe le 443).

```
Listen 8443    ← dans httpd.conf
```

Le port forwarding de la box fait : **443 externe → 8443 interne**.

---

## Tailscale

Tailscale occupe les ports 80 et 443 sur le Mac Studio. C'est pourquoi Apache utilise 8443.

```bash
# Voir ce que Tailscale sert
sudo tailscale serve status

# Libérer le port 443 (si besoin)
sudo tailscale serve reset

# Vérifier
sudo lsof -i:443 | grep LISTEN
```

**Attention** : `tailscale serve reset` libère le port mais désactive le serveur HTTPS Tailscale. Les URLs tailnet ne fonctionneront plus.

---

## Certificat SSL (Let's Encrypt)

```bash
# Vérifier le certificat
sudo certbot certificates

# Renouveler
sudo certbot renew

# Générer un nouveau certificat (si besoin)
sudo apachectl stop
sudo certbot certonly --standalone -d alexmacpple.duckdns.org
sudo apachectl start
```

Le certificat est dans `/etc/letsencrypt/live/alexmacpple.duckdns.org/`.

---

## Port forwarding (box internet)

Sur la Livebox (ou autre box) :

| Port externe | Port interne | Machine |
|-------------|-------------|---------|
| 443 | 8443 | 192.168.1.18 (Mac Studio) |
| 80 | 8080 | 192.168.1.18 (optionnel, redirige vers HTTPS) |

---

## Diagnostic

### Rien ne marche

```bash
# 1. Les apps Python tournent ?
curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8091/

# 2. Apache tourne ?
sudo apachectl configtest
sudo lsof -i:8443 | grep LISTEN

# 3. Le reverse proxy fonctionne ?
curl -sk https://localhost:8443/anonymisation/ -w "%{http_code}"
curl -sk https://localhost:8443/pseudonymus/ -w "%{http_code}"

# 4. Le port forwarding marche ?
curl -sk https://alexmacpple.duckdns.org/anonymisation/ -w "%{http_code}"
```

### Erreur "Cannot define multiple Listeners"

```bash
# Voir les Listen dupliqués
grep -n "^Listen" /etc/apache2/httpd.conf

# Supprimer les doublons
sudo sed -i '' '/^Listen 80$/d' /etc/apache2/httpd.conf
sudo sed -i '' '/^Listen 443$/d' /etc/apache2/httpd.conf
sudo apachectl configtest
```

### Erreur "Address already in use"

```bash
# Qui occupe le port ?
sudo lsof -i:PORT | grep LISTEN

# Tuer le processus
sudo kill -9 PID
```

### Erreur SSL "certificate verify failed"

Le certificat Let's Encrypt a expiré (90 jours). Renouveler :

```bash
sudo certbot renew
sudo apachectl graceful
```

---

## Workflow complet de démarrage

```bash
# 1. Lancer Pseudonymus
cd /Users/alex/Sites/pseudonymus && python3 serveur.py --port 8090 &

# 2. Lancer Anonymisation-synthesia
cd /Users/alex/Sites/anonymisation-synthesia && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091 &

# 3. Vérifier Apache
sudo apachectl configtest && sudo apachectl graceful

# 4. Tester en local
curl -sk https://localhost:8443/pseudonymus/ -w "%{http_code}"
curl -sk https://localhost:8443/anonymisation/ -w "%{http_code}"

# 5. Tester depuis l'extérieur
curl -sk https://alexmacpple.duckdns.org/pseudonymus/ -w "%{http_code}"
curl -sk https://alexmacpple.duckdns.org/anonymisation/ -w "%{http_code}"
```

---

## URLs finales

| Application | URL locale | URL publique |
|-------------|-----------|-------------|
| Anonymisation-synthesia | http://127.0.0.1:8091 | https://alexmacpple.duckdns.org/anonymisation/ |
| Pseudonymus | http://127.0.0.1:8090 | https://alexmacpple.duckdns.org/pseudonymus/ |
| Swagger API | http://127.0.0.1:8091/docs | https://alexmacpple.duckdns.org/anonymisation/docs |

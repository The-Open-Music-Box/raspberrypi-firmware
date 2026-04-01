# 🎵 The Open Music Box

> Un lecteur audio tangible pour enfants : autonomie, sans écran, et contrôlé par les parents. Les enfants explorent musique, histoires et podcasts en posant simplement des tags NFC sur le lecteur.

> [!IMPORTANT]
> **Ce projet (version Raspberry Pi) n'est plus activement développé.**
> Une nouvelle version basée sur **ESP32** est en cours de préparation et constitue désormais la priorité du projet.
> Cette version Raspberry Pi **reste fonctionnelle** et continuera de bénéficier d'un **support de maintenance**, mais elle ne fait plus l'objet de nouvelles fonctionnalités ou de mises à jour prioritaires.
> Suivez l'évolution du projet sur notre [page Facebook](https://www.facebook.com/theopenmusicbox).

[![License](https://img.shields.io/badge/License-Custom-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-teal.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.x-brightgreen.svg)](https://vuejs.org/)

<!-- Code Quality Badges -->
[![Type Check](https://img.shields.io/badge/mypy-1176_errors-red.svg)](https://github.com/The-Open-Music-Box/raspberrypi-firmware/issues/37)
[![Security](https://img.shields.io/badge/bandit-23_issues-yellow.svg)](https://github.com/The-Open-Music-Box/raspberrypi-firmware/issues/38)
[![Complexity](https://img.shields.io/badge/complexity-C_avg-yellow.svg)](https://github.com/The-Open-Music-Box/raspberrypi-firmware/issues/40)
[![Docstrings](https://img.shields.io/badge/docstrings-93.6%25-brightgreen.svg)](back/pyproject.toml)
[![Duplication](https://img.shields.io/badge/duplication-1.04%25-brightgreen.svg)](https://github.com/The-Open-Music-Box/raspberrypi-firmware/issues/42)
[![Dependencies](https://img.shields.io/badge/vulnerabilities-0-brightgreen.svg)](back/requirements.txt)

<a href="https://www.buymeacoffee.com/rhy6j5cdpq9" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

---

## 📖 Table des matières

**🎯 Présentation**
- [Description du projet](#-description-du-projet)
- [Fonctionnalités principales](#-fonctionnalités-principales)

**🛠️ Installation**
- [Matériel requis](#-matériel-requis)
- [Déploiement sur Raspberry Pi](#-déploiement-sur-raspberry-pi)

**🔧 Aspects techniques**
- [Architecture technique](#-architecture-technique)
- [Documentation](#-documentation)

**💻 Développement**
- [Développement](#-développement)
- [Troubleshooting](#-troubleshooting)

**🤝 Communauté**
- [Contribution](#-contribution)
- [License](#-license)
- [Contact](#-contact)

---

## 🎯 Description du projet

**The Open Music Box** est un lecteur audio tangible conçu pour offrir aux enfants une expérience d'écoute autonome et sans écran. Les parents préparent des playlists (musique, histoires, podcasts) et les associent à des tags NFC physiques. L'enfant n'a qu'à poser un tag sur le lecteur pour lancer instantanément son contenu favori, développant ainsi son autonomie tout en restant dans un environnement sécurisé et contrôlé par les parents.

Basé sur Raspberry Pi, ce projet open source combine hardware accessible et software moderne pour créer une alternative éducative et saine aux écrans.

### Concept

**The Open Music Box** transforme l'écoute audio en une expérience tangible et autonome, spécialement conçue pour les enfants. Les parents préparent et associent des playlists à des tags NFC physiques, permettant aux enfants d'explorer un univers audio riche (musique, histoires, podcasts) en toute autonomie.

- **🏷️ Tags NFC physiques**: Chaque tag représente une playlist (album, histoire, podcast)
- **👶 Autonomie totale**: L'enfant choisit et lance son contenu sans aide parentale
- **🎶 Lecture instantanée**: Posez un tag sur le lecteur pour démarrer automatiquement
- **🎛️ Contrôles simples**: Boutons intuitifs adaptés aux petites mains
- **👨‍👩‍👧 Gestion parentale**: Interface web pour préparer et organiser le contenu
- **🔒 Environnement sécurisé**: Contenu pré-approuvé par les parents

### Cas d'usage principaux

#### 🎯 Usage familial (cas principal)

**Pour les enfants (3-12 ans):**
- 🎵 Explorer leur bibliothèque musicale de façon autonome
- 📚 Écouter des histoires audio et livres-audio avant le coucher
- 🎙️ Découvrir des podcasts éducatifs adaptés à leur âge
- 🎨 Choisir leur ambiance sonore selon leurs activités (jeux, devoirs, détente)
- 🧩 Développer leur autonomie et sens de l'organisation

**Pour les parents:**
- ✅ Préparer des playlists thématiques (berceuses, comptines, histoires, musique calme)
- ✅ Contrôler et valider tout le contenu accessible
- ✅ Créer une expérience sans écran pour leurs enfants
- ✅ Associer facilement des tags aux contenus (stickers, cartes, figurines)
- ✅ Gérer à distance via l'interface web

#### 🏫 Autres usages

- **Écoles et garderies**: Bibliothèque audio collective pour temps calmes
- **Médiathèques**: Borne d'écoute interactive pour jeune public
- **Thérapie**: Outil ludique pour enfants à besoins spécifiques
- **Familles multigénérationnelles**: Interface simple pour grands-parents et enfants

---

## ✨ Fonctionnalités principales

### 🎵 Gestion de la musique

- **Playlists personnalisables**: Créez et organisez vos playlists
- **Upload de fichiers audio**: Support MP3, d'autres formats seront rajoutés

### 🏷️ Système NFC

- **Lecture automatique**: Détection et lecture instantanée
- **Association flexible**: Liez n'importe quel tag à n'importe quelle playlist

### 🎛️ Contrôles et lecture

- **Boutons physiques**: Play/Pause, Suivant, Précédent
- **Encodeur rotatif**: Contrôle du volume avec bouton intégré
- **Lecture continue**: Passe automatiquement au morceau suivant

### 🌐 Interface web

- **Design responsive**: Compatible mobile, tablette, et desktop
- **Synchronisation temps réel**: WebSocket pour des mises à jour instantanées
- **Interface intuitive**: UI facile à utiliser

---

## 🔌 Matériel requis

### Composants essentiels

| Composant | Modèle recommandé | Prix approximatif |
|-----------|-------------------|-------------------|
| **Ordinateur** | [Raspberry Pi 4 (1GB RAM)](https://www.raspberrystore.nl/PrestaShop/en/raspberry-pi-v4/226-raspberry-pi-4-model-b-1gb-765756931168.html) | ~40€ |
| **Ordinateur** Alternative | [Zero W2](https://www.raspberrystore.nl/PrestaShop/en/raspberry-pi-zero-v1-en-v2/588-raspberry-pi-zero-2wh-5056561800011.html) | ~22€ |
| **Carte audio** | [Waveshare WM8960 Audio HAT](https://www.amazon.fr/IBest-Waveshare-WM8960-Audio-Raspberry/dp/B07R8M3XFQ) | ~22€ |
| **Lecteur NFC** | [PN532 NFC Module (I2C/SPI)](https://www.amazon.fr/communication-lecteur-Arduino-Raspberry-Smartphone/dp/B07YDG6X2V/) | ~10€ |
| **Carte SD** | 32GB Class 10 | ~10€ |
| **Alimentation** | 5V 3A USB-C (Pi 4) ou Micro-USB (Pi 3) | ~10€ |

### Composants optionnels

- **Boutons GPIO**: Pour contrôles physiques (Play/Pause, Next, Prev)
- **Encodeur rotatif**: Pour contrôle du volume
- **Boîtier**: Pour protection et design
- **Tags NFC**: NTAG213/215/216 ou Mifare Classic (basiquement nimporte quel tag NFC peut etre utilisé)

### Configuration GPIO détaillée

Le projet utilise les broches GPIO suivantes (numérotation BCM) :

#### Boutons physiques (5 boutons configurables)
| Bouton | GPIO | Fonction par défaut | Description |
|--------|------|---------------------|-------------|
| BT0 | 23 | À définir | Debug print (configurable) |
| BT1 | 27 | Piste précédente | Skip to previous track |
| BT2 | 22 | À définir | Debug print (configurable) |
| BT3 | 6 | À définir | Debug print (configurable) |
| BT4 | 5 | Piste suivante | Skip to next track |

#### Encodeur rotatif (volume)
| Fonction | GPIO | Description |
|----------|------|-------------|
| SW (Switch) | 16 | Play/Pause (bouton pressoir de l'encodeur) |
| CLK (Channel A) | 26 | Signal d'encodage - rotation horaire = volume + |
| DT (Channel B) | 13 | Signal d'encodage - rotation anti-horaire = volume - |

#### LED RGB (indicateur d'état)
| Couleur | GPIO | Description |
|---------|------|-------------|
| Rouge | 25 | Composante rouge de la LED RGB |
| Vert | 12 | Composante verte de la LED RGB |
| Bleu | 24 | Composante bleue de la LED RGB |

#### Interfaces matérielles
| Interface | Pins | Description |
|-----------|------|-------------|
| I2C (NFC) | GPIO 2/3 | Lecteur NFC PN532 |
| Audio HAT | Tous les GPIO | WM8960 monte sur header GPIO |

> **Note**: Les boutons BT0, BT2 et BT3 sont configurables et peuvent être assignés à différentes actions via le fichier de configuration `button_actions_config.py`. Par défaut, ils affichent des messages de debug.

---

## 🚀 Déploiement sur Raspberry Pi

### Vue d'ensemble

Ce guide détaille le processus de déploiement automatisé de l'application **The Open Music Box** sur un Raspberry Pi. Le système utilise des scripts automatisés pour simplifier l'installation et la configuration.

---

## Installation rapide (recommandée)

La méthode la plus simple pour installer The Open Music Box sur un Raspberry Pi fraîchement configuré.

### Prérequis

- Raspberry Pi avec Raspberry Pi OS installé
- SSH configuré et accès au Pi
- Connexion internet

### Installation en 2 commandes

```bash
# Télécharger, extraire et installer (environ 10 minutes)
wget -qO- https://github.com/The-Open-Music-Box/raspberrypi-firmware/releases/latest/download/tomb.tar.gz | tar -xz && cd tomb && sudo ./setup.sh

# Redémarrer pour activer les drivers audio
sudo reboot
```

### Ce que fait setup.sh

Le script d'installation automatise entièrement la configuration:

- **Packages système**: Python 3, FFmpeg, I2C tools, DKMS, etc.
- **Driver audio WM8960**: Installation complète du driver audio HAT via DKMS
- **Configuration audio**: ALSA et service wm8960-soundcard
- **Environnement Python**: Création du venv et installation des dépendances
- **Service systemd**: Configuration et activation de `app.service`
- **Permissions**: Configuration correcte des droits d'accès

### Vérification post-installation

Après le redémarrage:

```bash
# Vérifier que le service est actif
sudo systemctl status app.service

# Tester l'audio
aplay /usr/share/sounds/alsa/Front_Center.wav
```

L'interface web est accessible sur `http://[IP_DU_PI]:5004`

### Télécharger une version spécifique

Pour installer une version particulière au lieu de la dernière:

```bash
# Remplacer v0.5.3 par la version souhaitée
wget https://github.com/The-Open-Music-Box/raspberrypi-firmware/releases/download/v0.5.3/tomb-v0.5.3.tar.gz
tar -xzf tomb-v0.5.3.tar.gz
cd tomb
sudo ./setup.sh
sudo reboot
```

---

## 1. Création de la carte SD

### Étape 1: Installer Raspberry Pi Imager

1. Téléchargez et installez [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insérez votre carte SD (minimum 16GB, recommandé 32GB)

### Étape 2: Configuration du système

1. **Choisir le système d'exploitation**
   - Choisissez votre modele de RasbperryPi
   - Choisir l'OS -> RaspberryPi OS (other)
   - Raspberry Pi OS lite (Bullseye) 64 ou 32 bits en fonction de votre Raspberry Pi

2. **Configuration avancée** (⚙️ Settings)
   - **Hostname**: `theopenmusicbox.local`
   - **Activer SSH**: ✅ Coché
   - **Définir username/password**:
     - Username: `admin` (ou votre choix)
     - Password: [votre mot de passe sécurisé]
   - **Configurer le WiFi** (recommandé):
     - SSID: [nom de votre réseau]
     - Password: [mot de passe WiFi]
     - Pays: [votre pays]
   - **Locale**: Fuseau horaire et clavier

3. **Écrire sur la carte SD**
   - Sélectionnez votre carte SD
   - Cliquez sur "Write"
   - Attendez la fin du processus (5-10 minutes)

4. **Premier démarrage**
   - Insérez la carte SD dans le Raspberry Pi
   - Branchez l'alimentation
   - Attendez 2-3 minutes pour le premier démarrage
   - Le Pi devrait être accessible sur le réseau

---

## 2. Configuration SSH et accès distant

### Étape 1: Configuration de la clé SSH

Exécutez le script de configuration SSH depuis votre ordinateur:

```bash
./setup_ssh_key_to_rpi.sh
```

Le script vous guidera à travers les étapes suivantes:

1. **Sélection de la clé SSH**:
   - Utilisez une clé existante ou créez-en une nouvelle
   - Les clés existantes sont listées avec numéros

2. **Configuration de la connexion**:
   - Username sur le Pi (ex: `admin`)
   - Adresse IP ou hostname (ex: `theopenmusicbox.local`)
   - Nom du raccourci SSH (ex: `tomb`)

3. **Copie de la clé**:
   - Le script copie automatiquement votre clé publique
   - Vous devrez entrer le mot de passe du Pi une seule fois
   - Configure `~/.ssh/config` pour un accès facile

4. **Test de connexion**:
   - Le script teste automatiquement la connexion SSH
   - Vous pouvez vous connecter immédiatement

### Exemple de session

```bash
jonathanpiette@mac tomb-rpi % ./setup_ssh_key_to_rpi.sh

========================================
🎵  The Open Music Box SSH Setup  🎵
========================================

Enhanced SSH Key Setup for Raspberry Pi

🗝️  Found existing SSH keys:
  1) id_ed25519
  2) musicbox_key
  3) rpi_local
  4) tomb
  5) Create a new key

Choose an option (1-5): 4
✅ Using existing key: tomb
👤 Username on the Raspberry Pi: admin
🌐 IP address or hostname: theopenmusicbox.local
🔖 SSH shortcut name: tomb

✅ Public key copied successfully
✅ SSH config updated successfully
✅ Passwordless SSH authentication working!

🎉 Setup completed successfully!
💻 You can now connect with: ssh tomb
```

### Étape 2: Test de la connexion

Une fois la clé configurée, connectez-vous simplement:

```bash
ssh tomb
```

Vous devriez voir:

```
Linux theopenmusicbox 6.1.21-v8+ #1642 SMP PREEMPT Mon Apr  3 17:24:16 BST 2023 aarch64
Last login: [date]
admin@theopenmusicbox:~ $
```

---

## 3. Installation sur le Raspberry Pi

### Vue du processus d'installation

L'installation s'effectue depuis votre ordinateur via SSH avec affichage en temps réel:

```bash
./deploy.sh --prod tomb
```

### Processus automatique

Le script `deploy.sh` effectue les étapes suivantes:

1. **🧪 Tests complets**: Exécution de 1500+ tests (architecture, unité, intégration)
2. **🔨 Build frontend**: Compilation de l'application Vue.js
3. **📦 Package**: Création du package de déploiement
4. **📤 Upload**: Transfert via rsync sur le Raspberry Pi
5. **🔄 Restart**: Redémarrage du service systemd
6. **🏥 Health check**: Vérification du statut du service
7. **📊 Monitoring**: Affichage des logs en temps réel

### Installation manuelle complète

**A venir**

### Script d'installation automatique (setup.sh)

Le script `setup.sh` configure:

- ✅ Environnement virtuel Python
- ✅ Dépendances Python
- ✅ Configuration `.env`
- ✅ Service systemd `app.service`
- ✅ Permissions et propriété des fichiers

Pour lancer l'installation (env 10 minutes):
```bash
ssh tomb
cd tomb
chmod +x setup.sh
./setup.sh
```
---

## 4. Configuration finale

### Vérification de l'installation

Après l'installation, vérifiez le statut du service:

```bash
sudo systemctl status app.service
```

Vous devriez voir:

```
● app.service - The Open Music Box
   Loaded: loaded (/etc/systemd/system/app.service; enabled)
   Active: active (running) since [date]
   ...
```

### Configuration FTP (optionnel)

Pour faciliter le transfert de fichiers audio:

```bash
# Installation du serveur FTP
sudo apt-get install vsftpd

# Configuration
sudo nano /etc/vsftpd.conf
```

Paramètres recommandés:

```
anonymous_enable=NO
local_enable=YES
write_enable=YES
chroot_local_user=YES
```

Redémarrez le service:

```bash
sudo systemctl restart vsftpd
```

### Observation des logs

Surveillez l'application en temps réel:

```bash
sudo journalctl -fu app.service --output=cat
```

ou utilisez:

```bash
./deploy.sh --monitor tomb
```

---

## 5. Synchronisation et déploiement continu

### Déploiement rapide

Pour déployer des modifications:

```bash
# Déploiement complet avec tests
./deploy.sh --prod tomb

# Déploiement sans tests (plus rapide)
./deploy.sh --prod tomb --skip-tests

# Déploiement sans monitoring
./deploy.sh --prod tomb --no-monitor
```

### Mode développement local

Pour tester localement avant déploiement:

```bash
# Déploiement en développement local
./deploy.sh --dev

# Tests seulement
./deploy.sh --test-only

# Build seulement
./deploy.sh --build-only
```

---

## 6. Commandes utiles

### Gestion du service

```bash
# Vérifier le statut
sudo systemctl status app

# Démarrer le service
sudo systemctl start app

# Arrêter le service
sudo systemctl stop app

# Redémarrer le service
sudo systemctl restart app

# Activer au démarrage
sudo systemctl enable app

# Désactiver au démarrage
sudo systemctl disable app
```

### Gestion des logs

```bash
# Logs en temps réel
sudo journalctl -fu app.service

# Logs sans formatage
sudo journalctl -fu app.service --output=cat

# Dernières 100 lignes
sudo journalctl -u app.service -n 100

# Logs depuis aujourd'hui
sudo journalctl -u app.service --since today

# Logs avec erreurs seulement
sudo journalctl -u app.service -p err
```

### Gestion des fichiers

```bash
# Emplacement de l'application
cd /home/admin/tomb

# Configuration
nano /home/admin/tomb/.env

# Logs applicatifs
tail -f /home/admin/tomb/logs/app.log

# Données audio
ls -lh /home/admin/tomb/app/data/audio/

# Playlists
ls -lh /home/admin/tomb/app/data/playlists/
```

### Test du matériel

```bash
# Test audio
aplay /usr/share/sounds/alsa/Front_Center.wav

# Volume système
alsamixer

# Liste des cartes audio
aplay -l

# Test NFC (si le service est arrêté)
sudo i2cdetect -y 1
```

---

## 7. Accès à l'interface web

Une fois le service démarré, l'interface web est accessible:

- **URL locale**: `http://theopenmusicbox.local:5004`
- **URL IP**: `http://[IP_DU_PI]:5004`
- **Depuis le Pi**: `http://localhost:5004`

### Première utilisation

#### 👨‍👩‍👧 Configuration parentale (une fois)

1. **Accédez à l'interface web** depuis votre téléphone ou ordinateur:
   - `http://theopenmusicbox.local:5004`

2. **Créez vos premières playlists**:
   - 📚 "Histoires du soir" - pour le coucher
   - 🎵 "Comptines préférées" - pour la journée
   - 🎙️ "Podcasts éducatifs" - pour apprendre en s'amusant
   - 🎶 "Musique calme" - pour les devoirs

3. **Ajoutez du contenu**:
   - Uploadez des fichiers audio depuis votre ordinateur
   - Importez des playlists depuis YouTube
   - Organisez les pistes dans l'ordre souhaité

4. **Associez des tags NFC**:
   - Collez un sticker ou étiquette sur chaque tag
   - Dans l'interface, cliquez sur "Associate NFC Tag"
   - Posez le tag sur le lecteur
   - Répétez pour chaque playlist

#### 👶 Utilisation par l'enfant (quotidienne)

1. **L'enfant choisit** son tag (ex: le tag avec l'image de dinosaure)
2. **Il pose le tag** sur le lecteur The Open Music Box
3. **La lecture démarre** automatiquement! 🎉
4. **Contrôles simples**:
   - Bouton ▶️ : Pause/Lecture
   - Bouton ⏭️ : Piste suivante
   - Bouton ⏮️ : Piste précédente
   - Molette 🔊 : Volume (tourner pour ajuster)

**C'est tout! Aucune aide parentale nécessaire au quotidien.**

---

## 8. Prérequis pour le déploiement

### Matériel

- ✅ Raspberry Pi 3/4/5 avec Raspbian OS
- ✅ Carte SD (16GB minimum, 32GB recommandé)
- ✅ Connexion réseau stable (WiFi ou Ethernet)
- ✅ Alimentation adaptée au modèle de Pi
- ✅ Carte audio WM8960 HAT (pour audio)
- ✅ Lecteur NFC PN532 (pour tags NFC)

### Logiciel (sur votre ordinateur)

- ✅ SSH client (inclus sur macOS/Linux, [PuTTY](https://www.putty.org/) sur Windows)
- ✅ Raspberry Pi Imager
- ✅ Clé SSH configurée
- ✅ Accès réseau au Raspberry Pi

### Réseau

- ✅ Raspberry Pi et ordinateur sur le même réseau
- ✅ mDNS activé (pour résolution de `*.local`)
- ✅ Port 5004 accessible (pour l'interface web)
- ✅ Port 22 accessible (pour SSH)

---

## 🏗️ Architecture technique

> Cette section détaille l'architecture logicielle du projet pour les développeurs et contributeurs. Si vous êtes un utilisateur final, vous pouvez passer directement à la section [Troubleshooting](#-troubleshooting).

### Vue d'ensemble

```
┌─────────────────────┐
│   Interface Web     │
│   (Vue.js 3)        │
└──────────┬──────────┘
           │ HTTP + WebSocket
┌──────────▼──────────┐
│   Backend API       │
│   (FastAPI/Python)  │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
┌────▼───┐  ┌───▼────┐
│ Audio  │  │  NFC   │
│ WM8960 │  │ PN532  │
└────────┘  └────────┘
```

### Stack technique

**Backend:**
- Python 3.9+
- FastAPI (API REST)
- Socket.IO (WebSocket)
- SQLite (Base de données)
- pygame (Lecture audio)

**Frontend:**
- Vue.js 3 (Composition API)
- Pinia (State management)
- Socket.IO Client
- Axios (HTTP client)
- Vite (Build tool)

**Hardware:**
- Raspberry Pi 3/4/5
- WM8960 Audio HAT (Waveshare)
- PN532 NFC Reader
- Boutons GPIO + encodeur rotatif

### Principes architecturaux

- **DDD (Domain-Driven Design)**: Séparation claire des couches
- **État serveur autoritaire**: Le serveur est la source de vérité
- **Événements séquencés**: Synchronisation fiable avec `server_seq`
- **Abstraction hardware**: Code testable indépendamment du matériel

Pour plus de détails, consultez la [documentation d'architecture](documentation/backend-services-architecture.md).

---

## 📚 Documentation technique

Pour approfondir vos connaissances sur l'architecture et le développement:

### Documentation backend

- **[Backend README](back/README.md)**: Architecture backend détaillée avec exemples
- **[Architecture des services](documentation/backend-services-architecture.md)**: Design patterns et couches logicielles
- **[API et WebSocket](documentation/api-socketio-communication.md)**: Protocoles de communication en temps réel

### Documentation frontend

- **[Architecture frontend](documentation/frontend-architecture.md)**: Structure Vue.js et state management
- **[Guide de style UI](documentation/ui_theme.md)**: Thème visuel et composants

### Documentation développeur

- **[Guide développeur](documentation/developer-guide.md)**: Workflows et conventions de code
- **[Deploy Guide](DEPLOY_GUIDE.md)**: Guide de déploiement avancé
- **[CI/CD et Releases](documentation/ci-cd-and-releases.md)**: Configuration du runner self-hosted et workflow de release

### Ressources utiles

- 🚀 [`deploy.sh`](deploy.sh) - Script de déploiement unifié
- 🔧 [`setup_ssh_key_to_rpi.sh`](setup_ssh_key_to_rpi.sh) - Configuration SSH automatique
- 📦 [`build_public_release.sh`](build_public_release.sh) - Build pour distribution publique

### Liens externes

- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [WM8960 Audio HAT Wiki](https://www.waveshare.com/wiki/WM8960_Audio_HAT)
- [PN532 NFC Module Guide](https://www.nxp.com/docs/en/user-guide/141520.pdf)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue.js Documentation](https://vuejs.org/)

---

## 💻 Développement

> Cette section s'adresse aux développeurs souhaitant contribuer au projet ou le personnaliser.

### Configuration de l'environnement

```bash
# Clone du repository
git clone https://github.com/yourusername/tomb-rpi.git
cd tomb-rpi

# Backend
cd back
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows
pip install -r requirements/dev.txt

# Frontend
cd ../front
npm install

# Variables d'environnement
cp back/.env.example back/.env
# Modifiez back/.env selon vos besoins
```

### Lancement en développement

```bash
# Backend (terminal 1)
cd back
source venv/bin/activate
python start_dev.py

# Frontend (terminal 2)
cd front
npm run dev
```

L'application sera accessible sur:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:5004`
- API Docs: `http://localhost:5004/docs`

### Tests

```bash
# Backend: tous les tests
cd back
USE_MOCK_HARDWARE=true python -m pytest

# Backend: tests spécifiques
USE_MOCK_HARDWARE=true python -m pytest tests/unit/
USE_MOCK_HARDWARE=true python -m pytest tests/integration/

# Frontend: tests
cd front
npm run test

# Frontend: coverage
npm run test:coverage
```

### Déploiement local

```bash
# Déploiement complet en développement
./deploy.sh --dev

# Tests seulement
./deploy.sh --test-only

# Build seulement
./deploy.sh --build-only
```

---

## 🔧 Troubleshooting

### Problèmes courants

#### 🔴 Erreur SSH: "Connection refused"

**Causes possibles:**
- SSH non activé sur le Pi
- Mauvaise adresse IP/hostname
- Pare-feu bloque la connexion

**Solutions:**
```bash
# Vérifier si le Pi répond
ping theopenmusicbox.local

# Tester SSH avec verbose
ssh -v tomb

# Se connecter avec IP directe
ssh admin@192.168.1.xxx

# Vérifier configuration SSH
cat ~/.ssh/config
```

#### 🔴 Erreur audio: "No sound"

**Causes possibles:**
- WM8960 mal connecté
- Drivers non installés
- Volume muet

**Solutions:**
```bash
# Réinstaller drivers WM8960
cd ~/WM8960-Audio-HAT
sudo ./install.sh
sudo reboot

# Vérifier carte audio détectée
aplay -l

# Tester lecture
aplay /usr/share/sounds/alsa/Front_Center.wav

# Ajuster volume
alsamixer
```

#### 🔴 Service ne démarre pas

**Causes possibles:**
- Erreur dans `.env`
- Dépendances manquantes
- Port déjà utilisé

**Solutions:**
```bash
# Voir les erreurs détaillées
sudo journalctl -u app.service -n 50

# Vérifier configuration
cat /home/admin/tomb/.env

# Tester manuellement
cd /home/admin/tomb
source venv/bin/activate
python start_app.py

# Vérifier port disponible
sudo netstat -tulpn | grep 5004
```

#### 🔴 Tags NFC non détectés

**Causes possibles:**
- PN532 mal connecté
- Drivers I2C non chargés
- Tag incompatible

**Solutions:**
```bash
# Activer I2C
sudo raspi-config
# Interface Options > I2C > Enable

# Vérifier détection I2C
sudo i2cdetect -y 1
# Devrait montrer "24" à l'adresse 0x24

# Redémarrer service
sudo systemctl restart app
```

#### 🔴 Interface web inaccessible

**Causes possibles:**
- Service arrêté
- Pare-feu bloque le port
- Mauvaise URL

**Solutions:**
```bash
# Vérifier service actif
sudo systemctl status app

# Vérifier port ouvert
sudo netstat -tulpn | grep 5004

# Trouver IP du Pi
hostname -I

# Tester depuis le Pi
curl http://localhost:5004/api/health
```

#### 🔴 Upload de fichiers échoue

**Causes possibles:**
- Espace disque insuffisant
- Permissions incorrectes
- Format audio non supporté

**Solutions:**
```bash
# Vérifier espace disque
df -h

# Vérifier permissions
ls -la /home/admin/tomb/app/data/

# Corriger permissions
sudo chown -R admin:admin /home/admin/tomb/app/data/
sudo chmod -R 755 /home/admin/tomb/app/data/

# Formats supportés: MP3, FLAC, WAV, OGG, M4A
```

### Logs de débogage

Pour un diagnostic approfondi:

```bash
# Logs système complets
sudo journalctl -u app.service --no-pager

# Logs avec timestamps
sudo journalctl -u app.service -o short-iso

# Logs depuis le dernier boot
sudo journalctl -u app.service -b

# Exporter logs dans un fichier
sudo journalctl -u app.service > ~/app_logs.txt
```

### Réinitialisation complète

Si tout échoue, réinstallez:

```bash
# Arrêter et désactiver service
sudo systemctl stop app
sudo systemctl disable app

# Supprimer installation
rm -rf /home/admin/tomb

# Redéployer
./deploy.sh --prod tomb
```

---

## 🤝 Contribution

Les contributions sont les bienvenues! Voici comment contribuer:

1. **Fork** le projet
2. **Créez une branche** pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. **Committez** vos changements (`git commit -m 'Add some AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. **Ouvrez une Pull Request**

### Guidelines

- Suivez les conventions de code existantes
- Ajoutez des tests pour les nouvelles fonctionnalités
- Documentez les changements dans le README si nécessaire
- Assurez-vous que tous les tests passent avant de soumettre

### Signaler un bug

Ouvrez une [issue](https://github.com/yourusername/tomb-rpi/issues) en incluant:

- Description détaillée du problème
- Steps pour reproduire
- Comportement attendu vs comportement observé
- Version du système, matériel utilisé
- Logs pertinents

---

## 📄 License

Ce projet est open source avec les conditions suivantes:

- ✅ **Usage libre**: Utilisation, copie, modification, distribution pour usage **non commercial**
- ✅ **Contributions**: Ouvertes à tous via pull requests et issues
- ⚠️ **Usage commercial réservé**: La monétisation (vente, services payants, intégration dans produits payants) est **réservée exclusivement à l'auteur original (Jonathan Piette)**
- 💼 **Licence commerciale**: Contactez l'auteur pour options de licence commerciale

Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 📧 Contact

**Jonathan Piette** - Créateur et mainteneur

- 🐙 GitHub: [@yourusername](https://github.com/yourusername)
- 📧 Email: your.email@example.com
- 💬 Discord: [The Open Music Box Community](#) *(à créer)*

### Support

- 🐛 **Bugs**: Ouvrez une [issue](https://github.com/yourusername/tomb-rpi/issues)
- 💡 **Feature requests**: Ouvrez une [issue](https://github.com/yourusername/tomb-rpi/issues) avec le tag "enhancement"
- 💬 **Questions**: Utilisez les [Discussions](https://github.com/yourusername/tomb-rpi/discussions)
- 📖 **Documentation**: Consultez le dossier [documentation/](documentation/)

---

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) pour le framework web
- [Vue.js](https://vuejs.org/) pour le framework frontend
- [Waveshare](https://www.waveshare.com/) pour le WM8960 Audio HAT
- [NXP](https://www.nxp.com/) pour le PN532 NFC reader
- La communauté [Raspberry Pi](https://www.raspberrypi.com/)
- Tous les [contributeurs](https://github.com/yourusername/tomb-rpi/contributors) du projet

---

## 🎵 Amusez-vous bien avec The Open Music Box!

Si ce projet vous plaît, n'hésitez pas à lui donner une ⭐ sur GitHub!

---

<p align="center">
  Made with ❤️ by Jonathan Piette<br>
  <sub>Transforming the way we interact with music</sub>
</p>

# Test des Boutons GPIO - TheOpenMusicBox

Ce dossier contient un script de test standalone pour vérifier le bon fonctionnement des boutons physiques connectés au Raspberry Pi.

## Script de Test

### `test_buttons_standalone.py`

Script indépendant pour tester tous les boutons GPIO sans avoir besoin de lancer l'application complète.

#### Fonctionnalités

- ✅ Test de tous les boutons configurés (BT0-BT4 + encodeur switch)
- ✅ Affichage en temps réel des pressions de boutons
- ✅ Compteur de pressions par bouton
- ✅ Horodatage des dernières pressions
- ✅ Support des différents backends GPIO (RPi.GPIO, lgpio, pigpio)
- ✅ Gestion automatique du debounce
- ✅ Statistiques finales à la sortie

#### Configuration GPIO Actuelle

| Bouton | GPIO | Fonction | Description |
|--------|------|----------|-------------|
| BT0 | 23 | À définir | Debug print (configurable) |
| BT1 | 27 | Piste précédente | Skip to previous track |
| BT2 | 22 | À définir | Debug print (configurable) |
| BT3 | 6 | À définir | Debug print (configurable) |
| BT4 | 5 | Piste suivante | Skip to next track |
| SW | 16 | Play/Pause | Bouton de l'encodeur rotatif |

## Utilisation

### Sur le Raspberry Pi

```bash
# Depuis le répertoire back/
cd /home/admin/tomb/

# Activer l'environnement virtuel
source venv/bin/activate

# Lancer le test
python tools/test_buttons_standalone.py
```

### Sortie Exemple

```
================================================================================
🎮 BUTTON TEST - TheOpenMusicBox
================================================================================

Press any button to test it.
Press Ctrl+C to exit and see final statistics.
================================================================================

🔌 Initializing buttons...
================================================================================
✅ [BT0] initialized on GPIO 23 - BT0 (GPIO23) - To be defined (debug print)
✅ [BT1] initialized on GPIO 27 - BT1 (GPIO27) - Previous track
✅ [BT2] initialized on GPIO 22 - BT2 (GPIO22) - To be defined (debug print)
✅ [BT3] initialized on GPIO 6 - BT3 (GPIO6) - To be defined (debug print)
✅ [BT4] initialized on GPIO 5 - BT4 (GPIO5) - Next track
✅ [SW] initialized on GPIO 16 - Play/Pause (encoder switch)
================================================================================
✅ Initialized 6/6 buttons
👂 Listening for button presses... (Press Ctrl+C to exit)

🔘 [BT1] PRESSED - GPIO 27 (Previous track) - Total presses: 1
────────────────────────────────────────────────────────────────────────────────
🔘 [BT4] PRESSED - GPIO 5 (Next track) - Total presses: 1
────────────────────────────────────────────────────────────────────────────────
🔘 [SW] PRESSED - GPIO 16 (Play/Pause (encoder switch)) - Total presses: 1
────────────────────────────────────────────────────────────────────────────────

^C
🛑 Test interrupted by user

================================================================================
📊 BUTTON TEST STATUS
================================================================================
[BT0] GPIO 23 - BT0 (GPIO23) - To be defined (debug print)     | Not pressed yet
[BT1] GPIO 27 - BT1 (GPIO27) - Previous track                  | Presses:   1 | Last: 14:23:15
[BT2] GPIO 22 - BT2 (GPIO22) - To be defined (debug print)     | Not pressed yet
[BT3] GPIO  6 - BT3 (GPIO6) - To be defined (debug print)      | Not pressed yet
[BT4] GPIO  5 - BT4 (GPIO5) - Next track                       | Presses:   1 | Last: 14:23:18
[SW]  GPIO 16 - Play/Pause (encoder switch)                    | Presses:   1 | Last: 14:23:21
================================================================================
🧹 Cleaning up GPIO resources...
✅ Cleanup completed
```

## Diagnostic des Problèmes

### Bouton non détecté

Si un bouton ne répond pas :

1. **Vérifier la connexion physique**
   - Le bouton est bien connecté au bon GPIO
   - Le GND (masse) est connecté
   - Les fils ne sont pas endommagés

2. **Vérifier les résistances pull-up/pull-down**
   - Le script essaie automatiquement avec et sans pull-up interne
   - Si aucune ne fonctionne, vérifier le câblage externe

3. **Tester manuellement avec un multimètre**
   - Mesurer la continuité du bouton
   - Vérifier que le bouton change d'état quand pressé

### Erreurs GPIO

Si vous obtenez des erreurs de permission :

```bash
# Ajouter l'utilisateur au groupe GPIO
sudo usermod -aG gpio $USER

# Se déconnecter et reconnecter pour appliquer
```

Si vous obtenez "No GPIO backend available" :

```bash
# Installer les bibliothèques GPIO
sudo apt-get update
sudo apt-get install python3-rpi.gpio python3-lgpio

# Ou dans l'environnement virtuel
pip install RPi.GPIO lgpio
```

### Pressions multiples (bounce)

Si un bouton déclenche plusieurs fois pour une seule pression :

- Le debounce est configuré à 300ms par défaut
- Pour l'ajuster, modifier `bounce_time` dans le script (ligne ~151)
- Valeur recommandée : entre 0.2 et 0.5 secondes

## Modifications de Configuration

Pour tester avec une configuration GPIO différente, modifiez le dictionnaire `button_configs` dans le script (lignes 67-73) :

```python
self.button_configs = {
    'NOUVEAU_BOUTON': {'gpio': 17, 'description': 'Ma nouvelle fonction'},
    # ... autres boutons
}
```

## Intégration avec l'Application

Une fois les boutons testés et validés avec ce script, la configuration finale se fait dans :

- **GPIO pins** : `back/app/src/config/hardware_config.py`
- **Actions** : `back/app/src/config/button_actions_config.py`

## Support

Pour plus d'informations sur la configuration GPIO, consultez :
- [README principal](../../README.md) - Section "Configuration GPIO détaillée"
- [Documentation hardware](../app/documentation/HARDWARE.md)

---

**Note** : Ce script est indépendant de l'application principale et peut être utilisé pour diagnostiquer les problèmes matériels avant le déploiement.

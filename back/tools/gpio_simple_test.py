#!/usr/bin/env python3
"""
Script simple pour tester les GPIO - Affiche quand un bouton est pressé
"""

import signal
import time
import sys

# Configuration des pins (mise à jour selon détection réelle)
PINS = {
    16: "Next",
    26: "Previous",
    23: "Play/Pause (Switch)",
    8: "Encoder CLK",
    21: "Encoder DT"
}

def cleanup():
    """Nettoyer GPIO à la sortie"""
    try:
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        print("\n✅ GPIO nettoyé")
    except:
        pass

def signal_handler(sig, frame):
    """Gérer Ctrl+C proprement"""
    print("\n🛑 Arrêt...")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def main():
    """Test simple des GPIO"""
    print("=" * 50)
    print("🎯 TEST SIMPLE GPIO")
    print("=" * 50)

    try:
        import RPi.GPIO as GPIO
        print("✅ RPi.GPIO importé")
    except ImportError:
        print("❌ RPi.GPIO non disponible")
        print("   Installez avec: sudo apt-get install python3-rpi.gpio")
        return

    # Configuration
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Configurer chaque pin
    for pin, name in PINS.items():
        try:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            print(f"✅ GPIO {pin:2d} configuré ({name})")
        except Exception as e:
            print(f"❌ GPIO {pin:2d} erreur: {e}")

    print("\n📍 Appuyez sur les boutons...")
    print("   Ctrl+C pour arrêter")
    print("-" * 50)

    # Stocker l'état précédent
    last_state = {}
    for pin in PINS:
        try:
            last_state[pin] = GPIO.input(pin)
        except:
            last_state[pin] = 1

    # Boucle de détection
    try:
        while True:
            for pin, name in PINS.items():
                try:
                    current = GPIO.input(pin)

                    # Détecter changement (front descendant = bouton pressé)
                    if last_state[pin] == 1 and current == 0:
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"[{timestamp}] 🔘 {name:12s} PRESSÉ! (GPIO {pin})")

                    last_state[pin] = current

                except:
                    pass

            time.sleep(0.01)  # Petit délai pour ne pas surcharger CPU

    except KeyboardInterrupt:
        pass

    cleanup()

if __name__ == "__main__":
    main()
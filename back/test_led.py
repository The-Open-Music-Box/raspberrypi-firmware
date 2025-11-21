#!/usr/bin/env python3
# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Script de test simple pour la LED RGB.

Teste les 3 couleurs primaires et quelques animations basiques.
Usage: python test_led.py
"""

import time
import sys

# Pins GPIO (numérotation BCM)
RED_PIN = 25
GREEN_PIN = 12
BLUE_PIN = 24

def test_led():
    """Test la LED RGB avec différentes couleurs et animations."""
    print("🔌 Initialisation des GPIO...")

    try:
        from gpiozero import PWMLED

        # Initialiser les LEDs PWM
        red = PWMLED(RED_PIN)
        green = PWMLED(GREEN_PIN)
        blue = PWMLED(BLUE_PIN)

        print(f"✅ GPIO initialisés (R:{RED_PIN}, G:{GREEN_PIN}, B:{BLUE_PIN})")
        print("\n" + "="*50)

        # Test 1: Rouge
        print("\n🔴 Test 1: ROUGE (2 secondes)")
        red.value = 1.0
        green.value = 0.0
        blue.value = 0.0
        time.sleep(2)

        # Éteindre
        red.value = 0.0
        time.sleep(0.5)

        # Test 2: Vert
        print("🟢 Test 2: VERT (2 secondes)")
        red.value = 0.0
        green.value = 1.0
        blue.value = 0.0
        time.sleep(2)

        # Éteindre
        green.value = 0.0
        time.sleep(0.5)

        # Test 3: Bleu
        print("🔵 Test 3: BLEU (2 secondes)")
        red.value = 0.0
        green.value = 0.0
        blue.value = 1.0
        time.sleep(2)

        # Éteindre
        blue.value = 0.0
        time.sleep(0.5)

        # Test 4: Blanc (toutes les couleurs)
        print("⚪ Test 4: BLANC (2 secondes)")
        red.value = 1.0
        green.value = 1.0
        blue.value = 1.0
        time.sleep(2)

        # Éteindre
        red.value = 0.0
        green.value = 0.0
        blue.value = 0.0
        time.sleep(0.5)

        # Test 5: Jaune (rouge + vert)
        print("🟡 Test 5: JAUNE (2 secondes)")
        red.value = 1.0
        green.value = 1.0
        blue.value = 0.0
        time.sleep(2)

        # Éteindre
        red.value = 0.0
        green.value = 0.0
        time.sleep(0.5)

        # Test 6: Cyan (vert + bleu)
        print("🔷 Test 6: CYAN (2 secondes)")
        red.value = 0.0
        green.value = 1.0
        blue.value = 1.0
        time.sleep(2)

        # Éteindre
        green.value = 0.0
        blue.value = 0.0
        time.sleep(0.5)

        # Test 7: Magenta (rouge + bleu)
        print("🟣 Test 7: MAGENTA (2 secondes)")
        red.value = 1.0
        green.value = 0.0
        blue.value = 1.0
        time.sleep(2)

        # Éteindre
        red.value = 0.0
        blue.value = 0.0
        time.sleep(0.5)

        # Test 8: Clignotement blanc
        print("💡 Test 8: CLIGNOTEMENT BLANC (5 fois)")
        for i in range(5):
            red.value = 1.0
            green.value = 1.0
            blue.value = 1.0
            time.sleep(0.3)
            red.value = 0.0
            green.value = 0.0
            blue.value = 0.0
            time.sleep(0.3)

        # Test 9: Pulsation blanche (breathing)
        print("🌊 Test 9: PULSATION BLANCHE (3 cycles)")
        for _ in range(3):
            # Fade in
            for i in range(0, 101, 5):
                brightness = i / 100.0
                red.value = brightness
                green.value = brightness
                blue.value = brightness
                time.sleep(0.02)
            # Fade out
            for i in range(100, -1, -5):
                brightness = i / 100.0
                red.value = brightness
                green.value = brightness
                blue.value = brightness
                time.sleep(0.02)

        # Nettoyer
        print("\n🧹 Nettoyage des GPIO...")
        red.close()
        green.close()
        blue.close()

        print("✅ Tests terminés avec succès!")
        print("="*50)

    except ImportError:
        print("❌ Erreur: gpiozero n'est pas installé")
        print("Installez-le avec: pip install gpiozero")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("="*50)
    print("Test LED RGB - TheOpenMusicBox")
    print("="*50)
    print(f"\nPins utilisés:")
    print(f"  Rouge (R):  GPIO {RED_PIN}")
    print(f"  Vert (G):   GPIO {GREEN_PIN}")
    print(f"  Bleu (B):   GPIO {BLUE_PIN}")
    print("\nAppuyez sur Ctrl+C pour arrêter\n")

    try:
        test_led()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrompu par l'utilisateur")
        sys.exit(0)

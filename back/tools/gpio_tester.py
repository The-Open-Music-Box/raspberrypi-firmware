#!/usr/bin/env python3
"""
Script de test GPIO simplifié
Met tous les GPIO à LOW puis alterne HIGH/LOW/HIGH en boucle
"""

import os
import signal
import sys
import time

try:
    from gpiozero import LED, Device
    from gpiozero.pins.lgpio import LgpioFactory
    GPIOZERO_AVAILABLE = True
except ImportError:
    print("⚠️  gpiozero ou lgpio non disponible - mode simulation")
    GPIOZERO_AVAILABLE = False


class SimpleGPIOTester:
    """Testeur GPIO simplifié"""

    def __init__(self):
        self.test_pins: list[int] = list(range(2, 28))  # GPIO 2-27
        self.running = True
        self.leds = {}

        # Configuration du factory GPIO
        if GPIOZERO_AVAILABLE:
            Device.pin_factory = LgpioFactory()

        # Handler pour arrêt propre
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handler pour arrêt propre"""
        print("\n🛑 Arrêt en cours...")
        self.running = False

    def print_header(self):
        """Affiche l'en-tête"""
        print("=" * 50)
        print("🔌 GPIO TESTER SIMPLIFIÉ")
        print("=" * 50)
        print(f"🧪 Pins testés: GPIO 2-27 ({len(self.test_pins)} pins)")
        print(f"💾 Mode: {'Hardware réel' if GPIOZERO_AVAILABLE else 'Simulation'}")
        print("=" * 50)

    def initialize_pins_low(self):
        """Phase 1: Met tous les pins à LOW"""
        print("\n📉 Phase 1: Initialisation - Tous les pins à LOW...")

        if not GPIOZERO_AVAILABLE:
            print("   [SIMULATION] Tous les pins mis à LOW")
            return

        try:
            for pin in self.test_pins:
                if not self.running:
                    break
                self.leds[pin] = LED(pin)
                self.leds[pin].off()
                print(f"   GPIO {pin:2d}: LOW")

            print("   ✅ Tous les pins initialisés à LOW")

        except Exception as e:
            print(f"   ❌ Erreur initialisation: {e}")

    def run_alternating_loop(self):
        """Phase 2: Boucle alternante HIGH/LOW/HIGH"""
        print("\n🔄 Phase 2: Boucle alternante HIGH → LOW → HIGH...")
        print("   (Ctrl+C pour arrêter)")

        if not GPIOZERO_AVAILABLE:
            print("   [SIMULATION] Boucle HIGH/LOW/HIGH")
            cycle = 0
            try:
                while self.running:
                    states = ["HIGH", "LOW", "HIGH"]
                    state = states[cycle % 3]
                    print(f"   Cycle {cycle + 1}: Tous les pins → {state}")
                    time.sleep(1.0)
                    cycle += 1
            except KeyboardInterrupt:
                pass
            return

        cycle = 0
        try:
            while self.running:
                states = [True, False, True]  # HIGH, LOW, HIGH
                state_names = ["HIGH", "LOW", "HIGH"]

                current_state = states[cycle % 3]
                state_name = state_names[cycle % 3]

                print(f"   Cycle {cycle + 1}: Tous les pins → {state_name}")

                # Appliquer l'état à tous les pins
                for pin in self.test_pins:
                    if not self.running:
                        break
                    if current_state:
                        self.leds[pin].on()
                    else:
                        self.leds[pin].off()

                time.sleep(1.0)
                cycle += 1

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"   ❌ Erreur boucle: {e}")

    def cleanup(self):
        """Nettoyage des ressources"""
        if GPIOZERO_AVAILABLE:
            for led in self.leds.values():
                try:
                    led.close()
                except Exception:
                    pass

    def run(self):
        """Lance le test complet"""
        try:
            self.print_header()

            if not self.running:
                return

            # Phase 1: Initialisation LOW
            self.initialize_pins_low()

            if not self.running:
                return

            # Phase 2: Boucle alternante
            self.run_alternating_loop()

        except KeyboardInterrupt:
            print("\n🛑 Test interrompu")
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
        finally:
            self.cleanup()
            print("\n🏁 Test terminé")


def main():
    """Point d'entrée principal"""
    print("🚀 Démarrage du testeur GPIO simplifié...")

    # Vérifications préliminaires
    if GPIOZERO_AVAILABLE and os.geteuid() != 0:
        print("⚠️  Ce script nécessite les privilèges root pour accéder aux GPIO")
        print("   Relancez avec: sudo python3 gpio_tester.py")
        sys.exit(1)

    tester = SimpleGPIOTester()
    tester.run()


if __name__ == "__main__":
    main()

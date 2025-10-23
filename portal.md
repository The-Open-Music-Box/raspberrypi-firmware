# 1) installation / réparation complète
sudo bash portal.sh install

# 2) lancer le mode setup (AP + portail) pendant 3 min
sudo bash portal.sh setup 180

# 3) retour manuel en mode client
sudo bash portal.sh normal

# 4) diagnostic rapide (état services / radio)
sudo bash portal.sh status

# 5) journaux utiles (AP + webserver)
sudo bash portal.sh logs

# 6) autotests locaux (HTTP + conf)
sudo bash portal.sh selftest

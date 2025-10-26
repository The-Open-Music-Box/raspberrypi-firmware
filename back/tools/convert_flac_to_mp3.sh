#!/bin/bash

# Script pour convertir tous les fichiers FLAC en MP3 dans le dossier upload
# Utilise ffmpeg pour la conversion
# Supprime le fichier source après conversion réussie

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================"
echo "🎵 Conversion FLAC vers MP3 🎵"
echo "======================================"

# Vérifier si ffmpeg est installé
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Erreur: ffmpeg n'est pas installé${NC}"
    echo "Installez-le avec: sudo apt-get install ffmpeg"
    exit 1
fi

# Trouver tous les fichiers FLAC dans le dossier upload et ses sous-dossiers
UPLOAD_DIR="./app/data/uploads"

if [ ! -d "$UPLOAD_DIR" ]; then
    echo -e "${RED}Erreur: Le dossier $UPLOAD_DIR n'existe pas${NC}"
    exit 1
fi

echo "Recherche des fichiers FLAC dans $UPLOAD_DIR..."

# Compter le nombre total de fichiers FLAC
TOTAL_FILES=$(find "$UPLOAD_DIR" -type f -iname "*.flac" | wc -l)

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo -e "${YELLOW}Aucun fichier FLAC trouvé dans $UPLOAD_DIR${NC}"
    exit 0
fi

echo -e "${GREEN}Trouvé $TOTAL_FILES fichier(s) FLAC à convertir${NC}"
echo ""

CONVERTED=0
FAILED=0

# Parcourir tous les fichiers FLAC
while IFS= read -r -d '' flac_file; do
    echo "----------------------------------------"
    echo -e "${YELLOW}Traitement: $flac_file${NC}"

    # Générer le nom du fichier MP3 (même nom, extension .mp3)
    mp3_file="${flac_file%.*}.mp3"

    # Vérifier si le fichier MP3 existe déjà
    if [ -f "$mp3_file" ]; then
        echo -e "${YELLOW}Le fichier MP3 existe déjà: $mp3_file${NC}"
        echo -e "${YELLOW}Suppression du fichier FLAC source...${NC}"
        rm "$flac_file"
        echo -e "${GREEN}✓ FLAC supprimé${NC}"
        ((CONVERTED++))
        continue
    fi

    # Convertir FLAC vers MP3 avec ffmpeg
    echo "Conversion en cours..."
    if ffmpeg -i "$flac_file" -ab 320k -map_metadata 0 -id3v2_version 3 "$mp3_file" -y 2>/dev/null; then
        echo -e "${GREEN}✓ Conversion réussie: $mp3_file${NC}"

        # Supprimer le fichier FLAC source
        echo "Suppression du fichier source..."
        rm "$flac_file"
        echo -e "${GREEN}✓ Fichier source supprimé${NC}"

        ((CONVERTED++))
    else
        echo -e "${RED}✗ Échec de la conversion${NC}"
        ((FAILED++))
    fi

done < <(find "$UPLOAD_DIR" -type f -iname "*.flac" -print0)

echo ""
echo "======================================"
echo "📊 Résumé de la conversion"
echo "======================================"
echo -e "${GREEN}Fichiers convertis avec succès: $CONVERTED${NC}"
echo -e "${RED}Échecs de conversion: $FAILED${NC}"
echo -e "${YELLOW}Total traité: $((CONVERTED + FAILED))${NC}"

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}🎉 Toutes les conversions ont réussi!${NC}"
else
    echo -e "${YELLOW}⚠️  Certaines conversions ont échoué${NC}"
fi
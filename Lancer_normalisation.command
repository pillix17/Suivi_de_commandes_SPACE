#!/bin/bash
# Place ce fichier dans le même dossier que normaliser_commandes.py et tes CSV.
# Double-clique dessus pour lancer la normalisation.

# Se déplacer dans le dossier du script
cd "$(dirname "$0")"

# Lancer le script Python
python3 normaliser_commandes.py

# Garder la fenêtre ouverte après exécution
echo ""
echo "Appuyez sur une touche pour fermer cette fenêtre..."
read -n 1

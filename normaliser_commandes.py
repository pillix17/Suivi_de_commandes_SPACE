#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║   Normalisateur de commandes — Klipso + Expose       ║
║   Double-cliquez pour lancer, ou glissez vos CSV     ║
╚══════════════════════════════════════════════════════╝

Ce script lit vos deux exports hebdomadaires (Klipso et Expose),
les met au même format, et produit un fichier CSV prêt à coller
dans votre tableau Excel de suivi.

UTILISATION :
  Option A — Placez ce script dans le même dossier que vos CSV,
             puis double-cliquez dessus.
  Option B — Dans un terminal : python3 normaliser_commandes.py
"""

import pandas as pd
import os
import sys
from datetime import datetime

# ─────────────────────────────────────────────────────────────
#  CONFIGURATION — modifiez ici si besoin
# ─────────────────────────────────────────────────────────────

# Dossier où chercher les CSV (par défaut : même dossier que ce script)
DOSSIER = os.path.dirname(os.path.abspath(__file__))

# Mots-clés qui identifient chaque type de fichier (insensible à la casse)
MOTS_CLES_KLIPSO = ["klipso", "lignes de commande", "lignes_commande"]
MOTS_CLES_EXPOSE  = ["expose", "space supplier", "space_supplier"]

# Colonnes du fichier de sortie (dans cet ordre)
COLONNES = [
    "Source",
    "N° Commande",
    "Date Commande",
    "Société / Client",
    "Statut",
    "Code Produit",
    "Libellé Produit",
    "Quantité",
    "Total HT",
    "Total TTC",
    "Contact Nom",
    "Contact Prénom",
    "Contact Email",
    "Contact Mobile",
    "Semaine Import",
]


# ─────────────────────────────────────────────────────────────
#  FONCTIONS UTILITAIRES
# ─────────────────────────────────────────────────────────────

def semaine_courante():
    """Retourne ex. 'S24-2026'"""
    n = datetime.now()
    return f"S{n.isocalendar()[1]:02d}-{n.year}"

def nettoyer_montant(s):
    """Convertit '28 000,00 €' → 28000.0"""
    if pd.isna(s) or str(s).strip() in ("", "0"):
        return ""
    s = str(s).replace("€", "").replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return s

def col(df, *noms):
    """Retourne la première colonne trouvée parmi les noms candidats, sinon ''."""
    for n in noms:
        if n in df.columns:
            return df[n].fillna("").astype(str)
    return pd.Series([""] * len(df))

def detecter_csv(dossier, mots_cles):
    """Retourne le chemin du premier CSV dont le nom contient un des mots-clés."""
    for f in sorted(os.listdir(dossier)):
        if not f.lower().endswith(".csv"):
            continue
        if any(mc in f.lower() for mc in mots_cles):
            return os.path.join(dossier, f)
    return None

def lire_csv(chemin):
    """Lit un CSV en essayant plusieurs encodages."""
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(chemin, sep=";", encoding=enc, dtype=str)
            return df, enc
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"Impossible de lire : {chemin}")


# ─────────────────────────────────────────────────────────────
#  LECTURE ET NORMALISATION KLIPSO
# ─────────────────────────────────────────────────────────────

def normaliser_klipso(chemin):
    df, enc = lire_csv(chemin)
    print(f"   Encodage détecté : {enc} — {len(df)} lignes")

    out = pd.DataFrame({
        "Source"          : pd.Series(["Klipso"] * len(df), index=df.index),
        "N° Commande"     : col(df, "N° de commande (Commande)"),
        "Date Commande"   : col(df, "Date de commande (Commande)"),
        "Société / Client": col(df, "Concerne (Commande)"),
        "Statut"          : col(df, "État (Commande)"),
        "Code Produit"    : col(df, "Code (Produit)"),
        "Libellé Produit" : col(df, "Libellé en Français (Produit)"),
        "Quantité"        : col(df, "Qté 1"),
        "Total HT"        : col(df, "Total HT brut").apply(nettoyer_montant),
        "Total TTC"       : col(df, "Total TTC net (devise comptable)").apply(nettoyer_montant),
        "Contact Nom"     : col(df, "Nom (Commande > Dossier exposant > Contact participation)"),
        "Contact Prénom"  : col(df, "Prénom (Commande > Dossier exposant > Contact participation)"),
        "Contact Email"   : col(df, "Email (Commande > Dossier exposant > Contact participation)"),
        "Contact Mobile"  : col(df, "Téléphone mobile (Commande > Dossier exposant > Contact participation)"),
        "Semaine Import"  : semaine_courante(),
    })

    return out[COLONNES]


# ─────────────────────────────────────────────────────────────
#  LECTURE ET NORMALISATION EXPOSE
# ─────────────────────────────────────────────────────────────

def normaliser_expose(chemin):
    df, enc = lire_csv(chemin)
    print(f"   Encodage détecté : {enc} — {len(df)} lignes")

    out = pd.DataFrame({
        "Source"          : pd.Series(["Expose"] * len(df), index=df.index),
        "N° Commande"     : col(df, "no_cde_fournisseur", "no_facture"),
        "Date Commande"   : col(df, "date_initiale_commande", "date_maj"),
        "Société / Client": col(df, "enseigne_participant", "société", "societe"),
        "Statut"          : col(df, "statut_client", "statut fournisseur"),
        "Code Produit"    : col(df, "reference_produit", "reference", "sku"),
        "Libellé Produit" : col(df, "produit_fournisseur"),
        "Quantité"        : col(df, "quantité", "quantite"),
        "Total HT"        : col(df, "prix_achat_HT_total").apply(nettoyer_montant),
        "Total TTC"       : pd.Series([""] * len(df), index=df.index),
        "Contact Nom"     : col(df, "nom_livraison"),
        "Contact Prénom"  : col(df, "prénom_livraison", "prenom_livraison"),
        "Contact Email"   : pd.Series([""] * len(df), index=df.index),
        "Contact Mobile"  : col(df, "mobile_livraison"),
        "Semaine Import"  : semaine_courante(),
    })

    return out[COLONNES]


# ─────────────────────────────────────────────────────────────
#  PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 56)
    print("  Normalisateur de commandes — Klipso + Expose")
    print("=" * 56)
    print()

    # ── Détection automatique des fichiers ──
    klipso_chemin = detecter_csv(DOSSIER, MOTS_CLES_KLIPSO)
    expose_chemin  = detecter_csv(DOSSIER, MOTS_CLES_EXPOSE)

    if klipso_chemin:
        print(f"✓ Klipso trouvé  : {os.path.basename(klipso_chemin)}")
    else:
        rep = input("⚠ Fichier Klipso non trouvé. Chemin complet (ou Entrée pour ignorer) : ").strip().strip('"')
        klipso_chemin = rep if rep and os.path.exists(rep) else None

    if expose_chemin:
        print(f"✓ Expose trouvé  : {os.path.basename(expose_chemin)}")
    else:
        rep = input("⚠ Fichier Expose non trouvé. Chemin complet (ou Entrée pour ignorer) : ").strip().strip('"')
        expose_chemin = rep if rep and os.path.exists(rep) else None

    print()

    # ── Traitement ──
    frames = []

    if klipso_chemin:
        print("→ Traitement Klipso…")
        try:
            df_k = normaliser_klipso(klipso_chemin)
            frames.append(df_k)
            print(f"   {len(df_k)} lignes normalisées.\n")
        except Exception as e:
            print(f"   ❌ Erreur : {e}\n")

    if expose_chemin:
        print("→ Traitement Expose…")
        try:
            df_e = normaliser_expose(expose_chemin)
            frames.append(df_e)
            print(f"   {len(df_e)} lignes normalisées.\n")
        except Exception as e:
            print(f"   ❌ Erreur : {e}\n")

    if not frames:
        print("❌ Aucun fichier traité. Vérifiez les noms et chemins.")
        input("\nAppuyez sur Entrée pour fermer…")
        sys.exit(1)

    # ── Fusion et export ──
    df_final = pd.concat(frames, ignore_index=True)

    semaine = semaine_courante()
    nom_sortie = os.path.join(DOSSIER, f"commandes_normalisees_{semaine}.csv")

    # Si le fichier existe déjà, on horodate pour éviter l'écrasement
    if os.path.exists(nom_sortie):
        ts = datetime.now().strftime("%H%M")
        nom_sortie = os.path.join(DOSSIER, f"commandes_Klipso&Expose_normalisees_{semaine}_{ts}.csv")

    df_final.to_csv(nom_sortie, sep=";", index=False, encoding="utf-8-sig")

    print("=" * 56)
    print(f"✅ Fichier créé : {os.path.basename(nom_sortie)}")
    print(f"   {len(df_final)} lignes au total")
    print()
    print("  ÉTAPES SUIVANTES :")
    print("  1. Ouvrez ce fichier CSV dans Excel")
    print("  2. Sélectionnez toutes les lignes de données")
    print("     (sans la ligne d'en-tête)")
    print("  3. Copiez (Ctrl+C) et collez (Ctrl+V) dans")
    print("     votre tableau 'Suivi_Commandes.xlsx'")
    print("     à la première ligne vide disponible")
    print("=" * 56)

    input("\nAppuyez sur Entrée pour fermer…")


if __name__ == "__main__":
    main()

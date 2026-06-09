#!/opt/homebrew/bin/python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
import glob
import json
from datetime import datetime

app = Flask(__name__, template_folder="templates")
DOSSIER = os.path.dirname(os.path.abspath(__file__))
STATUT_COL = "Statut Traitement"
STATUTS = ["A faire", "En cours", "Traité"]
MASTER_FILE = "suivi_master.csv"
HISTORY_FILE = "import_history.json"

COLONNES = [
    "Source", "N° Commande", "Date Commande", "Société / Client",
    "Statut", "Code Produit", "Libellé Produit", "Quantité",
    "Total HT", "Total TTC", "Contact Nom", "Contact Prénom",
    "Contact Email", "Contact Mobile", "Semaine Import",
]


# ── Utilitaires ────────────────────────────────────────────────

def semaine_courante():
    n = datetime.now()
    return f"S{n.isocalendar()[1]:02d}-{n.year}"

def nettoyer_montant(s):
    if pd.isna(s) or str(s).strip() in ("", "0"):
        return ""
    s = str(s).replace("€","").replace("\xa0","").replace(" ","").replace(",",".").strip()
    try:
        return float(s)
    except ValueError:
        return s

def col(df, *noms):
    for n in noms:
        if n in df.columns:
            return df[n].fillna("").astype(str)
    return pd.Series([""] * len(df))

def lire_csv_brut(chemin):
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(chemin, sep=";", encoding=enc, dtype=str)
            df.columns = [c.lstrip("﻿") for c in df.columns]
            return df, enc
        except Exception:
            continue
    raise ValueError(f"Impossible de lire : {chemin}")

def lire_csv(chemin):
    df, _ = lire_csv_brut(chemin)
    if STATUT_COL not in df.columns:
        df[STATUT_COL] = "A faire"
    df[STATUT_COL] = df[STATUT_COL].fillna("A faire")
    return df

def sauvegarder_csv(df, chemin):
    df.to_csv(chemin, sep=";", index=False, encoding="utf-8-sig")

def df_to_records(df):
    df = df.fillna("").copy()
    records = []
    for i, row in df.iterrows():
        rec = row.to_dict()
        rec["_index"] = i
        records.append(rec)
    return records

def trouver_csvs():
    master = os.path.join(DOSSIER, MASTER_FILE)
    files = [master] if os.path.exists(master) else []
    for pattern in ["commandes_normalisees_*.csv", "commandes_Klipso*normalisees_*.csv"]:
        files += sorted(glob.glob(os.path.join(DOSSIER, pattern)), key=os.path.getmtime, reverse=True)
    seen, result = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


# ── Normalisation ──────────────────────────────────────────────

def normaliser_klipso(chemin):
    df, _ = lire_csv_brut(chemin)
    return pd.DataFrame({
        "Source":           pd.Series(["Klipso"] * len(df)),
        "N° Commande":      col(df, "N° de commande (Commande)"),
        "Date Commande":    col(df, "Date de commande (Commande)"),
        "Société / Client": col(df, "Concerne (Commande)"),
        "Statut":           col(df, "État (Commande)"),
        "Code Produit":     col(df, "Code (Produit)"),
        "Libellé Produit":  col(df, "Libellé en Français (Produit)"),
        "Quantité":         col(df, "Qté 1"),
        "Total HT":         col(df, "Total HT brut").apply(nettoyer_montant),
        "Total TTC":        col(df, "Total TTC net (devise comptable)").apply(nettoyer_montant),
        "Contact Nom":      col(df, "Nom (Commande > Dossier exposant > Contact participation)"),
        "Contact Prénom":   col(df, "Prénom (Commande > Dossier exposant > Contact participation)"),
        "Contact Email":    col(df, "Email (Commande > Dossier exposant > Contact participation)"),
        "Contact Mobile":   col(df, "Téléphone mobile (Commande > Dossier exposant > Contact participation)"),
        "Semaine Import":   semaine_courante(),
    })[COLONNES]

def normaliser_expose(chemin):
    df, _ = lire_csv_brut(chemin)
    return pd.DataFrame({
        "Source":           pd.Series(["Expose"] * len(df)),
        "N° Commande":      col(df, "no_cde_fournisseur", "no_facture"),
        "Date Commande":    col(df, "date_initiale_commande", "date_maj"),
        "Société / Client": col(df, "enseigne_participant", "société", "societe"),
        "Statut":           col(df, "statut_client", "statut fournisseur"),
        "Code Produit":     col(df, "reference_produit", "reference", "sku"),
        "Libellé Produit":  col(df, "produit_fournisseur"),
        "Quantité":         col(df, "quantité", "quantite"),
        "Total HT":         col(df, "prix_achat_HT_total").apply(nettoyer_montant),
        "Total TTC":        pd.Series([""] * len(df)),
        "Contact Nom":      col(df, "nom_livraison"),
        "Contact Prénom":   col(df, "prénom_livraison", "prenom_livraison"),
        "Contact Email":    pd.Series([""] * len(df)),
        "Contact Mobile":   col(df, "mobile_livraison"),
        "Semaine Import":   semaine_courante(),
    })[COLONNES]


# ── Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    csvs = trouver_csvs()
    noms = [os.path.basename(f) for f in csvs]
    return render_template("index.html", csvs=noms)


@app.route("/api/data")
def api_data():
    fichier = request.args.get("fichier", MASTER_FILE)
    chemin = os.path.join(DOSSIER, fichier)
    if not os.path.exists(chemin):
        csvs = trouver_csvs()
        if not csvs:
            return jsonify({"error": "Aucun CSV trouvé"}), 404
        chemin = csvs[0]
    df = lire_csv(chemin)
    return jsonify({
        "fichier": os.path.basename(chemin),
        "lignes": len(df),
        "records": df_to_records(df),
        "statuts": STATUTS,
    })


@app.route("/api/update", methods=["POST"])
def api_update():
    data = request.json
    fichier = data.get("fichier")
    index = int(data.get("index"))
    nouveau_statut = data.get("statut")
    if nouveau_statut not in STATUTS:
        return jsonify({"error": "Statut invalide"}), 400
    chemin = os.path.join(DOSSIER, fichier)
    if not os.path.exists(chemin):
        return jsonify({"error": "Fichier introuvable"}), 404
    df = lire_csv(chemin)
    if index < 0 or index >= len(df):
        return jsonify({"error": "Index invalide"}), 400
    df.at[index, STATUT_COL] = nouveau_statut
    sauvegarder_csv(df, chemin)
    return jsonify({"ok": True})


@app.route("/api/update_batch", methods=["POST"])
def api_update_batch():
    data = request.json
    fichier = data.get("fichier")
    updates = data.get("updates", [])
    chemin = os.path.join(DOSSIER, fichier)
    if not os.path.exists(chemin):
        return jsonify({"error": "Fichier introuvable"}), 404
    df = lire_csv(chemin)
    for u in updates:
        idx = int(u.get("index"))
        statut = u.get("statut")
        if statut in STATUTS and 0 <= idx < len(df):
            df.at[idx, STATUT_COL] = statut
    sauvegarder_csv(df, chemin)
    return jsonify({"ok": True, "updated": len(updates)})


@app.route("/api/import", methods=["POST"])
def api_import():
    klipso_file = request.files.get("klipso")
    expose_file = request.files.get("expose")
    frames, errors, sources = [], [], []

    def process(f, normalizer, label):
        temp = os.path.join(DOSSIER, f"_temp_{label}.csv")
        try:
            f.save(temp)
            df = normalizer(temp)
            frames.append(df)
            sources.append(label)
        except Exception as e:
            errors.append(f"{label} : {e}")
        finally:
            if os.path.exists(temp):
                os.remove(temp)

    if klipso_file and klipso_file.filename:
        process(klipso_file, normaliser_klipso, "Klipso")
    if expose_file and expose_file.filename:
        process(expose_file, normaliser_expose, "Expose")

    if not frames:
        return jsonify({"error": "Aucun fichier traité", "details": errors}), 400

    new_df = pd.concat(frames, ignore_index=True)
    new_df[STATUT_COL] = "A faire"

    master_path = os.path.join(DOSSIER, MASTER_FILE)
    if os.path.exists(master_path):
        master_df = lire_csv(master_path)
        existing = set(master_df["N° Commande"].str.strip())
        new_rows = new_df[~new_df["N° Commande"].str.strip().isin(existing)].copy()
        new_orders = int(new_rows["N° Commande"].nunique())
        skipped = int(new_df[new_df["N° Commande"].str.strip().isin(existing)]["N° Commande"].nunique())
        merged = pd.concat([master_df, new_rows], ignore_index=True)
    else:
        new_rows = new_df
        new_orders = int(new_df["N° Commande"].nunique())
        skipped = 0
        merged = new_df

    sauvegarder_csv(merged, master_path)

    result = {
        "ok": True,
        "sources": sources,
        "nouvelles_lignes": int(len(new_rows)),
        "nouvelles_commandes": new_orders,
        "commandes_ignorees": skipped,
        "total_lignes": int(len(merged)),
        "errors": errors,
    }

    # Enregistrer dans l'historique
    history_path = os.path.join(DOSSIER, HISTORY_FILE)
    history = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.insert(0, {
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "sources": sources,
        "nouvelles_commandes": new_orders,
        "nouvelles_lignes": int(len(new_rows)),
        "commandes_ignorees": skipped,
        "total_lignes": int(len(merged)),
    })
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return jsonify(result)


@app.route("/api/import_history")
def api_import_history():
    history_path = os.path.join(DOSSIER, HISTORY_FILE)
    if not os.path.exists(history_path):
        return jsonify([])
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])


if __name__ == "__main__":
    import webbrowser, threading, time
    def ouvrir(): time.sleep(1); webbrowser.open("http://127.0.0.1:5050")
    threading.Thread(target=ouvrir, daemon=True).start()
    print("\n" + "="*50)
    print("  Suivi Commandes — Interface locale")
    print("  http://127.0.0.1:5050")
    print("  Ctrl+C pour arrêter")
    print("="*50 + "\n")
    app.run(port=5050, debug=False)

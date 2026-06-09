#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import glob
import json
import logging
from datetime import datetime

import pandas as pd
from flask import Flask, render_template, jsonify, request

# ── Chemins de base (gère le mode "frozen" PyInstaller) ──────
if getattr(sys, "frozen", False):
    # App compilée : ressources dans le répertoire temporaire de PyInstaller
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Répertoire des données utilisateur ───────────────────────
def _get_data_dir():
    if os.environ.get("SUIVI_DATA"):
        return os.environ["SUIVI_DATA"]
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        else:
            base = os.path.expanduser("~/Library/Application Support")
        return os.path.join(base, "SuiviCommandes")
    # Mode développement : dossier du script
    return os.path.dirname(os.path.abspath(__file__))

DOSSIER = _get_data_dir()
os.makedirs(DOSSIER, exist_ok=True)

# ── Logging vers fichier quand compilé ───────────────────────
if getattr(sys, "frozen", False):
    logging.basicConfig(
        filename=os.path.join(DOSSIER, "app.log"),
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
STATUT_COL = "Statut Traitement"
STATUTS = ["A faire", "En cours", "Traité"]
MASTER_FILE    = "suivi_master.csv"
HISTORY_FILE   = "import_history.json"
PRESETS_FILE   = "product_presets.json"
PRODUCTS_REF   = "produits_reference.csv"

# Preset "produits-SPACE" : Communication sauf ces 4 codes + 3 ajouts
_SPACE_EXCLUS = {"HA851", "LO819", "MI852", "MI853"}
_SPACE_AJOUTS = {"LO881", "SA880", "SP860"}

COLONNES = [
    "Source", "N° Commande", "Date Commande", "Société / Client",
    "Facturé à",
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
        "Facturé à":        col(df, "Facturé à (Commande)"),
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
        "Facturé à":        col(df, "societe_facturation", "facture_a", "facturé à"),
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


# ── Produits & Presets ────────────────────────────────────────

def _ref_path():
    """Cherche le fichier de référence produits : données > bundle > script."""
    for p in [
        os.path.join(DOSSIER, PRODUCTS_REF),
        os.path.join(BASE_DIR, PRODUCTS_REF),          # bundlé par PyInstaller
        os.path.join(os.path.dirname(os.path.abspath(__file__)), PRODUCTS_REF),
    ]:
        if os.path.exists(p):
            return p
    return None

def lire_produits_reference():
    path = _ref_path()
    if not path:
        return None
    df, _ = lire_csv_brut(path)
    df.columns = [c.strip().strip('"') for c in df.columns]
    return df

def construire_preset_space():
    df = lire_produits_reference()
    if df is None:
        return []
    fam_col  = next((c for c in df.columns if "famille"  in c.lower()), None)
    code_col = next((c for c in df.columns if c.lower() == "code"),     None)
    if not fam_col or not code_col:
        return []
    comm   = df[df[fam_col].str.strip().str.lower() == "communication"]
    codes  = {c.strip().strip('"') for c in comm[code_col].dropna() if c.strip().strip('"')}
    codes -= _SPACE_EXCLUS
    codes |= _SPACE_AJOUTS
    return sorted(codes)

def lire_presets():
    path = os.path.join(DOSSIER, PRESETS_FILE)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def sauver_presets(p):
    with open(os.path.join(DOSSIER, PRESETS_FILE), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)

def init_presets():
    if not os.path.exists(os.path.join(DOSSIER, PRESETS_FILE)):
        codes = construire_preset_space()
        sauver_presets({"produits-SPACE": codes} if codes else {})


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


@app.route("/api/products")
def api_products():
    df = lire_produits_reference()
    if df is not None:
        code_col  = next((c for c in df.columns if c.lower() == "code"),                None)
        label_col = next((c for c in df.columns if "lib" in c.lower()),                 None)
        fam_col   = next((c for c in df.columns if "famille" in c.lower()),             None)
        if code_col:
            result = []
            for _, row in df.iterrows():
                code  = str(row[code_col]).strip().strip('"')
                label = str(row[label_col]).strip().strip('"') if label_col else ""
                fam   = str(row[fam_col]).strip().strip('"')   if fam_col  else ""
                if code and code.lower() not in ("nan", "") and fam.lower() != "nan":
                    result.append({"code": code, "label": label, "famille": fam or "Autres"})
            return jsonify(result)

    # Fallback : extraire du master
    master_path = os.path.join(DOSSIER, MASTER_FILE)
    if os.path.exists(master_path):
        df_m = lire_csv(master_path)
        seen, result = set(), []
        for _, row in df_m[["Code Produit","Libellé Produit"]].drop_duplicates().iterrows():
            c = str(row["Code Produit"]).strip()
            if c and c not in seen:
                seen.add(c)
                result.append({"code": c, "label": str(row["Libellé Produit"]).strip(), "famille": ""})
        return jsonify(sorted(result, key=lambda x: x["code"]))
    return jsonify([])


@app.route("/api/presets", methods=["GET"])
def api_get_presets():
    return jsonify(lire_presets())


@app.route("/api/presets", methods=["POST"])
def api_save_preset():
    data  = request.json
    name  = (data.get("name") or "").strip()
    codes = data.get("codes", [])
    if not name:
        return jsonify({"error": "Nom manquant"}), 400
    p = lire_presets()
    p[name] = sorted(set(codes))
    sauver_presets(p)
    return jsonify({"ok": True, "count": len(codes)})


@app.route("/api/presets/<name>", methods=["DELETE"])
def api_delete_preset(name):
    p = lire_presets()
    if name in p:
        del p[name]
        sauver_presets(p)
    return jsonify({"ok": True})


def find_free_port(start=5050):
    import socket
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


if __name__ == "__main__":
    import webbrowser, threading, time
    init_presets()

    PORT = find_free_port(5050)
    URL  = f"http://127.0.0.1:{PORT}"

    def ouvrir():
        time.sleep(1.5)
        webbrowser.open(URL)

    threading.Thread(target=ouvrir, daemon=True).start()

    frozen = getattr(sys, "frozen", False)

    if not frozen:
        print(f"\n{'='*50}")
        print("  Suivi Commandes — Interface locale")
        print(f"  {URL}")
        print("  Ctrl+C pour arrêter")
        print(f"{'='*50}\n")

    # Waitress (serveur de production) quand compilé sur Windows
    if frozen and sys.platform == "win32":
        try:
            from waitress import serve
            serve(app, host="127.0.0.1", port=PORT, threads=4)
        except Exception as e:
            logging.error(f"Waitress error: {e}")
    else:
        app.run(host="127.0.0.1", port=PORT, debug=False)

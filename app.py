import json
import sqlite3
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "maliyet.db"

app = Flask(__name__)

GUMRUK_ORAN_1 = 0.037
GUMRUK_ORAN_2 = 0.23
KDV_ORAN = 0.20


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kayitlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            olusturma TEXT NOT NULL,
            urun TEXT NOT NULL,
            adet REAL NOT NULL,
            mal_birim_usd REAL NOT NULL,
            kargo_usd REAL NOT NULL,
            yurtici_usd REAL NOT NULL,
            damga_usd REAL NOT NULL,
            ham_usd REAL NOT NULL,
            cif_usd REAL NOT NULL,
            gumruk1_usd REAL NOT NULL,
            gumruk2_usd REAL NOT NULL,
            kdv_matrah_usd REAL NOT NULL,
            kdv_usd REAL NOT NULL,
            toplam_vergi_usd REAL NOT NULL,
            toplam_maliyet_usd REAL NOT NULL,
            birim_maliyet_usd REAL NOT NULL,
            usd_try REAL NOT NULL,
            toplam_maliyet_tl REAL NOT NULL,
            birim_maliyet_tl REAL NOT NULL,
            ham_tl REAL NOT NULL,
            json_detay TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def usd_try_kur():
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD", timeout=8
        )
        r.raise_for_status()
        return float(r.json()["rates"]["TRY"])
    except Exception:
        try:
            r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
            r.raise_for_status()
            return float(r.json()["rates"]["TRY"])
        except Exception:
            return 34.50


def hesapla(adet, mal_birim_usd, kargo_usd, yurtici_usd, damga_usd):
    ham = adet * mal_birim_usd
    cif = ham + kargo_usd
    g1 = cif * GUMRUK_ORAN_1
    g2 = cif * GUMRUK_ORAN_2
    kdv_matrah = cif + g1 + yurtici_usd
    kdv = kdv_matrah * KDV_ORAN
    toplam_vergi = g1 + g2 + kdv + damga_usd
    toplam_maliyet = cif + yurtici_usd + g1 + g2 + kdv + damga_usd
    birim = toplam_maliyet / adet if adet else 0.0
    detay = {
        "ham_usd": round(ham, 2),
        "cif_usd": round(cif, 2),
        "gumruk_yuzde_3_7_usd": round(g1, 2),
        "ilave_gumruk_yuzde_23_usd": round(g2, 2),
        "yurtici_usd": round(yurtici_usd, 2),
        "kdv_matrah_usd": round(kdv_matrah, 2),
        "kdv_yuzde_20_usd": round(kdv, 2),
        "damga_usd": round(damga_usd, 2),
        "toplam_vergi_usd": round(toplam_vergi, 2),
        "toplam_maliyet_usd": round(toplam_maliyet, 2),
        "birim_maliyet_usd": round(birim, 4),
    }
    return detay


@app.route("/")
def index():
    return send_from_directory(BASE, "index.html")


@app.route("/api/kur")
def api_kur():
    return jsonify({"usd_try": round(usd_try_kur(), 4)})


@app.route("/api/hesapla", methods=["POST"])
def api_hesapla():
    d = request.get_json(force=True, silent=True) or {}
    try:
        adet = float(d.get("adet", 0))
        mal_birim = float(d.get("mal_birim_usd", 0))
        kargo = float(d.get("kargo_usd", 0))
        yurtici = float(d.get("yurtici_usd", 200))
        damga = float(d.get("damga_usd", 37))
    except (TypeError, ValueError):
        return jsonify({"hata": "Sayısal alanlar geçersiz"}), 400
    if adet <= 0 or mal_birim < 0 or kargo < 0 or yurtici < 0 or damga < 0:
        return jsonify({"hata": "Adet pozitif, diğer tutarlar negatif olamaz"}), 400
    kur = usd_try_kur()
    detay = hesapla(adet, mal_birim, kargo, yurtici, damga)
    detay["usd_try"] = round(kur, 4)
    detay["ham_tl"] = round(detay["ham_usd"] * kur, 2)
    detay["toplam_maliyet_tl"] = round(detay["toplam_maliyet_usd"] * kur, 2)
    detay["birim_maliyet_tl"] = round(detay["birim_maliyet_usd"] * kur, 2)
    return jsonify(detay)


@app.route("/api/kayitlar", methods=["GET"])
def kayitlar_liste():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, olusturma, urun, adet, toplam_maliyet_usd, birim_maliyet_usd, toplam_maliyet_tl FROM kayitlar ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/kayitlar", methods=["POST"])
def kayit_ekle():
    d = request.get_json(force=True, silent=True) or {}
    urun = (d.get("urun") or "").strip()
    if not urun:
        return jsonify({"hata": "Ürün adı gerekli"}), 400
    try:
        adet = float(d.get("adet", 0))
        mal_birim = float(d.get("mal_birim_usd", 0))
        kargo = float(d.get("kargo_usd", 0))
        yurtici = float(d.get("yurtici_usd", 200))
        damga = float(d.get("damga_usd", 37))
    except (TypeError, ValueError):
        return jsonify({"hata": "Sayısal alanlar geçersiz"}), 400
    if adet <= 0:
        return jsonify({"hata": "Adet pozitif olmalı"}), 400
    kur = usd_try_kur()
    detay = hesapla(adet, mal_birim, kargo, yurtici, damga)
    detay["usd_try"] = round(kur, 4)
    ham_tl = round(detay["ham_usd"] * kur, 2)
    toplam_tl = round(detay["toplam_maliyet_usd"] * kur, 2)
    birim_tl = round(detay["birim_maliyet_usd"] * kur, 2)
    detay["ham_tl"] = ham_tl
    detay["toplam_maliyet_tl"] = toplam_tl
    detay["birim_maliyet_tl"] = birim_tl
    olusturma = datetime.utcnow().isoformat() + "Z"
    conn = get_db()
    cur = conn.execute(
        """
        INSERT INTO kayitlar (
            olusturma, urun, adet, mal_birim_usd, kargo_usd, yurtici_usd, damga_usd,
            ham_usd, cif_usd, gumruk1_usd, gumruk2_usd, kdv_matrah_usd, kdv_usd,
            toplam_vergi_usd, toplam_maliyet_usd, birim_maliyet_usd, usd_try,
            toplam_maliyet_tl, birim_maliyet_tl, ham_tl, json_detay
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            olusturma,
            urun,
            adet,
            mal_birim,
            kargo,
            yurtici,
            damga,
            detay["ham_usd"],
            detay["cif_usd"],
            detay["gumruk_yuzde_3_7_usd"],
            detay["ilave_gumruk_yuzde_23_usd"],
            detay["kdv_matrah_usd"],
            detay["kdv_yuzde_20_usd"],
            detay["toplam_vergi_usd"],
            detay["toplam_maliyet_usd"],
            detay["birim_maliyet_usd"],
            kur,
            toplam_tl,
            birim_tl,
            ham_tl,
            json.dumps(detay, ensure_ascii=False),
        ),
    )
    conn.commit()
    yeni_id = cur.lastrowid
    conn.close()
    return jsonify({"id": yeni_id, "mesaj": "Kaydedildi"})


@app.route("/api/kayitlar/<int:kid>", methods=["DELETE"])
def kayit_sil(kid):
    conn = get_db()
    conn.execute("DELETE FROM kayitlar WHERE id = ?", (kid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


init_db()

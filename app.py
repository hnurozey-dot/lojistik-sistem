from flask import Flask, render_template, request, redirect, session, send_from_directory, send_file
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime, timedelta
import os
import pandas as pd

from models import db, Firma, Sefer, CariFirma, CariNakliyeci, Fatura

app = Flask(__name__)
app.secret_key = "lojistik123"

# DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lojistik.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# upload
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)

# login user
user = {"username": "admin", "password": "1234"}


# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == user["username"] and request.form["password"] == user["password"]:
            session["user"] = "admin"
            return redirect("/dashboard")
        return "Hatalı giriş"
    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    seferler = Sefer.query.all()
    firmalar = Firma.query.all()
    cariler_f = CariFirma.query.all()
    cariler_n = CariNakliyeci.query.all()

    gelir = sum([s.gelir for s in seferler])
    gider = sum([s.gider for s in seferler])

    return render_template(
        "dashboard.html",
        seferler=seferler,
        firmalar=firmalar,
        cariler_f=cariler_f,
        cariler_n=cariler_n,
        gelir=gelir,
        gider=gider,
        kar=gelir - gider
    )


# ---------------- FİRMA EKLE ----------------
@app.route("/firma-ekle", methods=["POST"])
def firma_ekle():
    if "user" not in session:
        return redirect("/login")

    db.session.add(Firma(ad=request.form["ad"]))
    db.session.commit()

    return redirect("/dashboard")


# ---------------- SEFER EKLE + VADE ----------------
@app.route("/sefer-ekle", methods=["POST"])
def sefer_ekle():
    if "user" not in session:
        return redirect("/login")

    gelir = float(request.form["gelir"])
    gider = float(request.form["gider"])

    firma = request.form["firma"]
    nakliyeci = request.form["nakliyeci"]

    vade_firma = datetime.now() + timedelta(days=20)
    vade_nakliyeci = datetime.now() + timedelta(days=20)

    db.session.add(Sefer(
        firma=firma,
        nakliyeci=nakliyeci,
        plaka=request.form["plaka"],
        rota=request.form["rota"],
        gelir=gelir,
        gider=gider,
        kar=gelir - gider
    ))

    # FIRMA CARİ
    c1 = CariFirma.query.filter_by(firma=firma).first()
    if not c1:
        c1 = CariFirma(firma=firma, alacak=0, vade_tarihi=vade_firma)

    c1.alacak += gelir
    c1.vade_tarihi = vade_firma

    # NAKLİYECİ CARİ
    c2 = CariNakliyeci.query.filter_by(nakliyeci=nakliyeci).first()
    if not c2:
        c2 = CariNakliyeci(nakliyeci=nakliyeci, borc=0, vade_tarihi=vade_nakliyeci)

    c2.borc += gider
    c2.vade_tarihi = vade_nakliyeci

    db.session.add_all([c1, c2])
    db.session.commit()

    return redirect("/dashboard")


# ---------------- FATURA YÜKLE ----------------
@app.route("/fatura-yukle", methods=["POST"])
def fatura_yukle():
    if "user" not in session:
        return redirect("/login")

    firma = request.form.get("firma")
    tip = request.form.get("tip")
    tutar = float(request.form.get("tutar", 0))

    pdf = request.files["pdf"]
    filename = secure_filename(pdf.filename)

    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    pdf.save(path)

    db.session.add(Fatura(
        firma=firma,
        tip=tip,
        dosya=filename,
        tutar=tutar
    ))
    db.session.commit()

    return redirect("/dashboard")


# ---------------- FATURALAR ----------------
@app.route("/faturalar")
def faturalar():
    if "user" not in session:
        return redirect("/login")

    data = Fatura.query.order_by(Fatura.tarih.desc()).all()
    return render_template("faturalar.html", faturalar=data)


# ---------------- ARAMA ----------------
@app.route("/ara")
def ara():
    if "user" not in session:
        return redirect("/login")

    q = request.args.get("q", "")

    seferler = Sefer.query.filter(
        Sefer.firma.contains(q) |
        Sefer.nakliyeci.contains(q) |
        Sefer.plaka.contains(q)
    ).all()

    return render_template("arama.html", seferler=seferler, q=q)


# ---------------- EXCEL ----------------
@app.route("/excel-haftalik")
def excel_haftalik():
    if "user" not in session:
        return redirect("/login")

    start = request.args.get("start")
    end = request.args.get("end")

    query = Sefer.query

    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        query = query.filter(Sefer.tarih.between(start_date, end_date))

    seferler = query.all()

    data = [{
        "Firma": s.firma,
        "Nakliyeci": s.nakliyeci,
        "Plaka": s.plaka,
        "Rota": s.rota,
        "Gelir": s.gelir,
        "Gider": s.gider,
        "Kar": s.kar,
        "Tarih": s.tarih
    } for s in seferler]

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Rapor")

    output.seek(0)

    return send_file(
        output,
        download_name="rapor.xlsx",
        as_attachment=True
    )


# ---------------- CARİ ÖDEME ----------------
@app.route("/firma-tahsilat", methods=["POST"])
def firma_tahsilat():
    if "user" not in session:
        return redirect("/login")

    firma = request.form.get("firma")
    tutar = float(request.form.get("tutar", 0))

    cari = CariFirma.query.filter_by(firma=firma).first()

    if cari:
        cari.alacak -= tutar
        if cari.alacak < 0:
            cari.alacak = 0
        db.session.commit()

    return redirect("/dashboard")


@app.route("/nakliyeci-odeme", methods=["POST"])
def nakliyeci_odeme():
    if "user" not in session:
        return redirect("/login")

    nakliyeci = request.form.get("nakliyeci")
    tutar = float(request.form.get("tutar", 0))

    cari = CariNakliyeci.query.filter_by(nakliyeci=nakliyeci).first()

    if cari:
        cari.borc -= tutar
        if cari.borc < 0:
            cari.borc = 0
        db.session.commit()

    return redirect("/dashboard")


# ---------------- UPLOAD SERVE ----------------
@app.route("/uploads/<filename>")
def uploads(filename):
    return send_from_directory("uploads", filename)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
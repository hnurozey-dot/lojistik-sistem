from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Firma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(150), unique=True)


class Sefer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    firma = db.Column(db.String(150))
    nakliyeci = db.Column(db.String(150))

    plaka = db.Column(db.String(50))
    rota = db.Column(db.String(200))

    gelir = db.Column(db.Float)
    gider = db.Column(db.Float)
    kar = db.Column(db.Float)

    tarih = db.Column(db.DateTime, default=datetime.utcnow)

class CariFirma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firma = db.Column(db.String(150), unique=True)
    alacak = db.Column(db.Float, default=0)


class CariNakliyeci(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nakliyeci = db.Column(db.String(150), unique=True)
    borc = db.Column(db.Float, default=0)


class Fatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    firma = db.Column(db.String(150))
    tip = db.Column(db.String(20))  # musteri / nakliyeci

    dosya = db.Column(db.String(255))

    tutar = db.Column(db.Float, default=0)

    tarih = db.Column(db.DateTime, default=datetime.utcnow)
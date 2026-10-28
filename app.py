"""Nordexa Digital – nettside.

Start lokalt:   .venv/bin/python app.py     ->  http://127.0.0.1:5001
Innhold:        tekst, priser, prosjekter og spørsmål ligger i innhold.py
Innstillinger:  kopier .env.example til .env og fyll inn (valgfritt lokalt)
Mer hjelp:      se LESMEG.md
"""

import json
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

from flask import (
    Flask, Response, abort, flash, redirect, render_template, request, url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user,
    logout_user,
)
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import func, inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

import analyse
import innhold

try:  # .env er valgfritt – uten python-dotenv brukes bare miljøvariabler
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

try:
    from zoneinfo import ZoneInfo
    OSLO = ZoneInfo("Europe/Oslo")
except Exception:  # mangler tidssonedata -> vis UTC
    OSLO = None

app = Flask(__name__)


# =======================
# INNSTILLINGER
# =======================

def env(name, default=""):
    return os.environ.get(name, default).strip()


def load_secret_key():
    """Hemmelig nøkkel fra miljøet, ellers en som lages én gang og lagres i instance/."""
    key = env("SECRET_KEY")
    if key:
        return key
    path = os.path.join(app.instance_path, "secret_key")
    try:
        with open(path) as fh:
            key = fh.read().strip()
        if key:
            return key
    except OSError:
        pass
    key = secrets.token_hex(32)
    os.makedirs(app.instance_path, exist_ok=True)
    with open(path, "w") as fh:
        fh.write(key)
    return key


app.secret_key = load_secret_key()

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Sett COOKIE_SECURE=1 i .env når siden ligger på HTTPS
app.config["SESSION_COOKIE_SECURE"] = env("COOKIE_SECURE") == "1"
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # skjemaene er små
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30  # filene får ny adresse når de endres

database_url = env("DATABASE_URL", "sqlite:///database.db")
if database_url.startswith("postgres://"):  # eldre skrivemåte fra noen leverandører
    database_url = "postgresql://" + database_url[len("postgres://"):]
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if env("BEHIND_PROXY") == "1":  # på Railway, Render og lignende
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

SITE = {
    "name": "Nordexa Digital",
    "slagord": "Din vekst er vår største glede.",
    "email": env("CONTACT_EMAIL", "nordexadigital.no@gmail.com"),
    "phone": "+47 462 22 985",
    "phone_href": "+4746222985",
    "address": "Oslo, Norge",
    "org_nr": env("ORG_NR"),               # vises i bunnteksten når den er fylt inn
    "prisnote": env("PRICE_NOTE"),         # f.eks. «Alle priser er oppgitt eks. mva.»
    "linkedin": env("LINKEDIN_URL"),
    "instagram": env("INSTAGRAM_URL"),
    "url": env("SITE_URL").rstrip("/"),    # f.eks. https://nordexadigital.no
}

app.config["MAIL_SERVER"] = env("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(env("MAIL_PORT", "587"))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = env("MAIL_USERNAME", SITE["email"])
app.config["MAIL_PASSWORD"] = env("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]
MAIL_ENABLED = bool(app.config["MAIL_PASSWORD"])

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")
db = SQLAlchemy(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Logg inn for å se denne siden."
login_manager.login_message_category = "feil"


# =======================
# MODELLER
# =======================

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    topic = db.Column(db.String(60))
    meeting = db.Column(db.String(40))   # ønsket møtetid, hvis kunden foreslo en


class Audit(db.Model):
    """En gratis nettsideanalyse noen har bestilt."""
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(40), unique=True, nullable=False)
    url = db.Column(db.String(300), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    report = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class PageView(db.Model):
    """Én sidevisning. Ingen IP-adresse, ingen informasjonskapsel, ingenting som peker på en person."""
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(120), nullable=False, index=True)
    referrer = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)


class Event(db.Model):
    """Et klikk på en av knappene vi vil måle, f.eks. «Få en gratis vurdering»."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def init_db():
    """Lager tabeller, oppgraderer eldre databaser og sørger for at admin finnes."""
    db.create_all()

    columns = [c["name"] for c in inspect(db.engine).get_columns("contact")]
    for name, kind in (("created_at", "TIMESTAMP"), ("topic", "VARCHAR(60)"), ("meeting", "VARCHAR(40)")):
        if name not in columns:
            db.session.execute(text("ALTER TABLE contact ADD COLUMN %s %s" % (name, kind)))
    db.session.commit()

    if not User.query.filter_by(username="admin").first():
        password = env("ADMIN_PASSWORD")
        generated = not password
        if generated:
            password = secrets.token_urlsafe(12)
        db.session.add(User(
            username="admin",
            password=generate_password_hash(password, method="pbkdf2:sha256"),
        ))
        db.session.commit()
        if generated:
            print("\n  Admin-bruker opprettet.  Brukernavn: admin   Passord: %s"
                  "\n  Skriv det ned – det vises bare denne ene gangen.\n" % password)


# =======================
# FELLES FOR ALLE MALER
# =======================

NAV = [
    ("tjenester", "Tjenester"),
    ("prosjekter", "Prosjekter"),
    ("priser", "Priser"),
    ("om_oss", "Om oss"),
    ("blogg", "Blogg"),
]

MONTHS = ["januar", "februar", "mars", "april", "mai", "juni", "juli",
          "august", "september", "oktober", "november", "desember"]


def asset(filename):
    """Adresse til en statisk fil, med et versjonsnummer som endres når filen endres."""
    try:
        version = int(os.path.getmtime(os.path.join(app.static_folder, filename)))
    except OSError:
        version = 0
    return url_for("static", filename=filename, v=version)


def site_root():
    return SITE["url"] or request.url_root.rstrip("/")


@app.context_processor
def inject_globals():
    return {
        "site": SITE, "nav": NAV, "year": datetime.now().year, "asset": asset,
        "tjenester": innhold.TJENESTER, "canonical": site_root() + request.path,
        "site_root": site_root(),
    }


@app.template_filter("dato")
def dato(value):
    if not value:
        return "Ukjent dato"
    if OSLO is not None:
        value = value.replace(tzinfo=timezone.utc).astimezone(OSLO)
    return value.strftime("%d.%m.%Y kl. %H:%M")


@app.template_filter("langdato")
def langdato(iso):
    d = date.fromisoformat(iso)
    return "%d. %s %d" % (d.day, MONTHS[d.month - 1], d.year)


@app.template_filter("tojson_ld")
def tojson_ld(value):
    """JSON som trygt kan stå inne i en <script>-blokk."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


# =======================
# SIDER
# =======================

@app.route("/")
def home():
    return render_template(
        "index.html", prosjekter=innhold.PROSJEKTER, hvorfor=innhold.HVORFOR,
        prosess=innhold.PROSESS, pakker=innhold.PAKKER, faq=innhold.FAQ,
        teknologi=innhold.TEKNOLOGI, omtaler=innhold.OMTALER)


@app.route("/tjenester")
def tjenester():
    return render_template("tjenester.html")


@app.route("/prosjekter")
def prosjekter():
    return render_template("prosjekter.html", prosjekter=innhold.PROSJEKTER, omtaler=innhold.OMTALER)


@app.route("/prosjekter/<slug>")
def prosjekt(slug):
    for index, item in enumerate(innhold.PROSJEKTER):
        if item["slug"] == slug:
            neste = innhold.PROSJEKTER[(index + 1) % len(innhold.PROSJEKTER)]
            return render_template("prosjekt.html", p=item, neste=neste)
    abort(404)


@app.route("/referanser")
def referanser():  # gammel adresse
    return redirect(url_for("prosjekter"), code=301)


@app.route("/priser")
def priser():
    return render_template("priser.html", pakker=innhold.PAKKER, faq=innhold.FAQ)


@app.route("/prosess")
def prosess():
    return render_template("prosess.html", prosess=innhold.PROSESS)


@app.route("/om-oss")
def om_oss():
    har_bilde = os.path.exists(os.path.join(app.static_folder, "img", "nima.webp"))
    return render_template("om-oss.html", hvorfor=innhold.HVORFOR, har_bilde=har_bilde,
                           teknologi=innhold.TEKNOLOGI)


@app.route("/blogg")
def blogg():
    return render_template("blogg.html", innlegg=innhold.INNLEGG)


@app.route("/blogg/<slug>")
def blogginnlegg(slug):
    for item in innhold.INNLEGG:
        if item["slug"] == slug:
            andre = [i for i in innhold.INNLEGG if i["slug"] != slug][:2]
            return render_template("blogginnlegg.html", innlegg=item, andre=andre)
    abort(404)


@app.route("/personvern")
def personvern():
    return render_template("personvern.html")


@app.route("/vilkar")
def vilkar():
    return render_template("vilkar.html")


# =======================
# SØK
# =======================

def build_search_index():
    index = [
        {"url": "/", "title": "Forside",
         "text": "Vi bygger nettsider som gjør besøkende til kunder.",
         "keywords": "forside hjem start nordexa digital"},
        {"url": "/tjenester", "title": "Tjenester",
         "text": "Nettsider, webapplikasjoner, nettbutikk, UX/UI-design, optimalisering og vedlikehold.",
         "keywords": "tjeneste tjenester nettside nettsider nettbutikk netthandel e-handel betaling "
                     "seo google webapplikasjon app design ux ui optimalisering hastighet vedlikehold drift"},
        {"url": "/prosjekter", "title": "Prosjekter",
         "text": "Arbeid vi har laget, med mål, løsning og teknologi.",
         "keywords": "prosjekt prosjekter referanse referanser arbeid portefølje case eksempler"},
        {"url": "/priser", "title": "Priser",
         "text": "Pakkene Start, Vekst og Premium, og svar på vanlige spørsmål.",
         "keywords": "pris priser pakke pakker kostnad koster start vekst premium tilbud spørsmål faq"},
        {"url": "/prosess", "title": "Prosess",
         "text": "Seks steg fra idé til ferdig løsning.",
         "keywords": "prosess metode strategi design utvikling testing lansering videreutvikling steg hvordan"},
        {"url": "/om-oss", "title": "Om oss",
         "text": "Hvem som står bak Nordexa Digital, og hvorfor du bør velge oss.",
         "keywords": "om oss hvem byrå digitalbyrå nordexa nima maleki"},
        {"url": "/kontakt", "title": "Kontakt",
         "text": "Få en gratis vurdering, send en melding, ring eller skriv en e-post.",
         "keywords": "kontakt melding e-post epost telefon ring adresse oslo vurdering skjema møte"},
        {"url": "/nettsideanalyse", "title": "Gratis nettsideanalyse",
         "text": "Få en enkel rapport om hastighet, mobil, SEO, tilgjengelighet og sikkerhet.",
         "keywords": "analyse nettsideanalyse audit rapport sjekk test hastighet seo sikkerhet gratis"},
        {"url": "/blogg", "title": "Blogg", "text": "Artikler om nettsider, hastighet og synlighet.",
         "keywords": "blogg innsikt artikkel artikler"},
        {"url": "/personvern", "title": "Personvern og informasjonskapsler",
         "text": "Hvilke opplysninger vi lagrer, og hvilke rettigheter du har.",
         "keywords": "personvern informasjonskapsler cookies gdpr opplysninger data"},
        {"url": "/vilkar", "title": "Vilkår", "text": "Vilkår for bruk av nettsiden.",
         "keywords": "vilkår betingelser bruk"},
    ]
    for p in innhold.PROSJEKTER:
        index.append({"url": "/prosjekter/" + p["slug"], "title": "Prosjekt: " + p["tittel"],
                      "text": p["kort"], "keywords": " ".join(p["fag"] + p["teknologi"]).lower()})
    for i in innhold.INNLEGG:
        index.append({"url": "/blogg/" + i["slug"], "title": i["tittel"],
                      "text": i["ingress"], "keywords": "blogg artikkel"})
    return index


SEARCH_INDEX = build_search_index()


def search_pages(query):
    words = [w for w in re.split(r"[^\wæøåÆØÅ-]+", query.lower()) if len(w) > 1]
    results = []
    for page in SEARCH_INDEX:
        title = page["title"].lower()
        keywords = page["keywords"].split()
        body = page["text"].lower()
        score = 0
        for word in words:
            if word in title:
                score += 3
            if any(k.startswith(word) or word.startswith(k) for k in keywords):
                score += 2
            if word in body:
                score += 1
        if score:
            results.append((score, page))
    results.sort(key=lambda item: -item[0])
    return [page for _, page in results]


@app.route("/sok")
def sok():
    query = (request.args.get("q") or "").strip()[:80]
    results = search_pages(query) if query else []
    return render_template("sok.html", query=query, results=results)


# =======================
# KONTAKT
# =======================

PAKKENAVN = tuple(p["navn"] for p in innhold.PAKKER)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def send_mail(subject, body, reply_to=None):
    if not MAIL_ENABLED:
        return
    try:
        mail.send(Message(subject=subject, recipients=[SITE["email"]],
                          reply_to=reply_to, body=body))
    except Exception:  # innholdet er uansett lagret i admin
        app.logger.exception("Kunne ikke sende e-postvarsel")


def les_motetid(raw):
    """Gjør «2026-10-14T13:30» om til «onsdag 14.10.2026 kl. 13:30». Tom streng hvis ikke oppgitt."""
    if not raw:
        return "", None
    try:
        when = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
    except ValueError:
        return "", "Velg dato og klokkeslett fra kalenderen."
    now = datetime.now(OSLO).replace(tzinfo=None) if OSLO else datetime.now()
    if when < now:
        return "", "Velg et tidspunkt frem i tid."
    if when > now + timedelta(days=90):
        return "", "Velg et tidspunkt innen de neste tre månedene."
    days = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    return "%s %s" % (days[when.weekday()], when.strftime("%d.%m.%Y kl. %H:%M")), None


@app.route("/kontakt", methods=["GET", "POST"])
@limiter.limit("5 per minute; 30 per day", methods=["POST"])
def kontakt():
    form = {"name": "", "email": "", "topic": "", "meeting": "", "message": ""}
    errors = {}

    if request.method == "POST":
        form = {k: (request.form.get(k) or "").strip() for k in form}

        # Skjult felt som mennesker ikke ser. Roboter fyller det ut.
        if request.form.get("website"):
            flash("Meldingen er sendt. Vi svarer innen 1–2 arbeidsdager.", "ok")
            return redirect(url_for("kontakt") + "#skjema")

        if not 2 <= len(form["name"]) <= 120:
            errors["name"] = "Skriv inn navnet ditt."
        if len(form["email"]) > 120 or not EMAIL_RE.match(form["email"]):
            errors["email"] = "Skriv inn en gyldig e-postadresse, for eksempel navn@firma.no."
        if form["topic"] not in innhold.EMNER:
            form["topic"] = ""
        meeting, meeting_error = les_motetid(form["meeting"])
        if meeting_error:
            errors["meeting"] = meeting_error
        if len(form["message"]) < 10:
            errors["message"] = "Skriv litt mer om hva du trenger hjelp med."
        elif len(form["message"]) > 5000:
            errors["message"] = "Meldingen er for lang. Kort den ned til under 5000 tegn."

        if not errors:
            db.session.add(Contact(name=form["name"], email=form["email"], message=form["message"],
                                   topic=form["topic"] or None, meeting=meeting or None))
            db.session.commit()
            send_mail("Ny melding fra nettsiden",
                      "Navn: %s\nE-post: %s\nGjelder: %s\nØnsket møtetid: %s\n\nMelding:\n%s\n" % (
                          form["name"], form["email"], form["topic"] or "ikke oppgitt",
                          meeting or "ikke oppgitt", form["message"]),
                      reply_to=form["email"])
            flash("Meldingen er sendt. Vi svarer innen 1–2 arbeidsdager.", "ok")
            return redirect(url_for("kontakt") + "#skjema")

    else:
        if request.args.get("pakke") in PAKKENAVN:
            form["message"] = "Hei! Jeg er interessert i pakken %s.\n\n" % request.args["pakke"]
        if request.args.get("emne") in innhold.EMNER:
            form["topic"] = request.args["emne"]

    status = 422 if errors else 200
    return render_template("kontakt.html", form=form, errors=errors, emner=innhold.EMNER), status


# =======================
# GRATIS NETTSIDEANALYSE
# =======================

@app.route("/nettsideanalyse", methods=["GET", "POST"])
@limiter.limit("3 per minute; 15 per day", methods=["POST"])
def nettsideanalyse():
    form = {"url": "", "email": ""}
    errors = {}

    if request.method == "POST":
        form = {k: (request.form.get(k) or "").strip() for k in form}
        if request.form.get("website"):  # robotfelle
            return redirect(url_for("nettsideanalyse"))
        if len(form["email"]) > 120 or not EMAIL_RE.match(form["email"]):
            errors["email"] = "Skriv inn en gyldig e-postadresse, for eksempel navn@firma.no."
        report = None
        if not errors:
            try:
                report = analyse.analyser(form["url"])
            except analyse.AnalyseFeil as exc:
                errors["url"] = str(exc)
            except Exception:
                app.logger.exception("Analysen feilet")
                errors["url"] = "Analysen stoppet på noe uventet. Prøv igjen, eller kontakt oss."
        if report:
            audit = Audit(token=secrets.token_urlsafe(16), url=report["url"][:300],
                          email=form["email"], report=json.dumps(report, ensure_ascii=False))
            db.session.add(audit)
            db.session.commit()
            send_mail("Ny nettsideanalyse: %s" % report["url"],
                      "E-post: %s\nNettside: %s\nSnitt: %d/100\n" % (
                          form["email"], report["url"], report["snitt"]),
                      reply_to=form["email"])
            return redirect(url_for("analyserapport", token=audit.token))

    status = 422 if errors else 200
    return render_template("analyse.html", form=form, errors=errors), status


@app.route("/nettsideanalyse/<token>")
def analyserapport(token):
    audit = Audit.query.filter_by(token=token).first_or_404()
    return render_template("analyserapport.html", audit=audit, r=json.loads(audit.report),
                           kategorier=analyse.KATEGORIER)


# =======================
# STATISTIKK UTEN SPORING
# =======================

TRACKED = {"home", "tjenester", "prosjekter", "prosjekt", "priser", "prosess", "om_oss",
           "blogg", "blogginnlegg", "kontakt", "nettsideanalyse", "personvern", "vilkar"}
BOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|monitor|curl|wget|python|headless", re.I)
EVENT_RE = re.compile(r"^[a-z0-9_]{2,40}$")


def log_page_view(response):
    if (request.method != "GET" or response.status_code != 200
            or request.endpoint not in TRACKED or current_user.is_authenticated
            or request.headers.get("DNT") == "1" or request.headers.get("Sec-GPC") == "1"
            or BOT_RE.search(request.headers.get("User-Agent", "") or "bot")):
        return
    referrer = urlsplit(request.referrer or "").hostname or ""
    if referrer == (request.host or "").split(":")[0]:
        referrer = ""
    try:
        db.session.add(PageView(path=request.path[:120], referrer=referrer[:120] or None))
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route("/hendelse", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per minute")
def hendelse():
    name = (request.get_data(as_text=True) or "")[:40]
    if (EVENT_RE.match(name) and not current_user.is_authenticated
            and request.headers.get("DNT") != "1" and request.headers.get("Sec-GPC") != "1"):
        db.session.add(Event(name=name))
        db.session.commit()
    return "", 204


def statistikk(days=30):
    since = utcnow() - timedelta(days=days)

    def top(column, model, limit=8):
        rows = (db.session.query(column, func.count(model.id))
                .filter(model.created_at >= since, column.isnot(None))
                .group_by(column).order_by(func.count(model.id).desc()).limit(limit).all())
        biggest = max([count for _, count in rows] or [1])
        return [{"navn": name, "antall": count, "prosent": int(round(100.0 * count / biggest))}
                for name, count in rows]

    return {
        "dager": days,
        "visninger": PageView.query.filter(PageView.created_at >= since).count(),
        "henvendelser": Contact.query.filter(Contact.created_at >= since).count(),
        "analyser": Audit.query.filter(Audit.created_at >= since).count(),
        "sider": top(PageView.path, PageView),
        "kilder": top(PageView.referrer, PageView),
        "klikk": top(Event.name, Event),
        "emner": top(Contact.topic, Contact),
    }


# =======================
# ADMIN
# =======================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("admin"))

        flash("Feil brukernavn eller passord.", "feil")

    return render_template("login.html")


@app.route("/admin")
@login_required
def admin():
    contacts = Contact.query.order_by(Contact.id.desc()).all()
    audits = Audit.query.order_by(Audit.id.desc()).limit(50).all()
    for audit in audits:
        audit.snitt = json.loads(audit.report).get("snitt")
    return render_template("admin.html", contacts=contacts, audits=audits, stat=statistikk())


@app.route("/admin/slett/<int:contact_id>", methods=["POST"])
@login_required
def slett_melding(contact_id):
    contact = db.session.get(Contact, contact_id)
    if contact is None:
        abort(404)
    db.session.delete(contact)
    db.session.commit()
    flash("Meldingen fra %s er slettet." % contact.name, "ok")
    return redirect(url_for("admin"))


@app.route("/admin/slett-analyse/<int:audit_id>", methods=["POST"])
@login_required
def slett_analyse(audit_id):
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)
    db.session.delete(audit)
    db.session.commit()
    flash("Analysen av %s er slettet." % audit.url, "ok")
    return redirect(url_for("admin") + "#analyser")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Du er logget ut.", "ok")
    return redirect(url_for("login"))


# =======================
# FOR SØKEMOTORER
# =======================

@app.route("/robots.txt")
def robots():
    body = ("User-agent: *\nDisallow: /admin\nDisallow: /login\nDisallow: /sok\n"
            "Disallow: /nettsideanalyse/\n\nSitemap: %s/sitemap.xml\n" % site_root())
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    paths = ["/", "/tjenester", "/prosjekter", "/priser", "/prosess", "/om-oss", "/blogg",
             "/kontakt", "/nettsideanalyse", "/personvern", "/vilkar"]
    paths += ["/prosjekter/" + p["slug"] for p in innhold.PROSJEKTER]
    paths += ["/blogg/" + i["slug"] for i in innhold.INNLEGG]
    urls = "".join("<url><loc>%s%s</loc></url>" % (site_root(), p) for p in paths)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % urls)
    return Response(xml, mimetype="application/xml")


# =======================
# FEILSIDER
# =======================

def error_page(code, title, message):
    return render_template("feil.html", code=code, title=title, message=message), code


@app.errorhandler(404)
def not_found(_):
    return error_page(404, "Vi finner ikke siden",
                      "Adressen kan være skrevet feil, eller siden er flyttet.")


@app.errorhandler(405)
def wrong_method(_):
    return error_page(405, "Den siden kan ikke åpnes slik",
                      "Gå tilbake og bruk knappen på siden i stedet for å skrive adressen direkte.")


@app.errorhandler(429)
def too_many(_):
    return error_page(429, "Det gikk litt fort",
                      "Du har sendt mange forespørsler på kort tid. Vent et minutt og prøv igjen.")


@app.errorhandler(CSRFError)
def csrf_error(_):
    return error_page(400, "Skjemaet har utløpt",
                      "Siden har stått åpen lenge. Gå tilbake, last siden på nytt og send skjemaet igjen.")


@app.errorhandler(500)
def server_error(_):
    return error_page(500, "Noe gikk galt hos oss",
                      "Prøv igjen om litt, eller send oss en e-post hvis feilen fortsetter.")


# =======================
# SIKKERHETSHODER
# =======================

CSP = ("default-src 'self'; "
       "script-src 'self'; "
       "style-src 'self' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; "
       "img-src 'self' data:; "
       "form-action 'self'; base-uri 'self'; frame-ancestors 'none'")


@app.after_request
def finish_response(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not app.debug:  # feilsøkingssiden til Flask trenger innebygde skript
        response.headers["Content-Security-Policy"] = CSP
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    log_page_view(response)
    return response


with app.app_context():
    init_db()


def change_admin_password():
    """Kjør:  .venv/bin/python app.py nytt-passord"""
    import getpass
    first = getpass.getpass("Nytt admin-passord (minst 10 tegn): ")
    if len(first) < 10:
        raise SystemExit("Passordet må ha minst 10 tegn. Ingenting er endret.")
    if first != getpass.getpass("Skriv det en gang til: "):
        raise SystemExit("Passordene var ikke like. Ingenting er endret.")
    with app.app_context():
        user = User.query.filter_by(username="admin").first()
        user.password = generate_password_hash(first, method="pbkdf2:sha256")
        db.session.commit()
    print("Passordet for admin er endret.")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["nytt-passord"]:
        change_admin_password()
        raise SystemExit

    # Lokalt: feilsøking på. Sett FLASK_DEBUG=0 for å slå det av.
    # På en ekte server: bruk gunicorn (se Procfile), ikke denne.
    app.run(debug=env("FLASK_DEBUG", "1") == "1", port=int(env("PORT", "5001")))

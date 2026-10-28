"""Gratis nettsideanalyse.

Henter forsiden til en offentlig nettside og gjør en enkel, automatisk sjekk
av det som kan leses ut av HTML-en og svaret fra serveren. Dette er ikke en
full revisjon – bare det som kan måles ærlig uten å åpne siden i en nettleser.

Sikkerhet: adressen kommer fra en besøkende, så vi slipper bare gjennom vanlige
http/https-adresser som peker på offentlige IP-adresser, og vi kobler oss til
nøyaktig den adressen vi har kontrollert.
"""

import gzip
import http.client
import ipaddress
import re
import socket
import ssl
import time
import zlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

TIMEOUT = 8            # sekunder per forespørsel
MAX_BYTES = 1500000    # leser aldri mer enn dette
MAX_REDIRECTS = 4
USER_AGENT = "NordexaNettsideanalyse/1.0"

KATEGORIER = ["Hastighet", "Mobil", "SEO", "Tilgjengelighet", "Sikkerhet"]


class AnalyseFeil(Exception):
    """Feil som kan vises direkte til den som ba om analysen."""


# ---------------------------------------------------------------- HENTING

def normaliser_url(raw):
    raw = (raw or "").strip()
    if not raw:
        raise AnalyseFeil("Skriv inn adressen til nettsiden, for eksempel www.firma.no.")
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https") or not parts.hostname or "." not in parts.hostname:
        raise AnalyseFeil("Adressen ser ikke riktig ut. Skriv den slik: www.firma.no.")
    if parts.username or parts.password:
        raise AnalyseFeil("Adressen kan ikke inneholde brukernavn eller passord.")
    if parts.port not in (None, 80, 443):
        raise AnalyseFeil("Vi kan bare analysere nettsider på vanlige nettadresser.")
    if len(raw) > 300:
        raise AnalyseFeil("Adressen er for lang.")
    return raw


def offentlig_ip(host):
    """Slår opp verten og returnerer en IP-adresse, men bare hvis alle svarene er offentlige."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise AnalyseFeil("Vi finner ikke nettsiden. Sjekk at adressen er skrevet riktig.")
    addresses = [info[4][0] for info in infos]
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global or ip.is_multicast:
            raise AnalyseFeil("Vi kan bare analysere offentlige nettsider.")
    ipv4 = [a for a in addresses if ":" not in a]
    return (ipv4 or addresses)[0]


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class _TryggHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.create_connection((offentlig_ip(self.host), self.port), self.timeout)


class _TryggHTTPS(http.client.HTTPSConnection):
    def connect(self):
        sock = socket.create_connection((offentlig_ip(self.host), self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _hent_en(url):
    parts = urlsplit(url)
    path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
    if parts.scheme == "https":
        conn = _TryggHTTPS(parts.hostname, 443, timeout=TIMEOUT, context=_ssl_context())
    else:
        conn = _TryggHTTP(parts.hostname, 80, timeout=TIMEOUT)
    try:
        conn.request("GET", path, headers={
            "Host": parts.netloc, "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
            "Accept-Encoding": "gzip, deflate", "Accept-Language": "nb,en;q=0.7",
            "Connection": "close",
        })
        response = conn.getresponse()
        headers = {k.lower(): v for k, v in response.getheaders()}
        raw = response.read(MAX_BYTES + 1)
        return response.status, headers, raw
    finally:
        conn.close()


def hent(url):
    """Følger videresendinger selv, slik at hver adresse blir kontrollert."""
    start = time.monotonic()
    for _ in range(MAX_REDIRECTS + 1):
        try:
            status, headers, raw = _hent_en(url)
        except AnalyseFeil:
            raise
        except ssl.SSLError:
            raise AnalyseFeil("Sikkerhetssertifikatet til nettsiden kunne ikke bekreftes, "
                              "så vi fikk ikke hentet den.")
        except (socket.timeout, TimeoutError):
            raise AnalyseFeil("Nettsiden svarte ikke innen %d sekunder." % TIMEOUT)
        except (OSError, http.client.HTTPException):
            raise AnalyseFeil("Vi fikk ikke kontakt med nettsiden. Prøv igjen om litt.")

        if status in (301, 302, 303, 307, 308) and headers.get("location"):
            url = normaliser_url(urljoin(url, headers["location"]))
            continue
        if status >= 400:
            raise AnalyseFeil("Nettsiden svarte med feilkode %d, så vi fikk ikke analysert den." % status)

        encoding = headers.get("content-encoding", "").lower()
        komprimert = encoding in ("gzip", "deflate", "br")
        overfort = len(raw)
        try:
            if encoding == "gzip":
                raw = gzip.decompress(raw)
            elif encoding == "deflate":
                raw = zlib.decompress(raw)
        except (OSError, zlib.error, EOFError):
            pass
        if "html" not in headers.get("content-type", "text/html").lower():
            raise AnalyseFeil("Adressen peker ikke på en nettside.")

        charset = re.search(r"charset=([\w-]+)", headers.get("content-type", ""), re.I)
        try:
            html = raw[:MAX_BYTES].decode(charset.group(1) if charset else "utf-8", "replace")
        except LookupError:
            html = raw[:MAX_BYTES].decode("utf-8", "replace")
        return {
            "url": url, "headers": headers, "html": html,
            "sekunder": time.monotonic() - start,
            "overfort": overfort, "komprimert": komprimert,
        }
    raise AnalyseFeil("Nettsiden sender oss videre for mange ganger.")


# ---------------------------------------------------------------- LESING AV HTML

class _Side(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = ""
        self.meta = {}
        self.canonical = False
        self.h = []
        self.bilder = 0
        self.bilder_uten_alt = 0
        self.bilder_lazy = 0
        self.responsive_bilder = 0
        self.blokkerende_skript = 0
        self.stilark = 0
        self.jsonld = False
        self.felt = []
        self.labels = set()
        self.lenker = 0
        self.tomme_lenker = 0
        self.usikre_ressurser = 0
        self._in_title = False
        self._in_head = False
        self._lenke = None
        self._i_label = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang") or None
        elif tag == "head":
            self._in_head = True
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if "canonical" in rel:
                self.canonical = True
            if "stylesheet" in rel:
                self.stilark += 1
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.h.append(int(tag[1]))
        elif tag == "img":
            self.bilder += 1
            if "alt" not in a:
                self.bilder_uten_alt += 1
            if a.get("loading", "").lower() == "lazy":
                self.bilder_lazy += 1
            if a.get("srcset"):
                self.responsive_bilder += 1
        elif tag in ("picture", "source") and a.get("srcset"):
            self.responsive_bilder += 1
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self.jsonld = True
            elif a.get("src") and self._in_head and "async" not in a and "defer" not in a \
                    and a.get("type", "").lower() != "module":
                self.blokkerende_skript += 1
        elif tag in ("input", "select", "textarea"):
            if a.get("type", "").lower() not in ("hidden", "submit", "button", "image", "reset"):
                if self._i_label:  # felt som står inne i en <label> har ledetekst
                    a["aria-label"] = "i label"
                self.felt.append(a)
        elif tag == "label":
            self._i_label += 1
            if a.get("for"):
                self.labels.add(a["for"])
        elif tag == "a" and a.get("href"):
            self.lenker += 1
            self._lenke = {"tekst": "", "navn": bool(a.get("aria-label") or a.get("title"))}

        for key in ("src", "href"):
            if tag in ("img", "script", "iframe", "link", "source") and a.get(key, "").startswith("http://"):
                if not (tag == "link" and "stylesheet" not in a.get("rel", "")):
                    self.usikre_ressurser += 1

        if self._lenke is not None and tag in ("img", "svg") and (a.get("alt") or a.get("aria-label") or tag == "svg"):
            self._lenke["navn"] = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self._in_head = False
        elif tag == "label":
            self._i_label = max(0, self._i_label - 1)
        elif tag == "a" and self._lenke is not None:
            if not self._lenke["tekst"].strip() and not self._lenke["navn"]:
                self.tomme_lenker += 1
            self._lenke = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._lenke is not None:
            self._lenke["tekst"] += data


# ---------------------------------------------------------------- VURDERING

def analyser(raw_url):
    """Returnerer en rapport som kan lagres som JSON og vises til brukeren."""
    svar = hent(normaliser_url(raw_url))
    side = _Side()
    try:
        side.feed(svar["html"])
    except Exception:
        pass
    headers = svar["headers"]
    https = svar["url"].startswith("https://")
    sjekker = []

    def sjekk(kategori, ok, vekt, bra, forbedring):
        sjekker.append({"kategori": kategori, "ok": bool(ok), "vekt": vekt,
                        "tekst": bra if ok else forbedring})

    # --- Hastighet
    sek = svar["sekunder"]
    sjekk("Hastighet", sek < 1.0, 3,
          "Forsiden svarte på %.1f sekunder." % sek,
          "Forsiden brukte %.1f sekunder på å svare. Under ett sekund er et godt mål." % sek)
    sjekk("Hastighet", svar["komprimert"], 2,
          "Innholdet sendes komprimert.",
          "Slå på komprimering (gzip eller Brotli) på serveren, så lastes siden raskere.")
    kb = len(svar["html"].encode("utf-8")) / 1024.0
    sjekk("Hastighet", kb < 200, 2,
          "HTML-en er på %d kB, som er lett nok." % kb,
          "HTML-en er på %d kB. Rydd bort kode og innhold som ikke brukes." % kb)
    sjekk("Hastighet", side.blokkerende_skript <= 1, 2,
          "Ingen skript holder igjen visningen av siden.",
          "%d skript i toppen av siden må lastes før noe vises. Legg til «defer» på dem."
          % side.blokkerende_skript)
    if side.bilder > 4:
        sjekk("Hastighet", side.bilder_lazy >= side.bilder / 3.0, 2,
              "Bilder lenger ned lastes først når de trengs.",
              "Ingen eller få av de %d bildene bruker loading=\"lazy\". Da lastes alle med en gang."
              % side.bilder)
    sjekk("Hastighet", "cache-control" in headers or "expires" in headers, 1,
          "Serveren forteller nettleseren hvor lenge siden kan mellomlagres.",
          "Sett Cache-Control på serveren, så slipper faste besøkende å laste alt på nytt.")

    # --- Mobil
    viewport = side.meta.get("viewport", "").lower()
    sjekk("Mobil", "width=device-width" in viewport, 5,
          "Siden er satt opp til å tilpasse seg skjermbredden.",
          "Siden mangler <meta name=\"viewport\">. Da vises den som en forminsket PC-side på mobil.")
    sjekk("Mobil", "user-scalable=no" not in viewport and "maximum-scale=1" not in viewport, 2,
          "Besøkende kan zoome inn på mobil.",
          "Zoom er slått av på mobil. Det gjør siden vanskelig å lese for mange.")
    if side.bilder > 2:
        sjekk("Mobil", side.responsive_bilder > 0, 2,
              "Siden leverer bilder i flere størrelser.",
              "Bildene leveres i én størrelse. Med srcset får mobiler mindre og raskere bilder.")
    sjekk("Mobil", bool(side.meta.get("theme-color")), 1,
          "Siden har en egen farge på nettleserlinjen på mobil.",
          "Legg til <meta name=\"theme-color\">, så får nettleserlinjen på mobil merkevarens farge.")

    # --- SEO
    tittel = " ".join(side.title.split())
    sjekk("SEO", 10 <= len(tittel) <= 65, 4,
          "Tittelen har god lengde: «%s»." % tittel[:65],
          ("Siden mangler <title>." if not tittel else
           "Tittelen er på %d tegn. Mellom 10 og 65 tegn vises best i søk." % len(tittel)))
    beskrivelse = side.meta.get("description", "").strip()
    sjekk("SEO", 50 <= len(beskrivelse) <= 170, 3,
          "Siden har en metabeskrivelse med god lengde.",
          ("Siden mangler metabeskrivelse, teksten som vises under tittelen i Google."
           if not beskrivelse else
           "Metabeskrivelsen er på %d tegn. Mellom 50 og 170 tegn er best." % len(beskrivelse)))
    antall_h1 = side.h.count(1)
    sjekk("SEO", antall_h1 == 1, 3,
          "Siden har én hovedoverskrift.",
          ("Siden mangler hovedoverskrift (h1)." if antall_h1 == 0 else
           "Siden har %d hovedoverskrifter (h1). Det bør være én." % antall_h1))
    sjekk("SEO", side.canonical, 1,
          "Siden oppgir sin egen adresse (canonical).",
          "Legg til en canonical-lenke, så vet Google hvilken adresse som er den riktige.")
    sjekk("SEO", "og:title" in side.meta and "og:image" in side.meta, 2,
          "Siden har tittel og bilde for deling i sosiale medier.",
          "Siden mangler Open Graph-tittel eller -bilde. Da blir delinger på Facebook og LinkedIn bare en naken lenke.")
    sjekk("SEO", "noindex" not in side.meta.get("robots", "").lower(), 4,
          "Siden kan vises i søkemotorer.",
          "Siden ber søkemotorer om å ikke vise den (noindex).")
    sjekk("SEO", side.jsonld, 1,
          "Siden har strukturerte data som hjelper Google å forstå innholdet.",
          "Legg til strukturerte data (JSON-LD), så kan Google vise mer om bedriften i søket.")

    # --- Tilgjengelighet
    sjekk("Tilgjengelighet", bool(side.lang), 3,
          "Siden oppgir hvilket språk den er skrevet på.",
          "Sett lang på <html>, for eksempel lang=\"nb\". Skjermlesere trenger det for å lese riktig.")
    if side.bilder:
        sjekk("Tilgjengelighet", side.bilder_uten_alt == 0, 4,
              "Alle bilder har alt-tekst.",
              "%d av %d bilder mangler alt-tekst. Blinde og svaksynte får da ikke vite hva bildet viser."
              % (side.bilder_uten_alt, side.bilder))
    if side.felt:
        uten = [f for f in side.felt
                if not (f.get("id") in side.labels or f.get("aria-label") or f.get("aria-labelledby") or f.get("title"))]
        sjekk("Tilgjengelighet", not uten, 3,
              "Skjemafeltene har ledetekster.",
              "%d skjemafelt mangler ledetekst (label). Plassholdertekst alene er ikke nok." % len(uten))
    if side.lenker:
        sjekk("Tilgjengelighet", side.tomme_lenker == 0, 2,
              "Alle lenker har tekst som sier hvor de fører.",
              "%d lenker har verken tekst eller beskrivelse." % side.tomme_lenker)
    hopp = any(b - a > 1 for a, b in zip(side.h, side.h[1:]))
    sjekk("Tilgjengelighet", bool(side.h) and side.h[0] == 1 and not hopp, 2,
          "Overskriftene kommer i riktig rekkefølge.",
          "Overskriftene hopper over nivåer eller starter ikke med h1. Det gjør siden vanskeligere å navigere.")

    # --- Sikkerhet
    sjekk("Sikkerhet", https, 5,
          "Siden bruker HTTPS.",
          "Siden bruker ikke HTTPS. Nettlesere merker den som «ikke sikker».")
    sjekk("Sikkerhet", "strict-transport-security" in headers, 2,
          "Nettlesere får beskjed om alltid å bruke HTTPS (HSTS).",
          "Slå på HSTS, så kan ingen lure besøkende over på en usikret versjon av siden.")
    sjekk("Sikkerhet", headers.get("x-content-type-options", "").lower() == "nosniff", 1,
          "X-Content-Type-Options er satt.",
          "Sett X-Content-Type-Options: nosniff på serveren.")
    csp = headers.get("content-security-policy", "")
    sjekk("Sikkerhet", bool(csp), 2,
          "Siden har en Content-Security-Policy.",
          "Legg til en Content-Security-Policy. Den begrenser skaden hvis noen får lurt inn skadelig kode.")
    sjekk("Sikkerhet", "x-frame-options" in headers or "frame-ancestors" in csp, 1,
          "Siden kan ikke bygges inn i andres sider.",
          "Sett X-Frame-Options, så kan ikke andre nettsteder vise siden din i en ramme.")
    if https:
        sjekk("Sikkerhet", side.usikre_ressurser == 0, 2,
              "Alt innhold lastes over HTTPS.",
              "%d filer lastes over usikret HTTP. Nettlesere blokkerer ofte slike." % side.usikre_ressurser)

    poeng = {}
    for kategori in KATEGORIER:
        egne = [s for s in sjekker if s["kategori"] == kategori]
        total = sum(s["vekt"] for s in egne)
        poeng[kategori] = int(round(100.0 * sum(s["vekt"] for s in egne if s["ok"]) / total)) if total else 0

    mangler = sorted((s for s in sjekker if not s["ok"]), key=lambda s: -s["vekt"])
    return {
        "url": svar["url"],
        "poeng": poeng,
        "snitt": int(round(sum(poeng.values()) / float(len(poeng)))),
        "forbedringer": [{"kategori": s["kategori"], "tekst": s["tekst"]} for s in mangler[:3]],
        "sjekker": [{"kategori": s["kategori"], "ok": s["ok"], "tekst": s["tekst"]} for s in sjekker],
    }

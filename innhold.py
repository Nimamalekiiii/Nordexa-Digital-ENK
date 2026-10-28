"""Alt innhold som gjentas på nettsiden ligger her.

Endre tekst, priser, prosjekter og spørsmål i denne filen, så oppdateres
alle sidene som bruker dem. Lagre filen, og last siden på nytt.
"""

# ---------------------------------------------------------------- TJENESTER

TJENESTER = [
    {
        "id": "nettsider", "ikon": "nettside", "tittel": "Nettsider",
        "kort": "Skreddersydde nettsider som representerer merkevaren din og gjør besøkende til kunder.",
        "punkter": [
            "Design laget for din bedrift, ikke en ferdig mal",
            "Fungerer like godt på mobil, nettbrett og PC",
            "Tydelig vei fra første besøk til henvendelse",
        ],
    },
    {
        "id": "webapplikasjoner", "ikon": "app", "tittel": "Webapplikasjoner",
        "kort": "Digitale løsninger bygget rundt virksomhetens behov.",
        "punkter": [
            "Innlogging, skjemaer og egne adminsider",
            "Databaser og integrasjoner mot andre systemer",
            "Bygget slik at løsningen kan utvides senere",
        ],
    },
    {
        "id": "nettbutikk", "ikon": "butikk", "tittel": "Nettbutikk",
        "kort": "Skreddersydde e-handelsløsninger med betalingsintegrasjon.",
        "punkter": [
            "Produktsider bygget for å selge",
            "Betaling integrert i kassen",
            "Enkel administrasjon av produkter og ordre",
        ],
    },
    {
        "id": "design", "ikon": "design", "tittel": "UX/UI-design",
        "kort": "Brukervennlige og moderne digitale opplevelser.",
        "punkter": [
            "Struktur og brukerflyt før farger og former",
            "Visuelt uttrykk som passer merkevaren din",
            "Skisser du kan se og kommentere før noe bygges",
        ],
    },
    {
        "id": "optimalisering", "ikon": "fart", "tittel": "Optimalisering",
        "kort": "Vi forbedrer hastighet, SEO og konvertering.",
        "punkter": [
            "Raskere lasting på mobil og PC",
            "Teknisk SEO og strukturert innhold",
            "Tydeligere knapper og skjemaer som gir flere henvendelser",
        ],
    },
    {
        "id": "vedlikehold", "ikon": "verktoy", "tittel": "Vedlikehold",
        "kort": "Vi holder løsningen din sikker, oppdatert og optimalisert.",
        "punkter": [
            "Oppdateringer og sikkerhetskopier",
            "Endringer i tekst, bilder og sider",
            "Hjelp når noe slutter å virke",
        ],
    },
]

# Brukes i «Hva gjelder det?» i kontaktskjemaet og i statistikken i admin
EMNER = [t["tittel"] for t in TJENESTER] + ["Annet"]

# ---------------------------------------------------------------- TEKNOLOGI
# Det vi faktisk bygger med. Vises under toppen på forsiden.

TEKNOLOGI = ["Python", "Flask", "JavaScript", "HTML", "CSS", "SQL", "Git"]

# ---------------------------------------------------------------- PROSJEKTER
# Bare ekte arbeid. «type» sier ærlig hva slags prosjekt det er.
# Når du får kundeprosjekter: legg dem øverst, sett type til «Kundeprosjekt»
# og fyll inn «resultat» med tall du kan dokumentere.

PROSJEKTER = [
    {
        "slug": "oud-royale",
        "tittel": "Oud Royale",
        "type": "Eget konseptprosjekt",
        "fag": ["Webdesign", "Frontend"],
        "bilde": "img/prosjekter/oud-royale.webp",
        "bilde_alt": "Skjermbilde av Oud Royale: en parfymeflaske vist i en lys, luksuriøs nettbutikk",
        "kort": "Nettbutikk-konsept for eksklusive parfymer, med fokus på et rolig og luksuriøst uttrykk.",
        "mal": "Vise hvordan en liten merkevare kan få et eksklusivt uttrykk på nett "
               "uten at siden blir tung eller vanskelig å bruke.",
        "losning": "En forside som leder rett til kolleksjonen, produktkort med store bilder, "
                   "en lysbildevisning av parfymene og en meny som følger med når du ruller. "
                   "Innholdet tones inn etter hvert som du blar nedover.",
        "teknologi": ["HTML", "CSS", "JavaScript"],
        "resultat": [],
    },
    {
        "slug": "finansdashbord",
        "tittel": "Finansdashbord",
        "type": "Eget prosjekt",
        "fag": ["Webapplikasjon", "Backend", "Frontend"],
        "bilde": "img/prosjekter/finansdashbord.webp",
        "bilde_alt": "Skjermbilde av finansdashbordet med inntekt, utgifter og balanse øverst og en liste over posteringer",
        "kort": "Webapplikasjon som gir full oversikt over inntekter og utgifter.",
        "mal": "Lage et verktøy der man raskt kan føre inn inntekter og utgifter "
               "og se med en gang hvordan økonomien ligger an.",
        "losning": "Posteringer lagres i en database og vises i en liste du kan søke i og filtrere på måned. "
                   "Summer for inntekt, utgifter og balanse oppdateres fortløpende, og tre diagrammer "
                   "viser fordelingen per kategori og utviklingen over tid. Løsningen har lys og mørk modus.",
        "teknologi": ["Python", "Flask", "SQLite", "JavaScript", "Chart.js"],
        "resultat": [],
    },
    {
        "slug": "portefolje",
        "tittel": "Personlig portefølje",
        "type": "Eget prosjekt",
        "fag": ["Webdesign", "Frontend"],
        "bilde": "img/prosjekter/portefolje.webp",
        "bilde_alt": "Skjermbilde av porteføljen: mørk forside med navn, lenker og et animert nettverk i bakgrunnen",
        "kort": "Porteføljeside med animert bakgrunn og egne sider for bakgrunn, ferdigheter og erfaring.",
        "mal": "Presentere utdanning, ferdigheter og erfaring på en måte som skiller seg ut "
               "fra en vanlig CV.",
        "losning": "Fire sider knyttet sammen av en sidemeny som glir inn, en mørk stil med et "
                   "animert nettverk tegnet i bakgrunnen, og tydelige lenker til LinkedIn og GitHub.",
        "teknologi": ["HTML", "CSS", "JavaScript"],
        "resultat": [],
    },
]

# ---------------------------------------------------------------- KUNDEOMTALER
# Tom til du har ekte omtaler. Seksjonen vises ikke før listen har innhold.
# Eksempel:
# {"sitat": "…", "navn": "Kari Nordmann", "rolle": "Daglig leder", "firma": "Firma AS"},

OMTALER = []

# ---------------------------------------------------------------- HVORFOR OSS

HVORFOR = [
    {"tittel": "Skreddersydd",
     "tekst": "Ingen ferdige maler som gjør at bedriften din ser ut som alle andre."},
    {"tittel": "Konverteringsfokusert",
     "tekst": "Designet rundt hva du faktisk ønsker at brukeren skal gjøre."},
    {"tittel": "Lynrask",
     "tekst": "Optimalisert for mobil, desktop og Core Web Vitals."},
    {"tittel": "Bygget for vekst",
     "tekst": "Løsningen kan utvikles videre når virksomheten vokser."},
]

# ---------------------------------------------------------------- PROSESS

PROSESS = [
    {"tittel": "Strategi", "tekst": "Vi lærer virksomheten og målgruppen din å kjenne."},
    {"tittel": "Design", "tekst": "Vi utvikler struktur, UX og visuelt uttrykk."},
    {"tittel": "Utvikling", "tekst": "Designet blir bygget med moderne teknologi."},
    {"tittel": "Testing", "tekst": "Vi tester på forskjellige skjermer, nettlesere og enheter."},
    {"tittel": "Lansering", "tekst": "Vi publiserer løsningen og sørger for at alt fungerer."},
    {"tittel": "Videreutvikling", "tekst": "Vi hjelper deg videre etter lanseringen."},
]

# ---------------------------------------------------------------- PAKKER

PAKKER = [
    {
        "navn": "Start", "for": "For mindre bedrifter", "pris": "9 900 kr", "fra": True,
        "punkter": ["1–3 sider", "Responsivt design", "Grunnleggende SEO", "Kontaktskjema", "Rask levering"],
        "knapp": "Velg Start", "anbefalt": False,
    },
    {
        "navn": "Vekst", "for": "For bedrifter som vil vokse", "pris": "19 900 kr", "fra": True,
        "punkter": ["5–8 sider", "Skreddersydd design", "Konverteringsoptimalisering", "Avansert SEO", "Analyse og strategi"],
        "knapp": "Velg Vekst", "anbefalt": True,
    },
    {
        "navn": "Premium", "for": "For større behov", "pris": "Etter avtale", "fra": False,
        "punkter": ["Skreddersydd løsning", "Webapplikasjoner", "Systemintegrasjon", "Full strategi", "Langsiktig samarbeid"],
        "knapp": "Be om tilbud", "anbefalt": False,
    },
]

# ---------------------------------------------------------------- SPØRSMÅL OG SVAR
# Svarene bør stemme med hvordan du faktisk jobber. Rett på dem ved behov.

FAQ = [
    {"sporsmal": "Hvor mye koster en nettside?",
     "svar": "Start-pakken koster fra 9 900 kr og Vekst-pakken fra 19 900 kr. Større løsninger "
             "priser vi etter omfang. Du får alltid en fast pris i et skriftlig tilbud før vi begynner."},
    {"sporsmal": "Hvor lang tid tar det?",
     "svar": "Det avhenger av størrelsen på prosjektet og hvor raskt vi får tekst og bilder fra deg. "
             "Tilbudet inneholder en konkret leveringsdato, så du vet hva du kan regne med."},
    {"sporsmal": "Kan dere hjelpe med domene og hosting?",
     "svar": "Ja. Vi hjelper deg med å velge og sette opp domene, hosting og e-post, "
             "og sørger for at alt er koblet riktig sammen ved lansering."},
    {"sporsmal": "Kan dere lage nettbutikk?",
     "svar": "Ja. Vi bygger nettbutikker med produktsider, handlekurv og betaling."},
    {"sporsmal": "Kan dere vedlikeholde nettsiden?",
     "svar": "Ja. Vi kan ta oss av oppdateringer, sikkerhetskopier og endringer i innholdet, "
             "slik at du kan konsentrere deg om bedriften."},
    {"sporsmal": "Hva skjer etter lansering?",
     "svar": "Vi sjekker at alt fungerer som det skal, og retter feil som dukker opp. "
             "Vil du ha løpende hjelp videre, avtaler vi vedlikehold. Det er ingen bindingstid."},
]

# ---------------------------------------------------------------- BLOGG
# Hvert innlegg har en egen fil i templates/blogg/<slug>.html

INNLEGG = [
    {"slug": "hva-koster-en-nettside", "tittel": "Hva koster en nettside?",
     "dato": "2026-10-10", "lesetid": 3,
     "ingress": "Prisen avhenger av tre ting: hvor mye som skal bygges, hvor mye som skal "
                "skreddersys, og hva som skal skje etter lansering."},
    {"slug": "tregere-nettside", "tittel": "Fem ting som gjør nettsiden din treg",
     "dato": "2026-10-10", "lesetid": 3,
     "ingress": "De fleste trege nettsider er trege av de samme grunnene. Her er de vanligste, "
                "og hva du kan gjøre med dem."},
    {"slug": "digital-vekst-2026", "tittel": "Digital vekst i 2026",
     "dato": "2026-02-23", "lesetid": 4,
     "ingress": "Hvordan moderne nettsider skaper konkurransefortrinn: førsteinntrykk, "
                "brukeropplevelse, hastighet, SEO og kontinuerlig optimalisering."},
]

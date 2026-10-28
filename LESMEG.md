# Nordexa Digital – nettsiden

## Starte lokalt

```bash
cd ~/Desktop/Github_all_koding_Nima/Nordexa-Digital-ENK
.venv/bin/python app.py
```

Åpne http://127.0.0.1:5001. Stopp med `Ctrl + C`.

## Hvor endrer jeg hva?

| Jeg vil endre …                                   | Fil                              |
|---------------------------------------------------|----------------------------------|
| Tjenester, priser, prosjekter, spørsmål og svar   | `innhold.py`                     |
| Teksten på én side                                | `templates/<siden>.html`         |
| Et blogginnlegg                                   | `templates/blogg/<innlegg>.html` |
| Meny og bunntekst                                 | `templates/base.html`            |
| Farger, skrift og utseende                        | `static/css/style.css`           |
| Animasjoner                                       | `static/js/script.js`            |
| Org.nr., e-post, lenker til sosiale medier        | `.env` (kopier `.env.example`)   |
| Bildet på Om oss                                  | bytt ut `static/img/nima.webp`   |

### Nytt prosjekt

1. Legg et skjermbilde i `static/img/prosjekter/` (helst WebP, 1200 × 750).
2. Kopier en av blokkene i `PROSJEKTER` i `innhold.py` og fyll inn.
3. For kundeprosjekter: sett `type` til `Kundeprosjekt`, og fyll inn `resultat` med tall du kan dokumentere.

### Nytt blogginnlegg

1. Legg til en linje øverst i `INNLEGG` i `innhold.py`.
2. Lag `templates/blogg/<slug>.html` med samme navn som `slug`. Kopier et av de andre som mal.

### Kundeomtaler

Legg dem i `OMTALER` i `innhold.py`. Seksjonen vises automatisk på forsiden og prosjektsiden når listen ikke er tom.

## Admin

Gå til http://127.0.0.1:5001/login. Der ser du henvendelser, bestilte nettsideanalyser og statistikk.

Bytt passord:

```bash
.venv/bin/python app.py nytt-passord
```

## E-postvarsler

1. Slå på totrinnsbekreftelse på Google-kontoen.
2. Lag et app-passord: https://myaccount.google.com/apppasswords
3. Kopier `.env.example` til `.env` og lim passordet inn etter `MAIL_PASSWORD=`.
4. Start siden på nytt.

## Legge siden ut på nett

Siden er klargjort for Railway, Render og lignende (`Procfile` og `requirements.txt` er med).

1. Legg prosjektet på GitHub. `.gitignore` sørger for at `.env`, databasen og `.venv` ikke blir med.
2. Lag et nytt prosjekt hos leverandøren og koble det til GitHub-repoet.
3. Legg inn disse variablene hos leverandøren:
   - `SECRET_KEY` – en lang, tilfeldig tekst
   - `ADMIN_PASSWORD` – passordet du vil ha til admin
   - `SITE_URL` – adressen siden får, f.eks. `https://nordexadigital.no`
   - `COOKIE_SECURE=1`, `BEHIND_PROXY=1`, `FLASK_DEBUG=0`
   - `MAIL_PASSWORD`, `ORG_NR` og de andre fra `.env.example`
4. **Database:** SQLite-filen forsvinner hver gang siden legges ut på nytt hos de fleste leverandører.
   Legg til en PostgreSQL-database hos leverandøren, lim adressen inn som `DATABASE_URL`,
   og fjern `#` foran `psycopg2-binary` i `requirements.txt`.
5. Koble til domenet ditt i innstillingene hos leverandøren.

## Domene og e-post

- Kjøp domenet (f.eks. hos Domeneshop) og pek det til leverandøren der siden ligger.
- Sett opp e-post på domenet (f.eks. `post@nordexadigital.no`), og bytt `CONTACT_EMAIL` og `MAIL_USERNAME` i `.env`.
- Hvis du bytter bort fra Gmail, må du også endre `MAIL_SERVER` og `MAIL_PORT`.

## Sikkerhetskopi

Den opprinnelige nettsiden ligger i `_backup_original/`.

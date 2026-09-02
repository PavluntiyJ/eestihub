# Tallinn rent snapshot sources

## 2026-05-27 snapshot

- Source: [Hinnapäring — Üürikorteri hind Tallinnas linnaositi 2026](https://www.hinnaparing.ee/blogi/uurikorteri-hind-tallinnas-linnaositi-2026)
- Published/captured date: 2026-05-27
- Retrieved: 2026-09-02
- Coverage: public aggregate monthly rent ranges for one-, two- and
  three-room apartments in all eight Tallinn districts. The publisher
  attributes the table to Ruumiamet rental transaction statistics and an
  analysis of active KV.ee and City24 offers from January through May 2026.
- Transformation: each CSV rent is the integer midpoint of the published
  range, rounded to the nearest euro. This produces one representative
  value for the existing API fields without presenting a range endpoint as
  a measured arithmetic mean. District-level utility costs were not
  published, so `avg_utilities` is intentionally empty and the rents API
  retains the legacy utility estimate for that field.
- License/terms note: no explicit open-data license or content reuse terms
  were published on the source page when retrieved. The CSV manually
  transcribes and attributes 24 factual aggregate range midpoints from one
  public market report; no listing pages, login-only data or automated
  scraping were used. Re-check permission before redistributing a
  materially larger extract or automating future collection.

from decimal import Decimal


# e-Residency application: EUR 150. The digital ID is valid for five years,
# and renewal or replacement carries the same fee. Source: official e-Residency
# Knowledge Base, "Costs & fees". Retrieved 2026-09-02.
# https://learn.e-resident.gov.ee/hc/en-gb/articles/360000625118-Costs-fees
E_RESIDENCY_APPLICATION_FEE = Decimal("150.00")

# Electronic OÜ establishment: EUR 265. Sources: official e-Residency Knowledge
# Base and the Estonian e-Business Register. Retrieved 2026-09-02.
# https://learn.e-resident.gov.ee/hc/en-gb/articles/360000624838-5-steps-to-register-a-company-online
# https://ariregister.rik.ee/eng/application/start
# A notary is the alternative when the founders cannot use the online route.
# The Chamber of Notaries lists a EUR 200 registration state fee plus variable
# notary fees; this calculator intentionally models the standard e-resident
# self-service route instead. Retrieved 2026-09-02.
# https://www.notar.ee/et/teabekeskus/ariuhing
ONLINE_OU_REGISTRATION_FEE = Decimal("265.00")

# Licensed contact person/legal address services: EUR 200-400 per year. The
# calculator uses the midpoint, EUR 300, for a neutral first-year estimate.
# Source: official e-Residency Knowledge Base, "Costs & fees". Retrieved
# 2026-09-02.
# https://learn.e-resident.gov.ee/hc/en-gb/articles/360000625118-Costs-fees
CONTACT_PERSON_ANNUAL_FEE_MIN = Decimal("200.00")
CONTACT_PERSON_ANNUAL_FEE_MAX = Decimal("400.00")
CONTACT_PERSON_ANNUAL_FEE_DEFAULT = (
    CONTACT_PERSON_ANNUAL_FEE_MIN + CONTACT_PERSON_ANNUAL_FEE_MAX
) / Decimal("2")

# Basic monthly accounting commonly starts at EUR 50. Current packages in the
# official e-Residency Marketplace cluster around EUR 50-100 for a small active
# company (for example EUR 50 micro, EUR 95 general, EUR 99 full-service). The
# calculator exposes the input and defaults to the EUR 75 range midpoint.
# Retrieved 2026-09-02.
# https://learn.e-resident.gov.ee/hc/en-gb/articles/360000625118-Costs-fees
# https://marketplace.e-resident.gov.ee/en/packages/?services=33
MONTHLY_ACCOUNTING_FEE_MIN = Decimal("50.00")
MONTHLY_ACCOUNTING_FEE_MAX = Decimal("100.00")
MONTHLY_ACCOUNTING_FEE_DEFAULT = (
    MONTHLY_ACCOUNTING_FEE_MIN + MONTHLY_ACCOUNTING_FEE_MAX
) / Decimal("2")

MONEY_QUANT = Decimal("0.01")
WHOLE_EURO_QUANT = Decimal("1")

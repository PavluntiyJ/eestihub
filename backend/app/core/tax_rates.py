from decimal import Decimal


# Source: EMTA Tax rates 2026, verified 2026-07-09:
# https://www.emta.ee/en/business-client/taxes-and-payment/income-and-social-taxes/tax-rates
INCOME_TAX_RATE = Decimal("0.22")

# Source: EMTA Tax rates 2026, verified 2026-07-09:
# https://www.emta.ee/en/business-client/taxes-and-payment/income-and-social-taxes/tax-rates
BASIC_EXEMPTION_MONTHLY = Decimal("700")

# Source: EMTA Tax rates 2026, verified 2026-07-09:
# https://www.emta.ee/en/business-client/taxes-and-payment/income-and-social-taxes/tax-rates
SOCIAL_TAX_RATE = Decimal("0.33")

# Source: EMTA Tax rates 2026, verified 2026-07-09:
# https://www.emta.ee/en/business-client/taxes-and-payment/income-and-social-taxes/tax-rates
UNEMPLOYMENT_INSURANCE_EMPLOYEE_RATE = Decimal("0.016")

# Source: EMTA Tax rates 2026, verified 2026-07-09:
# https://www.emta.ee/en/business-client/taxes-and-payment/income-and-social-taxes/tax-rates
UNEMPLOYMENT_INSURANCE_EMPLOYER_RATE = Decimal("0.008")

# Source: EMTA Tax rates 2026 and funded pension page, verified 2026-07-09:
# https://www.emta.ee/en/business-client/taxes-and-payment/income-and-social-taxes/tax-rates
# https://www.emta.ee/en/business-client/taxes-and-payment/income-and-social-taxes/contributions-mandatory-funded-pension
PENSION_PILLAR_RATES = frozenset(
    {Decimal("0.00"), Decimal("0.02"), Decimal("0.04"), Decimal("0.06")}
)

# Source: EMTA Entrepreneur account page, verified 2026-07-09:
# https://www.emta.ee/en/private-client/taxes-and-payment/taxable-income/entrepreneur-account
ENTREPRENEUR_ACCOUNT_TAX_RATE = Decimal("0.20")

# Source: EMTA 2026 tax changes and social tax page, verified 2026-09-02:
# https://www.emta.ee/uudised/maksumuudatused-2026
# https://www.emta.ee/ariklient/maksud-ja-tasumine/tulumaks-ja-sotsiaalmaks/sotsiaalmaks
SOCIAL_TAX_MONTHLY_RATE = Decimal("886")
FIE_SOCIAL_TAX_MINIMUM_MONTHLY = SOCIAL_TAX_MONTHLY_RATE * SOCIAL_TAX_RATE

# Source: EMTA FIE social tax page, verified 2026-09-02:
# https://www.emta.ee/ariklient/registreerimine-ettevotlus/ettevotjale/fuusilisest-isikust-ettevotjale-fie/sotsiaalmaks
FIE_SOCIAL_TAX_ANNUAL_MAXIMUM = Decimal("36867.60")
FIE_SOCIAL_TAX_MONTHLY_MAXIMUM = FIE_SOCIAL_TAX_ANNUAL_MAXIMUM / Decimal("12")

# Source: EMTA Entrepreneur account page, verified 2026-09-02:
# https://www.emta.ee/eraklient/maksud-ja-tasumine/maksustatavad-tulud/ettevotluskonto
ENTREPRENEUR_ACCOUNT_ANNUAL_LIMIT = Decimal("40000")
ENTREPRENEUR_ACCOUNT_MONTHLY_LIMIT = ENTREPRENEUR_ACCOUNT_ANNUAL_LIMIT / Decimal("12")

# Source: EMTA VAT registration page, verified 2026-09-02:
# https://www.emta.ee/ariklient/maksud-ja-tasumine/kaibemaks/kaibemaksukohustuslasena-registreerimine/maksukohustuslasena-registreerimise-kohustus
VAT_REGISTRATION_ANNUAL_THRESHOLD = Decimal("40000")
VAT_REGISTRATION_MONTHLY_THRESHOLD = (
    VAT_REGISTRATION_ANNUAL_THRESHOLD / Decimal("12")
)

MONEY_QUANT = Decimal("0.01")
EFFECTIVE_TAX_RATE_QUANT = Decimal("0.001")

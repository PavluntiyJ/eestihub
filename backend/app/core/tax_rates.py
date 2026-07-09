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

MONEY_QUANT = Decimal("0.01")
EFFECTIVE_TAX_RATE_QUANT = Decimal("0.001")

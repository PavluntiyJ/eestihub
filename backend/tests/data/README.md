# Tax golden-file derivations

All amounts use the 2026 constants in `app/core/tax_rates.py`, unrounded
`Decimal` arithmetic, `ROUND_HALF_UP` to cents for money, and three decimal
places for effective tax rates.

- Gross basis: each regime starts from the CSV income. Payer-cost basis:
  employment gross is `cost / 1.338`, board-member gross is `cost / 1.33`,
  and FIE and entrepreneur-account gross equal cost.
- Employment: subtract 1.6% employee unemployment insurance and the selected
  pension rate, then charge 22% income tax above the €700 exemption. Payer cost
  is gross multiplied by `1 + 33% + 0.8%`.
- Board member: subtract the selected pension rate, then charge 22% income tax
  above the €700 exemption. Payer cost is gross multiplied by `1 + 33%`.
- FIE: clamp 33% social tax between €292.38 monthly and the €36,867.60 annual
  cap divided by 12, then charge 22% income tax above the €700 exemption.
- Entrepreneur account: charge `20% + pension_pillar_rate` on all receipts.

The scenarios cover both comparison bases at €3,000 / 2%, the FIE floor and
income below the exemption at €500 / 0%, income above the exemption at €1,000
/ 4%, and annual turnover above €40,000 at €5,000 / 6%. Together they exercise
every supported pension rate. The €200 / 0% FIE row records the legally correct
negative result: `€200 - €292.38 minimum social tax = -€92.38`, with an
effective tax rate of `1 - (-92.38 / 200) = 1.4619`, rounded to `1.462`.

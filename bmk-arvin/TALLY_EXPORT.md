# TallyPrime Edit Log — separate shop exports

Start with exports. Automatic synchronization is not configured. Do not mix data from the two legal companies.

For each company:

1. Select only the intended company in TallyPrime Edit Log.
2. Open Stock Summary, select the required as-of date and expand it to individual stock items. Include closing quantities and units.
3. Export the current report to Excel using Export > Current (or Ctrl+E where available). Save with the company name and as-of date.
4. Export the stock item master data separately if the report lacks item codes, units, groups or standard selling prices. XML is also useful for master data. If you use a price list, export the applicable price list separately.
5. Provide the exports for BMK and Sarbanan separately. Include the currency and whether the selling price includes tax. The stock valuation rate is not necessarily the customer selling price; confirm the intended selling-price source.

The current website stock importer accepts only SKU,Quantity snapshots for products already present. Do not upload an arbitrary full Tally report directly to it. Full catalogue mapping, fractional units, negative balances and price interpretation need validation against the supplied exports first. Before updating live stock, reconcile quantities and pending web orders so a snapshot does not accidentally restore reserved stock.

Official references:
- https://help.tallysolutions.com/export-data-in-tally/
- https://help.tallysolutions.com/sample-xml/
- https://help.tallysolutions.com/pre-requisites-for-integrations/

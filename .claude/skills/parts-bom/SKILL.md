---
name: parts-bom
description: Build a bill of materials (BOM) with prices for a VequIR product or assembly (vequir-unit, vequir-power, vequir-standard) from the "Vemef Parts" Google Sheet, and find parts and prices on South African supplier websites (Micro Robotics, Communica, Netram, Mantech, Pishop and others) to fill the sheet in. Use whenever the user asks what a product costs, for a BOM or parts list with prices, to price or re-price parts, to find a part at a supplier, to compare suppliers, or to add parts or prices to Vemef Parts.
---

# Parts, prices and BOMs

The parts and their prices live in one Google Sheet, **Vemef Parts**. A BOM
comes from a product's CAD files (what it is made of and how many) joined to
that sheet (who sells each part and for how much). When the sheet has no
price for a part, find one on the supplier sites and add it.

Two helpers in `scripts/` do the mechanical work (Python 3, standard library
only, run with `python3 -I`):

- `bom.py <dir>`: the draft BOM of a product or assembly.
- `supplier.py sites | search <site> <query> | product <url>`: supplier lookups.

## The sheet

- **Vemef Parts**: spreadsheet ID `1uFm6ji_R4uwDDygHD0bthpPcO0hoiKnp8TqrGdmTvrw`,
  tab `Sheet1`, through the Google Sheets connector. If its tools are not
  loaded, search for them ("google sheets values"). If the connector is not
  on in this session, ask the user to turn it on; do not work from a copy.
- Before writing to it, load the `google-workspace` skill (it covers how the
  Sheets tools parse what they write).
- Columns, row 1 frozen:

| Col | Header | Holds |
| --- | --- | --- |
| A | Part | the part as a buyer would name it, with the value for valued parts ("Resistor 0.25 W 1k") and the pack size when sold in packs ("M1.2 x 6 countersunk screws (pack of 10)") |
| B | Supplier | the shop's name as `supplier.py sites` gives it (Micro Robotics, Communica, ...) |
| C | Unit Price (ZAR ex VAT) | rand per piece, **excluding VAT**, as a number |
| D | Price Status | `confirmed` or `unconfirmed` (a dropdown: nothing else is accepted) |
| E | URL | the product page |
| F | Supplier SKU | the shop's part number or reference |
| G | Stock | what the page says: `in stock`, `out of stock`, a count, or empty |
| H | Date Checked | when C was read, `YYYY-MM-DD` |
| I | Library Item | the CAD library item: `electronics/diode_1n5822`; for a valued part, `item:value` as the schematic writes the value (`electronics/resistor_025w:1k`, `electronics/capacitor_mlcc:100n`) |

- One row per part **per supplier**: the same part at two shops is two rows
  with the same Library Item. Some rows have no supplier yet; fill them in
  rather than adding a second row.
- Read it with `get_values` on `Sheet1!A1:I`. Match rows to BOM lines by
  column I, never by the name in column A. A row with I empty is matched by
  name only with the user's say-so, and then I is filled in.

### Price rules

- **ex VAT, per piece.** SA VAT is 15 %: a price that includes VAT is divided
  by 1.15 and rounded to cents. If the page shows both, take its ex-VAT
  figure. A pack price is divided by the pack size. With quantity breaks
  (Mantech) take the 1-off price.
- **`confirmed`** only when the price was read just now from the product page
  itself or the shop's product API (`supplier.py search` with method woo or
  shopify, or `supplier.py product`), or the user gave it.
- **`unconfirmed`** when it came from a web-search result (its snippet), or
  the page could not be fetched. Write the URL anyway so the user can check it.
- Never replace a `confirmed` price with an `unconfirmed` one. A newer
  confirmed price replaces an older one in the same row; say old → new in the
  reply.

## Build a BOM

1. **Draft it.** From the root of the repository that holds the product
   (`vequir-unit` for products, `vequir-power` for packs and holders), with
   the others cloned beside it:

   ```bash
   python3 -I .claude/skills/parts-bom/scripts/bom.py products/LS1
   ```

   It prints JSON: `lines` (bought-in parts), `made` (parts VequIR prints or
   cuts itself: enclosures, holders' bodies, brackets) and `unresolved`.
   - Lines from `schematic.json` have exact counts, one line per value, with
     their references (R4, R5).
   - Lines from the assembly scripts with `"count": null` were added in a
     loop: open each `where` line and count the loop's list (the
     `base.pico_holes` it loops over is defined in that part's `part.py`).
     Count them, don't guess; say which loop each count came from.
   - `unresolved` entries whose shape is picked at run time (the wiring
     board's components) are already in the schematic lines when the product
     has a schematic; otherwise read the code.
   - A line marked "an assembly" (the 18650 holder) is not bought: its
     contents (cell, clips) are lines of their own, and its body is in `made`.
   - Wires, solder, glue, heat-shrink and the perfboard's raw stock are not
     modelled. List the perfboard under `made` as the script does; mention
     the rest as not counted.

2. **Price it.** Read the sheet and, per line, pick the row with the same
   Library Item (and value): the cheapest `confirmed` row in stock, else the
   cheapest `confirmed`, else the cheapest `unconfirmed`. A line with no row
   or no price is **missing**.

3. **Report it** as a table, most expensive line first or in schematic
   order, whichever the user asked for:

   | Refs | Part | Qty | Supplier | Unit (ZAR ex VAT) | Line total | Status |
   | --- | --- | --- | --- | --- | --- | --- |

   Then the total ex VAT and incl VAT (× 1.15), how much of it is
   unconfirmed, the missing lines, and the `made` parts (no price: they are
   printed or cut in-house). Offer to look up the missing and unconfirmed
   parts.

4. **Only if the user asks**, write the BOM to its own tab (`BOM LS1`) with
   Qty, Unit and `=Qty*Unit` line totals and a `SUM` total, the unit prices
   as `XLOOKUP`/`INDEX MATCH` formulas against `Sheet1` rather than typed
   copies, so the BOM follows the sheet.

## Find a part and add it to the sheet

1. **Know what to look for.** Read the library item's `description.md`: the
   exact part (TP4056, not TP4057; USB-C, not micro-USB; the module's size
   and pinout), and what the CAD model assumes. A different variant is a
   different part: don't record it under this Library Item without saying so.

2. **Search.** `python3 -I .claude/skills/parts-bom/scripts/supplier.py sites` lists each shop and its
   method:

   | Method | Shops | How |
   | --- | --- | --- |
   | woo, shopify | Make, Stelltron, Communica, Electromann | `search <site> <query>` returns names, links, prices and stock from the shop's API |
   | html | Netram, Rabtron, Hobbytronics, RoboFactory | `search` returns names and links; then `product <url>` |
   | websearch | Micro Robotics, Mantech, Pishop, Progenix, ElectroMechanica, Evetech | web search with `allowed_domains` set to the shop; then `product <url>` |
   | blocked | DIYElectronics, DigiKey | web search only: prices `unconfirmed` |
   | gone | Botshop | no longer sells parts: skip |

   Search the shops the user names; otherwise start with the ones already in
   the sheet for similar parts (Micro Robotics, Pishop), then a few others.
   Search by the part's core name (`tp4056`, `1n5822`, `ws2812 8`). Keep it
   to what the task needs: a dozen requests, not every shop for every part.
   Space requests to one shop a second or more apart; Electromann
   rate-limits quickly.

3. **Read the price.** `product <url>` returns `price` and `found_by`
   (`json-ld`, `meta`, `microdata`) when the page carries structured data,
   and `page_prices`: the rand amounts on the page with the words around
   them. Use `page_prices` to tell whether the structured price includes VAT
   (the `vat` note in `sites` says what is known per shop), and, when there
   is no structured price, to take the product's own price (not a cart total,
   a related product or a crossed-out old price). `blocked` means a bot
   check: fall back to the web-search snippet, `unconfirmed`. An `error`
   means the page has gone: search again.

4. **Write it.** One call per batch:
   - a new part or a new supplier for a part: `append_values` on
     `Sheet1!A:I`, a full row;
   - a known part and supplier (same column I and B): `update_values` on that
     row's C:H only.
   Write SKUs that look like numbers with a leading apostrophe (`'1195`) so
   they stay text, the date as `YYYY-MM-DD`, the price as a number. Read the
   rows back after writing and check them.

5. **Report** what was added or changed, with each price's status and URL,
   and anything not found.

## When a fetch fails

- `HTTP 403 ... no rule or network setting allows this host` from the proxy
  means the cloud environment does not allow that host (the bare and `www.`
  names of each shop are on the list in the user's environment). Tell the
  user which host; do not work around it.
- A shop's bot check that comes and goes (RoboFactory, Micro Robotics'
  search) is not a reason to retry in a loop: use web search and mark the
  price `unconfirmed`.
- When a shop changes its site and a method stops working, fix
  `scripts/supplier.py` in all three repositories (the skill is the same in
  each) and say so.

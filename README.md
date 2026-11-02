# vequir-standard

VequIR's standard parts, as a [neoBotics](https://github.com/anroleroux/neoBotics)
parts library: parts made to a standard or a maker's drawing, written as
CadQuery B-rep code from a plain-language description and built and checked
as exact solids (BREP, STEP, STL, shaded views).

Product page: **[anroleroux.co.za/vequir-standard](https://anroleroux.co.za/vequir-standard/)**

## The library

| Designation | Part |
| --- | --- |
| `batteries/cell_18650` | an 18650 lithium-ion cell, 18.4 × 65 mm, standing on its negative end |
| `terminals/keystone_1107_1` | a Keystone 1107-1 battery clip with a solder lug |
| `fasteners/m1_2x6_countersunk` | an M1.2 × 6 countersunk screw |

```
library/<category>/category.md            "# Title", then a blurb
library/<category>/<part>/description.md  the natural-language description
library/<category>/<part>/part.py         the CadQuery script (B-rep code)
```

Any neoBotics script places one with `load_library("<category>/<part>")` and
reads its variables (`cell.diameter`, `screw.length`), so whatever is sized
from it follows a change here. Other repositories reach this library by
naming it in their `libraries.txt` (`../vequir-standard/library`):
[vequir-power](https://github.com/anroleroux/vequir-power) does, for the
holder's cell and clips and the pack's screws, and
[vequir-unit](https://github.com/anroleroux/vequir-unit) does, for the PB6's
screws. This library uses no other, and must not: dependencies point down,
unit → power → standard.

A change here moves the parts built from it in those repositories: rebuild
them before pushing, and push them on the same branch name.

## Working on it

Clone neoBotics (the tool) beside this repository, install neobotics, and
run everything from this repository's root:

```bash
git clone https://github.com/anroleroux/neoBotics ../neoBotics
python -m venv .venv && source .venv/bin/activate
pip install -e "../neoBotics[dev]"

python -m pytest -q tests                     # checks of the real parts
neobotics build library/fasteners/m1_2x6_countersunk   # one part
neobotics site --out results --site site      # every part, then the pages
```

`results/` and `site/` are build output and git-ignored. In a Claude Code
session, the `neobotics-part` skill (`.claude/skills/neobotics-part/`) takes
a designation plus modelling instructions through the same steps.

## CI and the product page

`.github/workflows/cad.yml` runs on every push to `main` and `claude/**`. It
clones neoBotics beside the checkout (the branch of the same name when it
exists there, else the default branch), runs the tests, builds every part,
and deploys the site to GitHub Pages: **anroleroux.co.za/vequir-standard**,
the product page. A part that fails to build fails the job.
Settings → Pages → Source must be GitHub Actions.

Actions → **cad** → *Run workflow*, with `design` set to a part directory
holding a `description.md`, has Claude write its script; it needs the
`ANTHROPIC_API_KEY` repository secret.

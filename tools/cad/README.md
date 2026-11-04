# CAD tool

Natural language in, a 3D CAD model out. A description of a part goes to
Claude. Claude writes a [CadQuery](https://github.com/CadQuery/cadquery)
script: the B-rep code, Python that builds the part's exact boundary
representation. The script is run, checked and exported as BREP, STEP, STL and
shaded PNG views.

The CAD stage follows [topocombo](https://github.com/anroleroux/topocombo): a
part is a CadQuery script that assigns the part to `result` and names places on
it in `regions`. A script opens as-is in CQ-editor. The pipeline reads every
fact it needs from the built shape, never from parameters. The tool adds the
stage in front, which writes that script from a description.

## Pipeline

```
description.md ──► Claude ──► part.py ──► CadQuery (child process) ──► part.brep / .step / .stl
   (NL)                (B-rep code)           │                        part.png, part_rear_below.png
                          ▲                   │                        summary.json
                          └── build error ────┤
                          └── views + summary ┘  (review: APPROVED, or a revised script)
```

1. **NL → script.** The description goes to Claude (`claude-opus-5-5`, adaptive
   thinking, streamed) with a system prompt that fixes the script contract:
   - millimetres, z up, the part standing on z = 0;
   - every dimension as a named constant;
   - a docstring that lists each assumption the description left open;
   - `result` and `regions`;
   - only `cadquery` and `math` imported.
2. **Script → B-rep.** The script runs in a child process with a timeout,
   because it is model-written code. The child checks that `result` holds
   valid solids with volume and that every region selects faces, edges or
   vertices. It then exports the part. A failure goes back to Claude verbatim
   (the traceback with the script's line numbers, or the check that failed),
   and Claude sends a corrected script. By default four scripts are allowed in
   all.
3. **Review.** Claude gets two shaded views of the built part plus its measured
   bounding box, volume, face types and regions. It compares them with the
   description and answers `APPROVED` or sends a revised script, which goes
   back through step 2. One round by default (`--review 0` skips it).

The whole exchange is a single append-only conversation, and every script
Claude sends is kept under `attempts/`.

## Usage

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...        # or `ant auth login`

# NL -> B-rep code -> CAD
cad generate --description ../../vequir-unit/products/PB6/lid/description.md --out results/lid
cad generate "a 40 x 40 x 5 mm plate with four M3 holes on a 30 mm square" --out results/plate

# only the CAD stage, for a script written or edited by hand (no model, no key)
cad cad tests/fixtures/nema17_bracket/part.py --out results/nema17_bracket

# a shaded PNG of any BREP or STL (--view iso | rear_below)
cad view results/nema17_bracket/cad/part.stl
```

In a catalogue repository (see below), from its root:

```bash
# build one catalogue part by its designation
cad build PB6/lid
# or a reusable part or assembly in the parts library
cad build library/battery_holders/single_18650_holder

# build every part in the catalogue and the library, and render the site: an
# overview page, then one page per product, assembly and part with its 3D viewer
cad site --out results --site site
```

### Without an API key

The NL → script step does not have to be a `generate` run. A person (or
Claude in a coding session) can read a part's `description.md`, write its
`part.py` to the same contract, and commit both. CI builds every committed
`part.py` and publishes it, so no key is involved. This is how parts are added
for now. `generate` automates the same step once a key is
set.

### The catalogue repositories

The CAD tool lives in vequir-standard, under `tools/cad/`. The parts it
builds live in the VequIR catalogue repositories, each with its own CI and
its own product page (its catalogue site on GitHub Pages):

| Repository | Holds | Page |
| --- | --- | --- |
| [vequir-standard](https://github.com/anroleroux/vequir-standard) | `library/`: standard parts — `batteries/cell_18650`, `terminals/keystone_1107_1`, `fasteners/m1_2x6_countersunk` | [anroleroux.co.za/vequir-standard](https://anroleroux.co.za/vequir-standard/) |
| [vequir-power](https://github.com/anroleroux/vequir-power) | `library/battery_holders/`: the single 18650 holder and the six-cell pack, and their parts (holder body, end strip) | [anroleroux.co.za/vequir-power](https://anroleroux.co.za/vequir-power/) |
| [vequir-unit](https://github.com/anroleroux/vequir-unit) | `products/`: the PB6 powerbank | [anroleroux.co.za/vequir-unit](https://anroleroux.co.za/vequir-unit/) |

A catalogue repository holds a product breakdown, `products/`, a parts
library, `library/`, or both, plus a `site.md` (`# Title`, then the
overview's lede). Clone them side by side; the CAD tool comes with
vequir-standard:

```
vequir-standard/  vequir-power/  vequir-unit/
```

#### Products

Parts live in a product breakdown, `products/<PRODUCT>/<assembly>/.../<part>/`.
Assemblies nest to any depth, and the leaf assemblies hold the parts. Each
part has its `description.md` and `part.py`. `product.md` and `assembly.md`
name and describe the levels above. A product, and any assembly, may hold an
`assembly.py`: its contents placed together, checked for interference and
contact. A part's designation is its path (`PB6/chassis/base`);
`cad build <designation>` builds just that part, or an assembly's
assembled model (`PB6/chassis`). A script can read another part's variables
with `load_part("../base")`. See vequir-unit's README for the rules.

#### Parts libraries

`library/` holds parts and assemblies kept for reuse in any product, filed by
category: `library/<category>/<item>/`. A category is laid out like a product.
Any script places a library item with `load_library("<category>/<item>")`,
from any depth, and reads its variables as it would with `load_part`.

`load_library` searches several libraries, in order:

1. each directory in `CAD_LIBRARY` (an `os.pathsep`-separated list);
2. the `library/` directory nearest above the calling script;
3. each library the nearest `libraries.txt` above the script lists, one
   directory per line, relative to the file (`../vequir-standard/library`).

The first library holding the designation provides it. That is how one
repository uses another's library: vequir-power's `libraries.txt` names
vequir-standard's, so its holder takes its cell with
`load_library("batteries/cell_18650")`; vequir-unit's names both. Each
script resolves against its own repository, so a vequir-power part loaded
from vequir-unit still finds vequir-standard through vequir-power's file.

The site has a page for the library, and each item's page shows the call
that places it and every script that uses it, in any repository:

- each site publishes `uses.json` at its root: its scripts' uses of other
  repositories' library items, each resolved as `load_library` resolves it,
  with the page of the script that places it;
- a library repository lists the sites of the repositories that use it in
  `used-by.txt` beside `site.md`, one base URL per line
  (`https://anroleroux.co.za/vequir-unit/`). Its item pages fetch those
  sites' `uses.json` in the browser and add their uses to "Used in". So the
  list stays current when a user changes, without rebuilding the library.

In a Claude Code session, the `cad-part` skill
(`.claude/skills/cad-part/SKILL.md`, also in each catalogue
repository) takes a designation plus modelling instructions. It picks the
repository, writes or edits the description and the script, builds and
checks the part, updates the site, and commits.

`generate` options: `--max-attempts N` (scripts in all, repairs included),
`--review N` (review rounds), `--model`, `--effort low|medium|high|xhigh|max`
(default `high`).

### A run directory

```
results/jaw/
  description.md     the input, as given
  part.py            the script that built the part
  cad/               part.brep, part.step, part.stl, part.png, part_rear_below.png, summary.json
  attempts/NN.py     every script Claude sent, NN/ its build
  transcript.md      Claude's replies, in order
  manifest.json      model, attempts and their errors, review verdict, token usage, summary
```

### The part script

`tests/fixtures/nema17_bracket/` is a hand-written reference (kept with the
tests, outside the catalogue): a
NEMA 17 motor bracket with its description next to it. It follows the same contract a generated
script does:

```python
"""An L-bracket that holds a NEMA 17 stepper motor.

Assumptions where the description is silent:
- ...
"""
import cadquery as cq

width = 50.0  # along x, both plates
thickness = 3.0
...
result = vertical.union(base) ...      # the part: valid solid(s), z up, on z = 0
regions = {                            # named places for later stages
    "motor_face": result.faces("<Y"),
    "base_bottom": result.faces("<Z"),
}
```

`regions` is how a later stage refers to the part without knowing its
geometry. In topocombo, a study fixes and loads parts by region name; here the
same names can carry an assembly's mates or a study's loads.

## Modules

| Module | Role |
| --- | --- |
| `cad.nl2cad` | the prompt, the Claude client (`ClaudeCoder`), the generate → build → repair → review loop |
| `cad.part` | runs a part script in a child process, checks it, exports BREP / STEP / STL / PNG and `summary.json` |
| `cad.cadview` | headless shaded rendering (numpy z-buffer, no OpenGL), adapted from topocombo's `cadview` |
| `cad.pipeline` | lays out a run directory around the two stages |
| `cad.site` | the static page: an interactive three.js view of each part's STL, its description, measurements, script and downloads |
| `cad.catalog` | reads a catalogue's `products/` breakdown (assemblies to any depth) and its `library/`, builds every part, renders the site |
| `cad.cli` | `cad generate / cad / build / view / site` |

The model sits behind a small `Coder` interface (`(system, messages) ->
(text, content)`), so the tests drive the whole loop with scripted replies and
real CadQuery builds, with no network.

## CI and GitHub Pages

vequir-standard's `.github/workflows/cad.yml` runs these tests (from
`tools/cad/`) on every push to `main` and `claude/**`, before its own. The
tests use synthetic parts and the reference bracket, so they do not depend on
any catalogue.

Each catalogue repository has its own `.github/workflows/cad.yml`. On a push
it:

1. clones the repositories its `libraries.txt` names beside the checkout, on
   the same branch name when it exists there, else the default branch;
   vequir-standard, the bottom of the chain, carries the CAD tool;
2. installs the CAD tool (`tools/cad/` in vequir-standard, its own or the
   clone) and runs the repository's tests (checks
   of its real parts);
3. builds every part with `cad site` and renders the pages; a part that
   fails to build fails the job;
4. uploads the CAD files as the `parts` artifact, and deploys the site to
   GitHub Pages: that repository's product page.

The site:

- `index.html`, the overview: one card per product, then the library's
  categories (in a library-only repository, the categories with pictures);
- `products/<product>/index.html`, and one page per assembly below it: that
  level's contents as cards you can click into, then its assembled model with
  its fit; under the model's 3D view, each thing the assembly holds directly
  (a part, or a sub-assembly as one) can be hidden or made see-through, and a
  section slider cuts the model along x, y or z;
- one page per part: its designation, a 3D view you can orbit, cut with a
  section slider and make see-through, the
  description, measurements, and STEP / STL / BREP / script downloads.

Every 3D view draws coordinate crosshairs through the model's origin: x red,
y green, z blue, dashed on the negative side. The "axes" button in the
caption hides them.

Every page leads back up through a breadcrumb and a "Back to …" link. Links are
relative, so the site also works opened from a local folder. Pages
must be set to deploy from GitHub Actions (Settings → Pages → Source).

To generate a design with Claude in CI, add an `ANTHROPIC_API_KEY` secret to
the catalogue repository and start its **cad** workflow by hand with
`design` set to a part directory holding a `description.md`, such as
`products/PB6/lid`.

## Safety

Generated scripts are arbitrary Python. They run in a separate process with a
timeout, but not in a sandbox. Run `generate` somewhere you would run code
you have not read, such as a container or CI, and read `part.py` before you
reuse it elsewhere.

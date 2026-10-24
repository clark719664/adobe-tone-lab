# Adobe Shadows/Highlights measurement kit

This repository contains **126 real Adobe DNG Converter 18.7 previews** and a reproducible benchmark of the pinned PhotoCraft Shadows/Highlights operator. The references cover 18 synthetic inputs and seven settings per input, including two joint settings. They are original **8-bit sRGB JPEG preview** bytes with provenance and integrity checks.

The measured conditional postrender baseline has joint MAE **10.8562/255 on training families** and **9.6611/255 on research-visible validation families**. No improved operator passed the generalization gate. These measurements do not establish RAW-stage Camera Raw equivalence, photographic fidelity, or the separate 16-bit ProPhoto TIFF contract.

See [PREVIEW.md](PREVIEW.md) for the evidence, acquisition procedure, limitations and rejected experiments.

## Run from a fresh clone

Use Python 3.12, Rust stable and its native linker. On Windows, run native builds from a Visual Studio Developer Command Prompt or an equivalent configured build environment. From the repository root:

```sh
python -m pip install -r requirements-preview.txt
python -m unittest discover -s . -v
python preview_benchmark.py --oracle preview_reference --families preview_reference/families.json --build-dir .build/preview --out .build/reproduced-preview-baseline.json
python run_photocraft.py --build-dir .build/photocraft
```

The requirements pin NumPy 2.3.5 and Pillow 12.3.0. The test suite contains 37 Python tests. The separate PhotoCraft probe compiles the unchanged pinned Rust module and runs its eight upstream tests. The preview benchmark compiles that same actual operator with original numerical helpers and serial scheduling shims, then predicts edited previews from Adobe default JPEGs. It is a **conditional postrender prediction** benchmark.

The benchmark checks the exact 126 case identities, seven settings per input, family splits, requested XMP hashes, actual output settings, Adobe version and sRGB metadata, JPEG hashes and decoded-pixel hashes. Integrity checks prevent accidental mixing; they do not cryptographically prove Adobe authorship of an arbitrary supplied pack.

`preview_reference/` contains the real reference JPEGs and output XMP. `preview_acquisition/verification/` records setting counterfactuals and unchanged raw-payload checks. `preview_rejected_experiments/` preserves failed hypotheses and measurements. Validation families were reused during research; future model selection and final testing require new untouched families and a photographic corpus.

`.gitattributes` preserves byte-sensitive vendor files, source capture inputs and preview JPEG/XMP files across checkouts. Keep it intact. Adobe application binaries, installers and caches are not redistributed.

## Original public single-slider measurements

The frozen public Camera Raw 18.7 JSON contains 61 cases, including 27 scene cases and **zero joint cases in that original JSON**. This is separate from the new preview oracle. Its original no-op baseline, audit and scene scorer remain available:

```sh
python benchmark.py baseline --out .build/public-baseline.json
python benchmark.py audit
python benchmark.py score predictions.json --out .build/comparison.json
```

The scorer expects 384 finite nonnegative linear-ProPhoto block luminances for each required scene case, in the original 24×16 order. A passing single-slider score does not establish joint fidelity. The two saved Photoshop 25.4 grey probes reproduced by `run_photocraft.py` are narrow historical single-slider checks, separate from the 18.7 preview benchmark.

## Optional, unfinished 16-bit TIFF capture path

The original joint TIFF contract still lacks a complete legitimate paired batch. **Do not import preview JPEGs as TIFF references or substitute them into the old ProPhoto oracle.** The TIFF importer validates full 16-bit values, strips, byte order, dimensions, unsigned RGB, orientation, compression and ICC primaries/transfer curves. A successful import establishes file consistency, with `fidelity_status: not_measured`; it does not prove slider application or Adobe fidelity.

The optional manual capture requires an existing licensed Photoshop/Camera Raw installation and 21 TIFFs: seven settings on each of three supplied scenes. In Photoshop choose File → Scripts → Browse, select `acquisition/export_photoshop.jsx`, and choose a fresh empty output directory. The script requests ProPhoto RGB/16-bit exports. This Photoshop script was syntax-checked and has **not been executed in Adobe**. Independently verify that Camera Raw applied the requested settings and record its actual build.

```sh
python reference_import.py capture /path/to/exports --adobe-version "ACTUAL CAMERA RAW VERSION"
python reference_import.py import /path/to/exports --out .build/imported-joint-references.json
python benchmark.py joint-gate /path/to/exports
```

With the paired TIFF batch absent, `joint-gate` must return exit 2. The importer checks hashes and requested settings without modifying exports or the old oracle. The 16-bit joint candidate and fidelity gate remain unfinished. Synthetic importer test fixtures are explicitly labelled and never installed as Adobe expectations.

## Provenance and license

`sources.json` pins RAWmakase `6c60222a927ec54cea9bb11624615b3d2baa6aa9` and PhotoCraft `a02f2ee41059d3312e7ff24a5af5edcac7b6435a`. The 14 vendored files come from canonical Git blobs, with SHA-256 hashes and original notices. The copied generators produce input stimuli, never Adobe expected outputs. `public-oracle-search.json` records the bounded search for the original paired TIFF dependency.

The authored harness/acquisition code and documentation are MIT licensed in LICENSE. Vendored RAWmakase files remain MIT licensed; PhotoCraft files remain MIT-or-Apache-2.0. Complete notices are in `vendor/`; generated PhotoCraft wrappers retain those upstream terms.

GitHub Actions installs the pinned preview dependencies, runs all Python tests, reproduces the native preview baseline, runs the unchanged PhotoCraft tests and checks the absent-TIFF exit code. Successful CI verifies this toolkit and its recorded benchmark, not broad Adobe parity.

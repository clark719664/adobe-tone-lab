# Adobe Shadows/Highlights measurement kit

**Joint Adobe fidelity remains blocked by missing paired Adobe exports.** This repository supplies a tested importer, actual competitor baseline and ready capture inputs. It does not contain a replacement joint operator or claim that single-slider tests prove joint fidelity.

## Run from a fresh clone

Use Python 3.10 or newer. The benchmark, capture preparation, TIFF import and all 24 Python tests use only the standard library. NumPy is needed only if you run the optional copied procedural generators. Rust stable plus its native linker is needed only to rebuild the separate PhotoCraft probe.

From this repository's root:

```sh
python -m unittest discover -s . -v
python benchmark.py baseline --out public-baseline.json
python benchmark.py audit
# Expected exit 2: the public oracle contains zero joint cases.
python benchmark.py joint-gate references
# Expected exit 2 until all 21 real paired exports exist.
```

Optional actual competitor run:

```sh
python run_photocraft.py --build-dir .build
```

`.gitattributes` preserves exact vendor/input bytes across Windows and Unix checkouts. Do not remove it: source and input hashes are byte-sensitive. `prepare_acquisition.py` regenerates the capture pack with consistent LF sidecars; it never runs Adobe software.

## What is measured

- The frozen public Camera Raw 18.7 JSON has 61 cases, including 27 scene cases and **zero joint Shadows/Highlights cases**. The scorer requires 15 candidate scene arrays: three defaults and 12 edited cases. Both defaults and edits enter its anti-regression gate. Scenes 1/3 are designated train and scene 4 holdout; no parameters were fitted here.
- `public-baseline.json` measures the **no-op** operator: the actual frozen Adobe default remains unchanged for each edited case. Effect MAE spans 0.029778–0.266790 EV. Two of 12 edited cases are within historical upstream distance allowances; the overall gate fails. This is a real no-op measurement, not a new operator or a fresh RAWmakase engine render.
- `run_photocraft.py` compiles the actual unchanged pinned Rust `local_tone.rs` with its original numerical helpers. Only row/map scheduling is serial. All eight upstream tests passed. Two saved Photoshop 25.4 grey probes measured 165.2136 versus 165.3 and 90.35554 versus 89.6, errors 0.0864 and 0.7555 levels out of 255. This narrow single-slider check is not a complete app run, Adobe 18.7 comparison, joint test or photographic holdout.
- `reference_import.py` decodes full 16-bit values without an 8-bit image conversion. It validates TIFF strips, byte order, dimensions, orientation, unsigned RGB, compression, ICC primaries and transfer curves. ICC transfer checks evaluate **all 65,536 possible input codes**, require monotonic finite values, and allow at most 0.003 linear error from gamma 1.8. Tests include a hidden LUT spike and narrow parametric branch that sparse validation missed.

## Acquire the missing real references

An existing licensed Photoshop/Camera Raw installation is the remaining external dependency. No Adobe software, account, trial, login or export was installed or invoked here. The included exporter was syntax-checked, **not executed in Adobe**.

The current experiment requires **one batch producing 21 TIFFs**: seven settings on each of three scenes. This includes fresh defaults and single-slider controls as well as two joint settings. The TIFFs must come from the same Camera Raw build and these exact inputs. Existing full-resolution public measurements cannot substitute for any member of this new reduced-resolution batch.

1. Keep `acquisition/` together. In your existing Photoshop installation choose **File → Scripts → Browse**, then select `acquisition/export_photoshop.jsx`. Choose a fresh empty output folder. The script copies each DNG and its exact XMP to a separate capture folder, requests ProPhoto RGB/16-bit, and exports uncompressed TIFFs without resizing. You do not need to type 21 slider combinations. Existing documents and source inputs are preserved. If any export fails, inspect `export-report.txt`; do not fill missing files with predictions.
2. Independently check that Camera Raw applied the requested settings and embedded linear profile, including `ProcessVersion=15.4`. The XMP now includes upstream's `HasSettings=True`. A saved TIFF, script or ICC profile **does not prove that Adobe honored the sliders**. Use one consistent build and record its actual Camera Raw version. If only Lightroom is available, manually import these paired inputs and apply the recorded settings; the Photoshop script cannot run there.
3. From the kit root, record hashes and import the completed folder:

```sh
python reference_import.py capture /path/to/exports --adobe-version "ACTUAL CAMERA RAW VERSION"
python reference_import.py import /path/to/exports --out imported-joint-references.json
python benchmark.py joint-gate /path/to/exports
```

`capture` validates all 21 TIFFs and generates `capture.json` with hashes and requested settings. It refuses to overwrite an existing capture record. The Adobe version is a **user assertion**, and actual slider application remains explicitly **unverified**. No manual hash entry is needed. An import checks exact job IDs, original input hashes, XMP settings/hashes, per-output hashes, metadata and pixel/profile contract, then emits 24×16 block luminances in linear ProPhoto order. It never modifies the TIFFs or old oracle JSON. Retain the TIFFs for spatial/edge analysis.

A successful import reports `fidelity_status: not_measured`. It proves capture-file consistency, not that those files were produced by Adobe or that a candidate matches them. Synthetic test fixtures live only in temporary test folders and are labelled `SYNTHETIC TEST ONLY`; their values are never installed as Adobe expectations. No real joint references have been imported here.

## Evaluate a real candidate

For the **existing public single-slider** benchmark, provide a JSON object `{"cases":{"scene1/default":[...],"scene1/S+100":[...],...}}` with 384 finite nonnegative linear-ProPhoto block luminances per required case, in the original 24×16 order. Obtain predictions from the candidate's genuine scene-output pipeline. Do not treat encoded TIFF samples as linear values.

```sh
python benchmark.py score predictions.json --out comparison.json
```

Exit 1 means an upstream distance allowance was exceeded; exit 2 means invalid/missing input. MAE/max use clipped gamma 1.8 encoding. Effect compares log2(candidate/default) against log2(Adobe/default), using only blocks where all four values exceed 1/4096 and Adobe values are below 0.9. Empty support is an error. Passing this gate still says nothing about joint fidelity.

For the **new joint capture batch**, run the real candidate on identical reduced DNGs and paired settings. Use the imported fresh controls and joints together; do not mix them with old public cases. Fit only scenes 1/3, assess scene 4 and then an independent photographic holdout before shipping an operator change. The importer is ready; a joint candidate and its fidelity gate remain unimplemented because real joint evidence is absent.

## Provenance and search boundary

`sources.json` pins RAWmakase `6c60222a927ec54cea9bb11624615b3d2baa6aa9` and PhotoCraft `a02f2ee41059d3312e7ff24a5af5edcac7b6435a`. All 14 vendored files are extracted directly from those **canonical Git blobs**, with SHA256s and original licenses preserved. `photocraft_wrapper.rs` is generated by the runner. The optional copied generators create procedural inputs, never Adobe expected outputs.

A bounded follow-up checked the latest three RAWmakase releases, three relevant research branches, and attachments in issues 475/496 comments. It found no usable paired joint oracle in those targets; details are in `public-oracle-search.json`. This is not an exhaustive search of every historical asset. The missing dependency is a legitimate fresh paired export batch, followed by photographic validation. No guessed operator patch was made.

The authored benchmark/acquisition harness and documentation are MIT licensed (LICENSE). Vendored RAWmakase files remain MIT licensed and PhotoCraft files remain MIT-or-Apache-2.0; their complete notices are in vendor/. Generated photocraft_wrapper.rs contains derived PhotoCraft helpers under those same upstream terms.

GitHub Actions checks the Python benchmark/importer harness and unchanged PhotoCraft tests on Windows. A successful run does not establish Adobe joint fidelity.

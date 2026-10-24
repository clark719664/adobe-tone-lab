# Adobe 18.7 preview oracle and native operator baseline

The free official Adobe DNG Converter 18.7 produces reproducible setting-dependent previews from these synthetic DNGs and sidecars. This unlocks a genuine **8-bit sRGB JPEG preview** oracle. It does **not** unlock the separate 16-bit ProPhoto TIFF contract or prove Lightroom export equivalence.

## Evidence and boundaries

`preview_reference/` contains 126 actual Adobe JPEGs with source, requested-XMP, converted-DNG, JPEG and decoded-pixel hashes, actual output CRS settings, application/version and explicit PreviewColorSpace metadata. The JPEGs do not embed ICC profiles; the converted DNG explicitly reports PreviewColorSpace=2 (sRGB). These are copied unmodified JPEG bytes, not predictions. Adobe binaries are not redistributed.

The acquisition worker independently verified: neutral→joint→neutral swaps reproduce neutral pixels exactly; output-embedded settings match requests; embedded XMP overrides conflicting sidecars; neutral and joint source DNG raw payloads remain identical after conversion and decompression; opposite joint and exposure controls change output. Proof records are under `preview_acquisition/verification/`. This is evidence for this converter/version/preview path, not every Adobe app or rendering path.

`preview_families.py` makes six spatial families with three exposure/range variants each, from known scene-linear neutral ProPhoto values. Each scene has default, four isolated controls and two joint settings. Train families were ramp/stripes/checker/spots. Coefficient fitting excluded rings/random_regions, and every coefficient was frozen before its validation scores were computed. Those same validation families were reused to judge multiple hypotheses, so they are a shared validation set, not an independent untouched test set for every hypothesis. They are now research-visible; future model selection and final testing need new untouched families. Original public scene 4 was inspected diagnostically before fitting and is not an unseen holdout for this experiment.

## Reproduce the existing real-oracle benchmark

Tested with Python 3.12, NumPy 2.3.5 and Pillow 12.3.0; Rust stable/native linker is needed for the unchanged operator. From the repository root:

```sh
python -m pip install -r requirements-preview.txt
python -m unittest discover -s . -v
python preview_benchmark.py --oracle preview_reference --families preview_reference/families.json --build-dir .build/preview --out preview-baseline-results.json
```

The benchmark compiles the **actual pinned PhotoCraft Rust operator**, with original numerical helpers and only serial scheduling shims. Its input is the Adobe **default JPEG**, and output is compared against the corresponding edited JPEG. This is deliberately labelled **conditional postrender prediction**, not RAW-stage engine equivalence. The complete original PhotoCraft module's eight tests previously passed; the separate native module remains unchanged.

Measured joint MAE: training 10.8562/255 across 24 cases; held-out families 9.6611/255 across 12 cases. Full single-slider, no-op and per-case metrics are in `preview-baseline-results.json`. The conditional comparison can be dominated by stage/default-transfer differences, so these are not whole-engine Camera Raw parity numbers.

The reusable benchmark verifies exact case identities/counts and declared splits, requested XMP hashes, actual output CRS settings against the family settings and saved output XMP, converter/version/sRGB metadata, pixel dimensions/bit depth/profile contract, JPEG hashes and decoded-pixel hashes before native prediction. Equivalent numeric CRS spellings are accepted. These checks prevent accidental reference/slider mixing; they do not cryptographically prove Adobe authorship of a supplied data pack.

## Rejected candidates

No candidate passed the generalization gate; none is recommended for production.

- Reversing spatial pass order: training's best baseline/reverse mix was exactly zero reverse contribution. Rejected before using held-out scores to choose a coefficient.
- Attenuating the native Shadows gain only when Highlights is active: one train-selected coefficient 0.4 changed training 10.8562→10.6219/255 and holdout 9.6611→9.6052/255. Held-out gain was only 0.0559 levels, with a worst regression of 0.7570 levels. Rejected as below a one-level target-rounding bound.
- Amplifying the native Highlights gain only when Shadows is active: train-selected coefficient 0.7 changed training 10.8562→9.4674/255, but holdout worsened 9.6611→10.2548/255, worst regression 3.7092 levels. Rejected.

The failed attenuation implementation and its coefficient are explicitly experimental/rejected; its tests check mechanics and holdout exclusion, not Adobe fidelity. Full failed measurements are in `preview_rejected_experiments/`.

For fixed predictions, changing every target channel by at most half an 8-bit level changes a paired MAE improvement by at most one level. This bounds **target rounding only**; it does not bound JPEG loss or the response to quantized neutral input.

Neutral clipping is real but does not explain the bulk error here: averaged across 36 joint cases, 7.94% of neutral pixels are clipped, and only 6.98% of native baseline absolute-error mass lies there. More than 93% of error lies on unclipped pixels. Full measurements are preserved. The next research step is a baseline consuming the known linear inputs with explicit neutral-transfer calibration, or the actual RAWmakase scene-stage kernel, rather than more global coupling fits on JPEGs. No replacement RAW operator has landed.

## Acquire new real previews without an account or installation

On Windows, the helper downloads the pinned **official free Adobe package** plus the pinned portable open-source extractor, verifies hashes and a valid Adobe signature, and extracts the needed files without running the installer. Existing authorized download/extraction steps were exercised; the complete preparation script was syntax-checked but not rerun over the working converter. The acquisition script itself was rerun on all 126 fixtures successfully.

```powershell
powershell -NoProfile -File preview_acquisition/prepare_converter.ps1 -Destination .build/adobe-cache
python preview_families.py .build/preview-input
python preview_acquisition/acquire_previews.py --converter ".build/adobe-cache/portable/app/Adobe DNG Converter.exe" --inputs .build/preview-input --out .build/new-adobe-previews
```

Use a fresh empty output folder. Acquisition rejects embedded-XMP inputs, verifies the exact converter executable hash, waits for exit status, checks every requested output CRS setting and preview metadata, and saves untouched JPEG/XMP bytes plus provenance. Its copied input DNGs and converted DNGs remain available for independent examination. Standard portable runs printed missing optional model warnings; the Basic-slider counterfactuals and unchanged raw payload tests still passed. Full Lightroom/Photoshop behavior is not inferred from that result.

Generated input values are never Adobe expectations. Never route these JPEGs through `reference_import.py` or replace the old frozen 18.7 ProPhoto JSON with preview values. A held-out photographic corpus and higher-precision exports remain necessary for broad fidelity claims.

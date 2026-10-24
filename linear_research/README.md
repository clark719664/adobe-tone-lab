# Native linear-stage falsification

This experiment found no justified joint Shadows/Highlights correction. It runs actual pinned RAWmakase scene-tone source on known scene-linear synthetic probes and uses a neutral transfer fitted only on twelve training defaults. An exact RGB counterfactual shows that errors inherited from the individual controls dominate the joint error. It does not establish complete Adobe pipeline reconstruction, Lightroom parity, or photograph performance.

On the 24 training joint cases, native baseline MAE is **14.0319/255**. Replacing only its interaction with Adobe's measured interaction leaves **14.7182/255** error; replacing the single-control errors instead leaves approximately **2.493/255**. These are diagnostic counterfactuals using reference outputs, not usable predictors. See `decomposition.json` for precise per-case and aggregate values. The old rings/random_regions cases were already research-visible and are diagnostics, not an independent final test.

The follow-up texture experiment did not establish a cause. Two training charts received `0.3*sin(2*pi*x/8)*sin(2*pi*y/8)` EV texture before16-bit quantization, without clipping (source maximum below1). No parameters changed. Shadows+100 MAE changed21.061→21.973 on stripes and19.986→19.648 on checker; default errors changed0.321→0.891 and3.017→3.191. One worsened and the other improved only slightly. This does not confirm texture as the explanation. Fourteen actual Adobe DNG Converter18.7 previews and synthetic inputs are included in `texture-diagnostic`; no Adobe executable is included.

## Native boundary

`vendor/` is unchanged MIT-licensed code/data from https://github.com/pch/rawmakase at6c60222a927ec54cea9bb11624615b3d2baa6aa9; `source-pins.json` records all SHA-256 values. `linear_probe.rs` is the integration wrapper. Its unused app interface structs do not replace evaluated filter code. The actual LocalToneMap guided/bilateral filters, context measurements and tables produce gains, followed by actual GlobalTone white/default-black tables. Positive Shadows shifts the default-black key by the median native shadow gain. The local map uses the source's image-relative radius and the full256×192 measurement image.

Known approximations: neutral grayscale mosaic values bypass demosaicing; camera/profile transforms are the probe's intended neutral ProPhoto mapping; the white maximum uses the full image rather than the engine's128-edge box reduction; default-profile/display behavior is represented by a shared monotone empirical transfer. The1025-point global LUT is interpolated. This is a source-grounded harness, not the full RAWmakase renderer. Real-photo and complete color-pipeline claims are unsupported.

Broad joint gain scaling and bounded3/6/10-feature residual models reduced mean error but failed case-regression guards. Their full searches are preserved in `linear-global-scale-search.json` and `linear-residual-search.json`. A briefly investigated palette-gated workaround was rejected as an arbitrary restriction and is not part of this package. Reserved diagonal_wave/soft_blobs/stepped_wedges final-validation families remain uncaptured.

## Reproduce

Requirements: Python with `requirements.txt`, Cargo/Rust supporting edition2024, a native compiler/linker. The original kit's `preview_reference` and generated source DNGs are inputs; no Adobe installation is needed to reproduce these measurements. From this directory, with paths replaced as appropriate:

```text
cargo build --locked --release --jobs 1
python -m unittest discover -s . -p "test_*.py" -v
python measure.py --inputs PATH/TO/GENERATED-DNGS --reference PATH/TO/preview_reference --cache scratch/cache --output scratch/baseline.json --refit-transfer scratch/transfer.npz
python decompose.py --manifest PATH/TO/preview_reference/families.json --previews PATH/TO/preview_reference/previews --cache scratch/cache --transfer scratch/transfer.npz --output scratch/decomposition.json
python measure.py --inputs texture-diagnostic/inputs --reference texture-diagnostic --cache scratch/texture-cache --output scratch/texture-baseline.json
python decompose.py --manifest texture-diagnostic/families.json --previews texture-diagnostic/previews --cache scratch/texture-cache --transfer neutral-transfer-global.npz --output scratch/texture-decomposition.json
```

To regenerate the original source DNGs, run the parent kit's `preview_families.py` into a fresh directory. The runner verifies their captured hashes, each JPEG hash, and requested/embedded Shadows/Highlights/exposure/process-version settings. It always reruns the native kernel into the supplied cache. Calibration refitting requires exactly the twelve defaults from ramp/stripes/checker/spots and checks its arrays equal the frozen calibration; it cannot learn from validation/default previews. Decomposition verifies reference and cache hashes and the exact per-pixel error identity.

Verification: a fresh build in this isolated package passed; **15 tests** passed, including actual native default/determinism/product checks, training calibration bounds, source hash mutation and setting mismatch rejection. A fresh native cache reproduced all126 baseline cases and the training calibration exactly. `package-sha256.json` pins distributable files. Build products, caches, and the proprietary Adobe converter are excluded.

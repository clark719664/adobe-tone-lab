# Adobe operator benchmark and joint-reference acquisition kit

This is a runnable first measurement milestone. It **does not reproduce Adobe's joint Shadows/Highlights operator**. No guessed operator patch was made: the public Adobe 18.7 fixtures have zero joint-slider cases, and the private joint TIFFs /17-photo stress references are unavailable.

## What runs

- `benchmark.py` scores exact linear-ProPhoto block arrays against the frozen public Camera Raw18.7 oracle. It reproduces RAWmakase's encoded MAE/max, supported-block effect error in EV, and accepted-distance allowances. Every candidate must supply all 15 scene cases (3 defaults + 12 edited). Both default and edited cases enter the regression gate. Scenes1/3 are designated train; scene 4 is held out. This split is for future candidates; no parameters were fitted here.
- `public-baseline.json` measures a deliberately unchanged operator using each **actual Adobe default** as the prediction for its edited case. These are genuine no-op errors, not fabricated Adobe outputs. Edited-case effect errors span 0.029778–0.266790EV; 2/12 edited cases fall within the upstream accepted distances. Those upstream distances are historical thresholds, not a fresh RAWmakase engine run. This benchmark is block-level; it does not prove pixel/photo parity.
- `run_photocraft.py` compiles the **actual unchanged pinned PhotoCraft Rust module** with its original numerical helpers and Encoding. Only parallel row/map scheduling is replaced by serial loops. It runs all 8 upstream tests plus the two upstream saved Photoshop 25.4 Camera Raw Filter grey measurements. It is neither a Python reimplementation nor a complete PhotoCraft app build.
- `acquisition/` contains 21 paired DNG+XMP jobs: default, S+100, H-100, S+50, H-50, S+100/H-100, S+50/H-50 for each of scenes 1/3/4. Inputs are exact copies of the actual upstream reduced384×256 DNGs. Hashes and settings are recorded per job. Frozen public18.7 block values came from different-resolution original captures; **never combine those old single-slider values with new reduced-DNG joint captures**.

## Reproduce from a checkout

From this repository root in PowerShell (Python3.10+; NumPy is needed only for the vendored generators; Pillow is needed only to validate future TIFF imports; Rust stable/native linker is needed for the competitor probe):

```powershell
$py = 'python' # or the path to your Python 3.10+ interpreter
& $py -m unittest discover -s . -v
& $py run_photocraft.py --build-dir work/build
& $py benchmark.py baseline --out public-baseline.json
& $py benchmark.py audit
# Exit 2 explicitly means joint oracle absent; it is not a passing fidelity test.
& $py benchmark.py joint-gate work/real-adobe-exports
# Expected exit 2 while the 21 paired exports are missing.
```

A real candidate prediction file has `{"cases":{"scene1/default":[...],"scene1/S+100":[...],...}}` with 384 finite nonnegative **linear-ProPhoto block luminances** per case. Render the frozen probe input using the candidate's genuine scene-output pipeline; do not use encoded TIFF values as linear inputs. Supply every required case, including defaults. Run `benchmark.py score predictions.json --out comparison.json`; exit 1 means an upstream distance allowance is exceeded, exit 2 means invalid/missing inputs. The arrays must preserve the original 24×16 block order. MAE/max use clipped gamma 1.8 encoding. Effect compares log2(candidate/default) against log2(Adobe/default), only where all four values exceed 1/4096 and Adobe values are below 0.9. Empty support is an error. This score is a **single-slider** anti-regression check; a passing score still cannot establish joint fidelity.

## Acquire the missing oracle with legitimate Adobe access

No Adobe software was installed or invoked here. A contributor who already has authorized access can:

1. Work on copies of `acquisition/inputs/`; retain these immutable originals and their hashes. Camera Raw may embed settings in a DNG, so apply the **recorded per-job settings** through its normal interface or existing upstream `camera_raw.py` workflow. A sidecar alone is not proof that Adobe used it. Check sliders, As Shot white balance, ProcessVersion 15.4, all other recorded controls, and the embedded linear profile before exporting. Do not apply an automatic preset.
2. Export all 21 files named by `acquisition/manifest.json`, without resizing, as unsigned 16-bit RGB TIFFs with embedded **ProPhoto RGB gamma 1.8**. Use the same Camera Raw build for all paired captures. Record its actual version. These inputs require **fresh defaults and singles**, as well as joints.
3. Copy `capture-template.json` to the export folder as `capture.json`; replace the version and each output SHA256 with values from the actual exports. Retain settings/input hashes. Do not fill placeholders with predictions. Keep unmodified TIFFs as the oracle.
4. Run `joint-gate EXPORT_FOLDER`. It checks every paired file, input/XMP/output hashes,384×256 size, unsigned 16-bit RGB tags, embedded ICC profile description and ProPhoto primaries. **It does not yet verify the ICC transfer curve or whether Adobe really applied each slider**; independently confirm gamma 1.8 and inspect settings/capture provenance before block reduction. Success only reports paired-export availability, not fidelity. Missing files fail instead of skip.
5. Reduce exported **decoded linear-ProPhoto** images into 24×16 block luminances using weights [0.2880402,0.7118741,0.0000857]. Preserve full-resolution TIFFs for spatial/edge analysis. Run a real candidate on those identical new inputs and paired settings. Fit only scenes 1/3 and assess scene 4 plus a separate photographic holdout before shipping an operator change. Do not replace existing frozen oracle values to make tests pass.

## Provenance and scope

`sources.json` pins RAWmakase 6c60222a927ec54cea9bb11624615b3d2baa6aa9 and PhotoCraft a02f2ee41059d3312e7ff24a5af5edcac7b6435a and records 14 vendored file SHA256s. MIT / MIT-or-Apache notices are retained. Sources in `vendor/` are unchanged. `photocraft_wrapper.rs` is generated from those sources by the runner; generated executables live only in the scratch build folder. There is no upstream source patch because evidence does not support a joint improvement yet.

The copied real generators `vendor/probe_dng.py` and `vendor/probe_scenes.py` are available for expanding the experiment. Their procedural scenes are not ground-truth Adobe renders. Existing scene JSON, competitor grey measurements and the new capture queue use distinct comparison contracts; their scores must not be pooled.

The authored benchmark/acquisition harness and documentation are MIT licensed (LICENSE). Vendored RAWmakase files remain MIT licensed and PhotoCraft files remain MIT-or-Apache-2.0; their complete notices are in vendor/. Generated photocraft_wrapper.rs contains derived PhotoCraft helpers under those same upstream terms. No Adobe application or private photographic reference corpus is distributed.

GitHub Actions checks the benchmark harness and unchanged PhotoCraft tests on Windows. This job does not validate Adobe joint fidelity.

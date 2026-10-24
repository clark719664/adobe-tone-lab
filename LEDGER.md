# Experiment ledger

2026-10-23 — evidence frozen before measurement

RAWmakase commit: 6c60222a927ec54cea9bb11624615b3d2baa6aa9.
PhotoCraft commit: a02f2ee41059d3312e7ff24a5af5edcac7b6435a.
Fourteen vendored source/data files have SHA256 pins; licenses are preserved.
Public Camera Raw 18.7 oracle: 61 cases, 27 scene cases, zero joint Shadows/Highlights cases. Three reduced DNGs are available; private stress-photo TIFFs are absent.

2026-10-23 — harness implementation

Nine initial tests failed before the benchmark module existed. Final 13 tests pass, including exact scoring, one-stop effect, invalid-input rejection, empty-support failure, fixture integrity, default-case regression, capture hashes and XML settings. An integrity test caught Windows newline translation affecting XMP hashes; hashing actual written bytes fixed it and all 21 jobs were regenerated.

The no-op operator uses frozen real Adobe defaults unchanged as its predictions. Across 12 edited cases its effect MAE spans 0.029778–0.266790 EV, with two edited cases within historical upstream distances; the overall gate fails. These quantify omitted slider effects. They are not a competitor fit or a fresh RAWmakase engine run. Held-out scene 4: S+100 0.252997 EV, S-50 0.135058 EV, H-100 0.266790 EV, H+50 0.121101 EV. No parameters fitted.

2026-10-23 — actual competitor execution

Compiled the unchanged PhotoCraft local_tone.rs with rustc. The wrapper uses original Encoding, luma, transfer, bilinear and box-mean helpers; only scheduling is serial. Initial compilation exposed missing wrapper dependencies, then original box_mean and serial par_map were supplied. The operator and constants remain unchanged. All eight upstream Rust tests pass without skips.

Saved Photoshop 25.4 grey oracle: S+100 165.3/255, measured 165.2136, error 0.08641052/255. H-100 89.6/255, measured 90.35554, error 0.75553894/255. Both are within the original five-level tolerance. This covers two single-slider grey spots, not joints, photographic holdouts or Adobe 18.7 parity.

2026-10-23 — joint reference acquisition boundary

Twenty-one paired DNG/XMP jobs: fourteen train and seven held-out scene 4. For each scene: fresh default, two Shadows singles, two Highlights singles, two joint settings. DNGs are byte-identical copies of pinned reduced inputs. Old full-resolution captures must not be mixed with these new captures.

Audit exits 2 with zero saved joint cases. Joint availability gate exits 2 because all 21 paired exports are missing. No TIFF was manufactured. Actual ICC transfer curve and slider application must be independently checked when legitimate exports become available; even an availability pass does not claim fidelity.

Decision: no unsupported operator fit or upstream patch. Required next evidence: legitimate paired Adobe exports on the exact capture inputs, then a real candidate run and independent photographic holdout. README contains commands, limitations and acquisition instructions.

2026-10-23 — importer and portability follow-up

The importer now uses only the Python standard library. It validates all 21paired jobs against original source/XMP hashes and exact settings metadata, decodes unsigned 16-bit uncompressed RGB TIFFs without 8-bit conversion, handles both byteorders and multiple strips, validates 384x256 geometry/ProPhoto primaries, checks every 65536 representable ICC input code for monotonic finite gamma 1.8 transfer within 0.003 linear tolerance, and emits 24x16 linear block luminances. Import success remains fidelity_status=not_measured and actual Adobe slider application unverified. Adobe version is user asserted, not detected from the pixels.

Independent review found sparse ICC sampling could miss a LUT spike and narrow parametric branch. Two regressions failed first, then all-code validation fixed them. Final 24 tests cover those cases, sampled/all five parametric ICC forms, BE/multiple-strip/nonuniform block order, truncation, corrupt strips, metadata/hash tampering, and a complete synthetic 21-file import. Synthetic fixtures are validation inputs only and never become Adobe expectations.

A manual-run Photoshop exporter now packages the upstream fresh-DNG/XMP workflow into one 21-export batch, including HasSettings=True. The script was not run in Adobe. Its source is syntax-checked with the #target directive removed for Node parsing; this does not verify Adobe APIs at runtime.

Source/input portability: canonical vendor bytes are extracted directly from the pinned Git blobs; .gitattributes preserves byte-hashed files. XMP generation uses explicit LF. No Adobe reference numbers changed. A fresh local Git clone with autocrlf disabled is part of final verification.

Bounded oracle follow-up: three latest release asset lists, complete trees of learned-local-tone / fix-camera-and-shadow-response / scene-tone-stage-design, and comments for issues 475/496 yielded no usable paired joint references. The first two branches have the same public probe JSON Gitblob as main. See public-oracle-search.json. External dependency remains legitimate same-build paired Adobe exports, then real candidate and photographic validation.

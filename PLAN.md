# Adobe joint Shadows / Highlights: implementation contract

Goal: measure actual existing operators against frozen Adobe evidence, preserve a scene holdout, and package deterministic acquisition inputs for missing joint references. Do not infer joint fidelity from single-slider tests.

Pinned sources: RAWmakase 6c60222a927ec54cea9bb11624615b3d2baa6aa9 (Camera Raw 18.7 probe measurements); PhotoCraft a02f2ee41059d3312e7ff24a5af5edcac7b6435a (actual local Laplacian source, Photoshop25.4 neutral-grey measurements). Sources remain unmodified.

1. Freeze public probe JSON, accepted engine distances, DNGs, generator and source hashes.
2. Add failing tests for exact scoring, invalid input rejection, source integrity, holdout split and missing joint-reference failure.
3. Implement a dependency-light evaluator, compile the actual PhotoCraft module using a sequential scheduling shim, execute its saved Adobe grey probes and upstream tests. This does not claim a complete PhotoCraft app run.
4. Package immutable probe DNG copies, explicitly paired default / single / joint XMP settings and an export manifest. Gate reference import by actual file presence, metadata and hashes, never auto-bless.
5. Report measured results and the unsolved fidelity boundary. An operator change requires paired joint evidence and a held-out scene with anti-regression; absent that evidence, ship the runnable benchmark/acquisition kit and no guessed operator patch.

Original experiment scope: authored benchmark and acquisition artifacts, with scratch builds kept separate. No Adobe installation, login, payment or export automation was performed. This repository publishes the research milestone.

Ledger start: public scene references expose 384 block luminances per scene/case, not full TIFFs. Baselines are accepted upstream distances, not fresh local engine renders. Full joint TIFFs and the private stress photos are absent from this clone. Confirm with machine-readable audit.

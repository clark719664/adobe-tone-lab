#target photoshop
// Manually run only in an existing licensed Photoshop installation.
// Requested XMP settings are not proof that Camera Raw applied every setting.
// Workflow adapted from pch/rawmakase, MIT; see ../vendor/rawmakase-LICENSE.
(function () {
 var root = new File($.fileName).parent;
 var outDir = Folder.selectDialog("Choose an EMPTY folder for the 21 paired Adobe reference TIFFs");
 if (!outDir) return;
 var jobs = [{"id": "scene1__default", "input": "inputs/scene1__default.dng", "xmp": "inputs/scene1__default.xmp", "output": "scene1__default.tif"}, {"id": "scene1__S+100", "input": "inputs/scene1__S+100.dng", "xmp": "inputs/scene1__S+100.xmp", "output": "scene1__S+100.tif"}, {"id": "scene1__H-100", "input": "inputs/scene1__H-100.dng", "xmp": "inputs/scene1__H-100.xmp", "output": "scene1__H-100.tif"}, {"id": "scene1__S+50", "input": "inputs/scene1__S+50.dng", "xmp": "inputs/scene1__S+50.xmp", "output": "scene1__S+50.tif"}, {"id": "scene1__H-50", "input": "inputs/scene1__H-50.dng", "xmp": "inputs/scene1__H-50.xmp", "output": "scene1__H-50.tif"}, {"id": "scene1__S+100_H-100", "input": "inputs/scene1__S+100_H-100.dng", "xmp": "inputs/scene1__S+100_H-100.xmp", "output": "scene1__S+100_H-100.tif"}, {"id": "scene1__S+50_H-50", "input": "inputs/scene1__S+50_H-50.dng", "xmp": "inputs/scene1__S+50_H-50.xmp", "output": "scene1__S+50_H-50.tif"}, {"id": "scene3__default", "input": "inputs/scene3__default.dng", "xmp": "inputs/scene3__default.xmp", "output": "scene3__default.tif"}, {"id": "scene3__S+100", "input": "inputs/scene3__S+100.dng", "xmp": "inputs/scene3__S+100.xmp", "output": "scene3__S+100.tif"}, {"id": "scene3__H-100", "input": "inputs/scene3__H-100.dng", "xmp": "inputs/scene3__H-100.xmp", "output": "scene3__H-100.tif"}, {"id": "scene3__S+50", "input": "inputs/scene3__S+50.dng", "xmp": "inputs/scene3__S+50.xmp", "output": "scene3__S+50.tif"}, {"id": "scene3__H-50", "input": "inputs/scene3__H-50.dng", "xmp": "inputs/scene3__H-50.xmp", "output": "scene3__H-50.tif"}, {"id": "scene3__S+100_H-100", "input": "inputs/scene3__S+100_H-100.dng", "xmp": "inputs/scene3__S+100_H-100.xmp", "output": "scene3__S+100_H-100.tif"}, {"id": "scene3__S+50_H-50", "input": "inputs/scene3__S+50_H-50.dng", "xmp": "inputs/scene3__S+50_H-50.xmp", "output": "scene3__S+50_H-50.tif"}, {"id": "scene4__default", "input": "inputs/scene4__default.dng", "xmp": "inputs/scene4__default.xmp", "output": "scene4__default.tif"}, {"id": "scene4__S+100", "input": "inputs/scene4__S+100.dng", "xmp": "inputs/scene4__S+100.xmp", "output": "scene4__S+100.tif"}, {"id": "scene4__H-100", "input": "inputs/scene4__H-100.dng", "xmp": "inputs/scene4__H-100.xmp", "output": "scene4__H-100.tif"}, {"id": "scene4__S+50", "input": "inputs/scene4__S+50.dng", "xmp": "inputs/scene4__S+50.xmp", "output": "scene4__S+50.tif"}, {"id": "scene4__H-50", "input": "inputs/scene4__H-50.dng", "xmp": "inputs/scene4__H-50.xmp", "output": "scene4__H-50.tif"}, {"id": "scene4__S+100_H-100", "input": "inputs/scene4__S+100_H-100.dng", "xmp": "inputs/scene4__S+100_H-100.xmp", "output": "scene4__S+100_H-100.tif"}, {"id": "scene4__S+50_H-50", "input": "inputs/scene4__S+50_H-50.dng", "xmp": "inputs/scene4__S+50_H-50.xmp", "output": "scene4__S+50_H-50.tif"}];
 var oldDialogs = app.displayDialogs;
 var failures = [], exported = 0;
 var scratch = new Folder(outDir.fsName + "/capture-input-copies");
 if (scratch.exists) throw new Error("Choose a fresh output folder; capture-input-copies already exists.");
 scratch.create();
 app.displayDialogs = DialogModes.NO;
 try {
  for (var i = 0; i < jobs.length; i++) {
   var j = jobs[i], doc = null;
   try {
    var dest = new File(outDir.fsName + "/" + j.output);
    if (dest.exists) throw new Error("Output already exists: " + dest.fsName);
    var raw = new File(scratch.fsName + "/" + j.id + ".dng");
    var sidecar = new File(scratch.fsName + "/" + j.id + ".xmp");
    if (!new File(root.fsName + "/" + j.input).copy(raw.fsName)) throw new Error("DNG copy failed");
    if (!new File(root.fsName + "/" + j.xmp).copy(sidecar.fsName)) throw new Error("XMP copy failed");
    var options = new CameraRAWOpenOptions();
    options.bitsPerChannel = BitsPerChannelType.SIXTEEN;
    options.colorSpace = ColorSpaceType.PROPHOTORGB;
    doc = app.open(raw, options);
    if (doc.bitsPerChannel != BitsPerChannelType.SIXTEEN) throw new Error("Expected 16-bit document");
    if (doc.colorProfileName != "ProPhoto RGB") throw new Error("Unexpected profile: " + doc.colorProfileName);
    if (doc.width.as("px") != 384 || doc.height.as("px") != 256) throw new Error("Unexpected dimensions");
    var settings = new TiffSaveOptions();
    settings.imageCompression = TIFFEncoding.NONE;
    settings.embedColorProfile = true;
    settings.layers = false;
    doc.saveAs(dest, settings, true);
    exported++;
   } catch (e) { failures.push(j.id + ": " + e); }
   finally { if (doc) doc.close(SaveOptions.DONOTSAVECHANGES); }
  }
 } finally { app.displayDialogs = oldDialogs; }
 var report = new File(outDir.fsName + "/export-report.txt");
 report.encoding = "UTF-8"; report.open("w");
 report.write("Paired exports: " + exported + "/21\nRequested XMP settings: application unverified.\n" + failures.join("\n"));
 report.close();
 alert("Exported " + exported + "/21 references. " + failures.length + " failures.\nReview Camera Raw settings/version, then run reference_import.py capture and import.");
})();

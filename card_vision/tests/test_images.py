"""Image and batch regressions: real file decoding, isolation, outputs and CLI."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from cardvision.batch import run_batch
from cardvision.config import load_config
from cardvision.models import Status
from cardvision.sources import VideoSource, read_image, write_image
from cardvision.ui import overlay
from cardvision.vision.pipeline import VisionPipeline

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("image_demo",ROOT/"tools"/"generate_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class ImageTests(unittest.TestCase):
    def test_independent_images_classify_immediately_without_video_history(self):
        pipeline = VisionPipeline(load_config())
        for status in (Status.CORRECT,Status.REVERSED,Status.CHIP_NOT_VISIBLE):
            _,obs = pipeline.process_image(demo.synthetic_frame(status.value))
            self.assertEqual(obs.status,status)
            self.assertIsNone(obs.debug["quality"]["motion"])
        # Image review must not create video motion evidence.
        self.assertIsNone(pipeline.previous)
        _,video = pipeline.process(demo.synthetic_frame("CORRECT"),0,0)
        self.assertEqual(video.reason,"motion_or_first_frame")

    def test_image_quality_and_orientation_gates_are_preserved(self):
        pipeline = VisionPipeline(load_config())
        _,vertical = pipeline.process_image(demo.synthetic_frame("CORRECT",angle=90))
        self.assertEqual(vertical.status,Status.UNKNOWN)
        blurred = cv2.GaussianBlur(demo.synthetic_frame("CORRECT"),(71,71),25)
        self.assertEqual(pipeline.process_image(blurred)[1].status,Status.UNKNOWN)

    def test_image_extensions_unicode_and_corrupt_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as tmp:
            root = Path(tmp)
            for suffix in (".JPG",".JPEG",".PNG"):
                path = root/("카드"+suffix)
                write_image(path,demo.synthetic_frame("CORRECT"))
                source = VideoSource(path)
                try:
                    self.assertTrue(source.is_image)
                    _,obs = VisionPipeline(load_config()).process_image(source.read()[1])
                    self.assertEqual(obs.status,Status.CORRECT)
                finally:
                    source.close()
            path = root/"corrupt.jpg"
            path.write_bytes(b"not an image")
            with self.assertRaisesRegex(OSError,"Cannot decode image"):
                VideoSource(path)

    def test_overlay_and_geometry_metadata(self):
        cfg = load_config()
        frame,obs = VisionPipeline(cfg).process_image(demo.synthetic_frame("CORRECT"))
        view = overlay(frame,obs,None,cfg,True,1,1.,still_image=True)
        self.assertEqual(view.shape,(800,960,3))
        self.assertFalse(np.array_equal(view[:540],frame))
        metadata = obs.record()
        self.assertEqual(len(metadata["card_quad"]),4)
        self.assertEqual(len(metadata["chip_polygon"]),4)
        json.dumps(metadata,allow_nan=False)


class BatchTests(unittest.TestCase):
    def test_recursive_groups_labels_annotation_collisions_and_corrupt_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as tmp:
            root = Path(tmp)/"inputs"
            for name in ("internet","phone"):
                (root/name).mkdir(parents=True)
            correct = demo.synthetic_frame("CORRECT")
            write_image(root/"internet"/"같은이름.JPG",correct)
            write_image(root/"internet"/"같은이름.png",correct)
            write_image(root/"phone"/"photo.JPEG",demo.synthetic_frame("REVERSED"))
            (root/"phone"/"broken.png").write_bytes(b"broken")
            (root/"phone"/"ignored.txt").write_text("ignored")
            labels = [{"file":"internet/같은이름.JPG","status":"CORRECT","card_present":True,"chip_visible":True},
                      {"file":"phone/photo.JPEG","status":"CORRECT","card_present":True,"chip_visible":True}]
            label_path = Path(tmp)/"labels.json"
            label_path.write_text(json.dumps(labels),encoding="utf-8")
            run = run_batch(root,Path(tmp)/"output",load_config(),recursive=True,save_annotated=True,labels_path=label_path)
            report = json.loads((run/"results.json").read_text(encoding="utf-8"))
            summary = report["summary"]
            self.assertEqual(summary["total_images"],4)
            self.assertEqual(summary["processed_images"],3)
            self.assertEqual(summary["read_or_processing_errors"],1)
            self.assertEqual(summary["classification_accuracy"],.5)
            self.assertEqual(summary["by_group"]["internet"]["classification_accuracy"],1.)
            self.assertEqual(summary["by_group"]["phone"]["classification_accuracy"],0.)
            images = [row for row in report["images"] if row["error"] is None]
            self.assertEqual(len({r["annotated_path"] for r in images}),3)
            for row in images:
                self.assertIsNotNone(row["card_box"])
                self.assertIsNotNone(row["chip_image_box"])
                self.assertGreater(row["processing_ms"],0)
                self.assertIsNotNone(read_image(run/row["annotated_path"]))
            with (run/"results.csv").open(encoding="utf-8-sig",newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(len(csv_rows),4)
            self.assertIn("internet/같은이름.JPG",[r["file"] for r in csv_rows])
            corrupt = next(r for r in report["images"] if r["error"] is not None)
            self.assertIsNone(corrupt["card_detected"])

    def test_no_implicit_image_saving_and_nested_output_is_excluded(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as tmp:
            root = Path(tmp)
            write_image(root/"card.png",demo.synthetic_frame("CORRECT"))
            output = root/"results"
            first = run_batch(root,output,load_config(),save_annotated=True)
            second = run_batch(root,output,load_config(),recursive=True)
            self.assertNotEqual(first,second)
            report = json.loads((second/"results.json").read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["total_images"],1)
            self.assertIsNone(report["summary"]["classification_accuracy"])
            self.assertFalse((second/"annotated").exists())

    def test_bad_folders_and_empty_input_fail_clearly(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as tmp:
            root = Path(tmp)
            for folder,output in ((root/"missing",root/"out"),(root,root/"out"),(root,root)):
                with self.subTest(folder=folder,output=output), self.assertRaises(ValueError):
                    run_batch(folder,output,load_config())

    def test_annotation_error_preserves_detection_and_continues(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as tmp:
            root = Path(tmp)/"input"
            root.mkdir()
            write_image(root/"card.png",demo.synthetic_frame("CORRECT"))
            with patch("cardvision.batch.write_image",side_effect=OSError("simulated disk error")):
                run = run_batch(root,Path(tmp)/"out",load_config(),save_annotated=True)
            report = json.loads((run/"results.json").read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["processed_images"],1)
            self.assertEqual(report["summary"]["annotation_errors"],1)
            self.assertEqual(report["images"][0]["status"],"CORRECT")

    def test_single_image_cli_never_issues_actuator_command(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as tmp:
            root = Path(tmp)
            write_image(root/"card.PNG",demo.synthetic_frame("CORRECT"))
            result = subprocess.run([sys.executable,str(ROOT/"main.py"),"--source",str(root/"card.PNG"),
                                     "--headless","--simulate-acks","--output",str(root/"out")],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            log = next((root/"out"/"logs").glob("*.jsonl"))
            events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertNotIn("command",[e["kind"] for e in events])
            observation = next(e for e in events if e["kind"]=="observation")
            self.assertEqual(observation["status"],"CORRECT")
            self.assertEqual(observation["controller_state"],"IMAGE_REVIEW")

    def test_unknown_image_failure_saving_keeps_annotations(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as tmp:
            root = Path(tmp)
            write_image(root/"vertical.png",demo.synthetic_frame("CORRECT",angle=90))
            result = subprocess.run([sys.executable,str(ROOT/"main.py"),"--source",str(root/"vertical.png"),
                                     "--headless","--save-annotated","--save-failures","--output",str(root/"out")],
                                    capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            saved = next((root/"out"/"frames").rglob("*.png"))
            self.assertEqual(read_image(saved).shape,(800,960,3))


if __name__ == "__main__":
    unittest.main()

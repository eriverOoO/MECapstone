"""Keep permissive geometry except for the known large AND wide failure class."""
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
import yaml
from cardvision.config import load_config
from cardvision.sources import read_image
from cardvision.vision.chip_detector import ChipDetector
from cardvision.vision.chip_geometry import oversized_and_wide
from cardvision.vision.pipeline import VisionPipeline

ROOT=Path(__file__).resolve().parents[1]


class ChipGeometryTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()["chip"]

    def test_two_known_hologram_dimensions_are_rejected(self):
        for box in ((21,199,139,90),(78,204,115,65)):
            self.assertTrue(oversized_and_wide(box,(404,640,3),self.cfg))

    def test_large_or_wide_alone_does_not_reject(self):
        for box in ((80,140,86,70),(80,140,90,70),(70,120,120,110),(80,140,100,58)):
            with self.subTest(box=box):
                self.assertFalse(oversized_and_wide(box,(404,640,3),self.cfg))

    def test_large_square_contact_still_passes_detector(self):
        card=np.full((404,640,3),(155,90,45),np.uint8)
        cv2.rectangle(card,(70,120),(189,229),(45,175,215),-1)
        cv2.rectangle(card,(70,120),(189,229),(25,35,40),2)
        for x in (110,150):
            cv2.line(card,(x,122),(x,227),(25,35,40),2)
        for y in (155,190):
            cv2.line(card,(72,y),(187,y),(25,35,40),2)
        candidates,_=ChipDetector(self.cfg).detect(card)
        self.assertTrue(any(c.score>=self.cfg["min_score"] for c in candidates))

    def test_filter_can_be_disabled_or_relaxed(self):
        self.cfg["large_wide_filter"]=False
        self.assertFalse(oversized_and_wide((0,0,139,90),(404,640,3),self.cfg))
        self.cfg["large_wide_filter"]=True
        self.cfg["large_wide_area_min"]=.035
        self.assertFalse(oversized_and_wide((0,0,115,65),(404,640,3),self.cfg))

    def test_invalid_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/test") as folder:
            path=Path(folder)/"config.yaml"
            for key,value in (("large_wide_filter",1),("large_wide_area_min",0),
                              ("large_wide_area_min",float("nan")),("large_wide_aspect_min",-1)):
                cfg=load_config()
                cfg["chip"][key]=value
                path.write_text(yaml.safe_dump(cfg),encoding="utf-8")
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    load_config(path)


@unittest.skipUnless(all((ROOT/"data/test/topdown_kit/images"/name).exists() for name in
                         ("originals/sbi_back.jpg","planar_variants/sbi_back__dim_0.jpg")),"Optional downloaded SBI fixtures")
class RealHologramRegressionTests(unittest.TestCase):
    def test_both_remaining_holograms_become_back_estimates(self):
        pipeline=VisionPipeline(load_config())
        for name in ("originals/sbi_back.jpg","planar_variants/sbi_back__dim_0.jpg"):
            with self.subTest(file=name):
                _,obs=pipeline.process_image(read_image(ROOT/"data/test/topdown_kit/images"/name))
                self.assertFalse(obs.chip_detected)
                self.assertEqual(obs.card_class,"BACK_LIKELY")
                self.assertTrue(any(r["reason"]=="large_and_wide_chip_candidate" and r["score"]>=.6 for r in obs.rejected_chips))


if __name__=="__main__":
    unittest.main()

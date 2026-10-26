"""Position-gating and same-color contact regression tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
import yaml
from cardvision.config import load_config
from cardvision.models import Observation,Status
from cardvision.sources import read_image
from cardvision.vision.chip_detector import ChipDetector
from cardvision.vision.chip_position import expected_regions,position_allowed
from cardvision.vision.pipeline import VisionPipeline

ROOT=Path(__file__).resolve().parents[1]


def contact(card: np.ndarray, box: tuple[int,int,int,int], silver: bool = False) -> None:
    x,y,w,h=box
    cv2.rectangle(card,(x,y),(x+w-1,y+h-1),(185,185,185) if silver else (45,175,215),-1)
    cv2.rectangle(card,(x,y),(x+w-1,y+h-1),(25,35,40),2)
    for fraction in (1/3,2/3):
        cv2.line(card,(x+2,round(y+h*fraction)),(x+w-3,round(y+h*fraction)),(25,35,40),2)
        cv2.line(card,(round(x+w*fraction),y+2),(round(x+w*fraction),y+h-3),(25,35,40),2)


class PositionTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()["chip"]

    def test_margin_and_center_only_tolerance(self):
        shape=(400,640,3)
        # Center at (0.11,0.30): outside nominal window, inside loose margins.
        self.assertTrue(position_allowed((60,110,20,20),shape,self.cfg))
        self.assertTrue(position_allowed((50,130,150,100),shape,self.cfg))
        self.assertFalse(position_allowed((550,120,90,70),shape,self.cfg))
        self.assertFalse(position_allowed((70,270,90,60),shape,self.cfg))

    def test_180_degree_equivalence_and_disabled_filter(self):
        shape=(400,640,3)
        for box in ((70,130,80,70),(550,130,60,60),(90,260,80,60),(270,160,70,70)):
            x,y,w,h=box
            turned=(640-x-w,400-y-h,w,h)
            self.assertEqual(position_allowed(box,shape,self.cfg),position_allowed(turned,shape,self.cfg))
        self.cfg["position_filter"]=False
        self.assertTrue(position_allowed((550,120,90,70),shape,self.cfg))
        self.assertEqual(expected_regions(self.cfg),[])

    def test_outside_high_score_does_not_compete_with_real_chip(self):
        card=np.full((400,640,3),(155,90,45),np.uint8)
        contact(card,(80,135,70,75),silver=True)
        contact(card,(460,300,70,75))
        candidates,debug=ChipDetector(self.cfg).detect(card)
        self.assertTrue(candidates)
        x,y,w,h=candidates[0].box
        self.assertLess((x+w/2)/640,.34)
        self.assertGreater(candidates[0].score,self.cfg["min_score"])
        self.assertTrue(any(r["score"]>=self.cfg["min_score"] for r in debug["rejected_chip_candidates"]))

    def test_only_off_position_chip_is_rejected(self):
        card=np.full((400,640,3),(155,90,45),np.uint8)
        contact(card,(75,265,80,75))
        candidates,debug=ChipDetector(self.cfg).detect(card)
        self.assertEqual(candidates,[])
        self.assertTrue(debug["rejected_chip_candidates"])

    def test_edge_branch_recovers_gold_contact_on_gold_card(self):
        card=np.full((400,640,3),(35,165,205),np.uint8)
        contact(card,(85,135,70,70))
        color_cfg=copy.deepcopy(self.cfg)
        color_cfg["edge_candidates"]=False
        color_candidates,_=ChipDetector(color_cfg).detect(card)
        self.assertFalse(any(c.score>=self.cfg["min_score"] for c in color_candidates))
        candidates,_=ChipDetector(self.cfg).detect(card)
        self.assertTrue(candidates)
        self.assertEqual(candidates[0].method,"edge")
        self.assertGreaterEqual(candidates[0].score,self.cfg["min_score"])

    def test_same_contact_proposals_are_deduplicated(self):
        card=np.full((400,640,3),(155,90,45),np.uint8)
        contact(card,(80,135,70,75))
        candidates,_=ChipDetector(self.cfg).detect(card)
        strong=[c for c in candidates if c.score>=self.cfg["min_score"]]
        self.assertEqual(len(strong),1)

    def test_class_aliases_preserve_controller_contract(self):
        aliases=((Status.CORRECT,"FRONT_CORRECT"),(Status.REVERSED,"FRONT_REVERSED"),
                 (Status.CHIP_NOT_VISIBLE,"BACK_LIKELY"),(Status.UNKNOWN,"UNKNOWN"))
        for status,alias in aliases:
            obs=Observation(0,0,status)
            self.assertEqual(obs.card_class,alias)
            record=obs.record()
            self.assertEqual(record["status"],status.value)
            self.assertEqual(record["card_class"],alias)
            json.dumps(record,ensure_ascii=False)

    def test_configuration_rejects_invalid_regions(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/test") as folder:
            path=Path(folder)/"bad.yaml"
            for key,value in (("expected_region",[.1,.2,.7,.8]),("expected_region",[.3,.5,.2,.6]),
                              ("position_margin",[-.01,.02]),("position_margin",[.2,.02]),
                              ("position_filter","yes"),("edge_candidates",1)):
                cfg=load_config()
                cfg["chip"][key]=value
                path.write_text(yaml.safe_dump(cfg),encoding="utf-8")
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    load_config(path)


@unittest.skipUnless((ROOT/"data/test/topdown_kit/images/originals/aircash_back.jpg").exists(),"Optional downloaded card fixtures")
class RealImageRegressionTests(unittest.TestCase):
    def test_rejected_hologram_and_recovered_visa_contact(self):
        pipeline=VisionPipeline(load_config())
        directory=ROOT/"data/test/topdown_kit/images/originals"
        _,back=pipeline.process_image(read_image(directory/"aircash_back.jpg"))
        self.assertEqual(back.card_class,"BACK_LIKELY")
        self.assertFalse(back.chip_detected)
        self.assertTrue(any(r["score"]>=.6 for r in back.rejected_chips))
        _,front=pipeline.process_image(read_image(directory/"piraeus_visa_front.jpg"))
        self.assertEqual(front.card_class,"FRONT_REVERSED")
        self.assertTrue(front.chip_detected)
        self.assertLess(front.chip_relative[0],.34)
        self.assertTrue(front.expected_chip_regions)


if __name__=="__main__":
    unittest.main()

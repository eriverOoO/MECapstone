"""Stage search-window tolerance, card presence, coordinates and motion scope."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
import yaml
from cardvision.config import load_config
from cardvision.models import Status
from cardvision.ui import overlay
from cardvision.vision.pipeline import VisionPipeline

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("stage_demo",ROOT/"tools/generate_demo.py")
demo=importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def stage_frame(angle: float = 0, dx: int = 0, dy: int = 0) -> np.ndarray:
    """Synthetic dark stage only; this does not model real filament reflectance."""
    frame=demo.synthetic_frame("CORRECT",angle=angle,offset=dx)
    frame=cv2.warpAffine(frame,np.float32([[1,0,0],[0,1,dy]]),(960,540),borderValue=(32,32,32))
    background=np.all(frame==32,axis=2)
    texture=np.repeat((12+(np.arange(540)%8==0)*3).astype(np.uint8)[:,None],960,axis=1)
    frame[background]=np.repeat(texture[:,:,None],3,axis=2)[background]
    return frame


class StageRoiTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()
        # Deliberately start with a window close to nominal card dimensions;
        # additional margin must let the actual card move beyond that rectangle.
        self.cfg["card"]["fixed_roi"]=[242,120,476,300]
        self.cfg["card"]["roi_padding_fraction"]=.15

    def test_shift_and_small_rotation_use_actual_card_not_window_edges(self):
        for dx,dy,angle in ((0,0,0),(35,18,6),(-35,-18,-6),(30,-15,-5)):
            with self.subTest(dx=dx,dy=dy,angle=angle):
                pipeline=VisionPipeline(self.cfg)
                _,obs=pipeline.process_image(stage_frame(angle,dx,dy))
                self.assertEqual(obs.status,Status.CORRECT,obs.reason)
                self.assertEqual(obs.inspection_roi,(171,75,618,390))
                center=np.mean(obs.card_quad,axis=0)
                self.assertLess(np.linalg.norm(center-np.array([480+dx,270+dy])),4)
                self.assertAlmostEqual(obs.chip_relative[0],.8,delta=.04)
                self.assertAlmostEqual(obs.chip_relative[1],.473,delta=.04)
                self.assertLess(np.linalg.norm(obs.card_quad[1]-obs.card_quad[0]),510)

    def test_empty_dark_stage_is_not_assumed_to_be_card(self):
        frame=np.full((540,960,3),12,np.uint8)
        frame[::8]=15
        _,obs=VisionPipeline(self.cfg).process_image(frame)
        self.assertFalse(obs.card_detected)
        self.assertEqual(obs.status,Status.UNKNOWN)
        self.assertIsNotNone(obs.inspection_roi)

    def test_outside_search_window_is_not_processed_as_card(self):
        self.cfg["card"]["fixed_roi"]=[20,20,100,100]
        _,obs=VisionPipeline(self.cfg).process_image(stage_frame())
        self.assertFalse(obs.card_detected)

    def test_window_expansion_clips_to_image_bounds(self):
        self.cfg["card"]["fixed_roi"]=[10,10,940,520]
        _,obs=VisionPipeline(self.cfg).process_image(stage_frame())
        self.assertEqual(obs.inspection_roi,(0,0,960,540))
        self.assertEqual(obs.status,Status.CORRECT)
        self.cfg["card"]["fixed_roi"]=[2000,2000,100,100]
        self.assertFalse(VisionPipeline(self.cfg).process_image(stage_frame())[1].card_detected)

    def test_movement_outside_window_does_not_reset_observation(self):
        pipeline=VisionPipeline(self.cfg)
        frame=stage_frame()
        pipeline.process(frame,0,0)
        changed=frame.copy()
        changed[:60]=255
        _,obs=pipeline.process(changed,1,.1)
        self.assertEqual(obs.status,Status.CORRECT)
        self.assertEqual(obs.debug["quality"]["motion"],0)

    def test_card_cut_by_actual_search_boundary_is_unknown(self):
        self.cfg["card"]["roi_padding_fraction"]=0
        self.cfg["card"]["fixed_roi"]=[350,150,350,250]
        _,obs=VisionPipeline(self.cfg).process_image(stage_frame())
        self.assertFalse(obs.card_detected)
        self.assertEqual(obs.status,Status.UNKNOWN)

    def test_search_region_is_visible_and_serialized(self):
        frame,obs=VisionPipeline(self.cfg).process_image(stage_frame())
        rendered=overlay(frame,obs,None,self.cfg,True,1,1.,still_image=True)
        self.assertFalse(np.array_equal(rendered[75,171],frame[75,171]))
        self.assertEqual(obs.record()["inspection_roi"],(171,75,618,390))

    def test_invalid_roi_configuration_fails_early(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/test") as folder:
            config=Path(folder)/"config.yaml"
            for key,value in (("fixed_roi",[1.5,2,30,40]),("fixed_roi",[1,2,-3,40]),
                              ("roi_padding_fraction",-.1),("roi_padding_fraction",.9),
                              ("roi_padding_fraction",float("nan"))):
                cfg=load_config()
                cfg["card"][key]=value
                config.write_text(yaml.safe_dump(cfg),encoding="utf-8")
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    load_config(config)


if __name__=="__main__":
    unittest.main()

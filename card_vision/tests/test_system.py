import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
from cardvision.config import load_config
from cardvision.control import Controller, MockActuator
from cardvision.models import Action, Observation, Status
from cardvision.sources import VideoSource
from cardvision.vision.geometry import classify, order_quad
from cardvision.vision.pipeline import Stabilizer, VisionPipeline

ROOT=Path(__file__).resolve().parents[1]


def tool_module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"tools"/f"{name}.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()["orientation"]
        self.quad=np.array([[0,0],[160,0],[160,100],[0,100]],np.float32)

    def test_all_inlet_sides_and_stage_rotation(self):
        self.assertEqual(classify(self.quad,(130,50),self.cfg)[0],Status.CORRECT)
        self.assertEqual(classify(self.quad,(30,50),self.cfg)[0],Status.REVERSED)
        self.cfg["inlet"]="left"
        self.assertEqual(classify(self.quad,(30,50),self.cfg)[0],Status.CORRECT)
        vertical=order_quad(np.array([[0,0],[100,0],[100,160],[0,160]],np.float32))
        self.cfg["inlet"]="down"
        self.assertEqual(classify(vertical,(50,130),self.cfg)[0],Status.CORRECT)
        self.cfg["inlet"]="up"
        self.assertEqual(classify(vertical,(50,30),self.cfg)[0],Status.CORRECT)
        self.cfg["image_to_stage"]=[[0,1,0],[-1,0,160],[0,0,1]]
        self.assertEqual(classify(self.quad,(130,50),self.cfg)[0],Status.CORRECT)

    def test_vertical_dead_zone_and_mirror(self):
        self.assertEqual(classify(self.quad,(80,50),self.cfg)[0],Status.UNKNOWN)
        self.cfg["inlet"]="up"
        self.assertEqual(classify(self.quad,(130,50),self.cfg)[0],Status.UNKNOWN)
        self.cfg["inlet"]="left"
        self.cfg["image_to_stage"]=[[-1,0,160],[0,1,0],[0,0,1]]
        self.assertEqual(classify(self.quad,(130,50),self.cfg)[0],Status.CORRECT)

    def test_corner_order_does_not_flip_classification(self):
        for shift in range(4):
            for points in (np.roll(self.quad,shift,axis=0),np.roll(self.quad[::-1],shift,axis=0)):
                self.assertEqual(classify(order_quad(points),(130,50),self.cfg)[0],Status.CORRECT)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()
        self.controller=Controller(self.cfg["control"],3)
        self.frame=0

    def feed(self,status,n=3,card=True):
        command=None
        for _ in range(n):
            self.frame+=1
            candidate=self.controller.observe(Observation(self.frame,self.frame/30,status,card_detected=card),now=0)
            command=candidate or command
        return command

    def test_flip_rotate_insert_with_fresh_observations(self):
        flip=self.feed(Status.CHIP_NOT_VISIBLE)
        self.assertEqual(flip.action,Action.FLIP)
        self.assertIsNone(self.feed(Status.CORRECT))
        self.assertFalse(self.controller.acknowledge(999,True,now=0))
        self.assertTrue(self.controller.acknowledge(flip.command_id,True,now=0))
        self.assertIsNone(self.feed(Status.REVERSED,2))
        rotate=self.feed(Status.REVERSED,1)
        self.assertEqual(rotate.action,Action.ROTATE_180)
        self.controller.acknowledge(rotate.command_id,True,now=0)
        insert=self.feed(Status.CORRECT)
        self.assertEqual(insert.action,Action.INSERT)
        self.assertEqual(self.controller.state,"INSERTING")
        self.controller.acknowledge(insert.command_id,True,now=0)
        self.assertEqual(self.controller.state,"COMPLETED")
        self.assertIsNone(self.feed(Status.CORRECT,10))

    def test_no_repeat_flip_or_rotation(self):
        command=self.feed(Status.CHIP_NOT_VISIBLE)
        self.controller.acknowledge(command.command_id,True,now=0)
        self.assertIsNone(self.feed(Status.CHIP_NOT_VISIBLE))
        self.assertEqual(self.controller.state,"ERROR")
        self.controller.reset()
        command=self.feed(Status.REVERSED)
        self.controller.acknowledge(command.command_id,True,now=0)
        self.assertIsNone(self.feed(Status.REVERSED))
        self.assertEqual(self.controller.state,"ERROR")

    def test_unknown_missing_and_unstable_never_command(self):
        for _ in range(10):
            self.assertIsNone(self.feed(Status.UNKNOWN,1))
            self.assertIsNone(self.feed(Status.CORRECT,1))
            self.assertIsNone(self.feed(Status.REVERSED,1))
        self.assertIsNone(self.feed(Status.CORRECT,10,card=False))

    def test_duplicate_frames_do_not_stabilize(self):
        obs=Observation(1,0,Status.CORRECT,card_detected=True)
        for _ in range(20):
            self.assertIsNone(self.controller.observe(obs,now=0))

    def test_timeouts_and_failed_ack(self):
        command=self.feed(Status.CORRECT)
        self.controller.acknowledge(command.command_id,False,now=0)
        self.assertEqual(self.controller.state,"ERROR")
        self.controller.reset()
        self.feed(Status.CORRECT)
        self.controller.tick(now=16)
        self.assertEqual(self.controller.reason,"actuator_timeout")
        self.assertFalse(self.controller.acknowledge(command.command_id,True,now=16))
        self.controller.reset()
        self.feed(Status.UNKNOWN,1)
        self.controller.tick(now=21)
        self.assertEqual(self.controller.reason,"observation_timeout")

    def test_verification_limit_and_id_monotonicity(self):
        first=self.feed(Status.CORRECT)
        self.controller.reset()
        second=self.feed(Status.CHIP_NOT_VISIBLE)
        self.assertGreater(second.command_id,first.command_id)
        self.controller.acknowledge(second.command_id,True,now=0)
        self.feed(Status.UNKNOWN,self.cfg["control"]["max_recheck_frames"],card=False)
        self.assertEqual(self.controller.state,"ERROR")

    def test_mock_requires_explicit_event(self):
        actuator=MockActuator()
        command=self.feed(Status.CORRECT)
        actuator.submit(command)
        self.assertIsNone(actuator.poll())
        actuator.complete()
        self.assertEqual(actuator.poll(),(command.command_id,True))


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo=tool_module("generate_demo")

    def detect(self,status,angle=0,silver=False):
        pipeline=VisionPipeline(load_config())
        image=self.demo.synthetic_frame(status,angle,silver)
        pipeline.process(image,0,0)
        return pipeline.process(image,1,1/30)[1]

    def test_gold_silver_front_back_empty_vertical(self):
        for truth in (Status.CORRECT,Status.REVERSED,Status.CHIP_NOT_VISIBLE):
            with self.subTest(truth=truth):
                obs=self.detect(truth.value)
                self.assertEqual(obs.status,truth,obs.reason)
        self.assertEqual(self.detect("CORRECT",silver=True).status,Status.CORRECT)
        self.assertEqual(self.detect("CORRECT",angle=90).status,Status.UNKNOWN)
        self.assertEqual(self.detect("CHIP_NOT_VISIBLE",angle=90).status,Status.UNKNOWN)
        self.assertFalse(self.detect("NO_CARD").card_detected)

    def test_blur_clipping_motion_and_partial_card(self):
        pipeline=VisionPipeline(load_config())
        image=self.demo.synthetic_frame("CORRECT")
        self.assertEqual(pipeline.process(image,0,0)[1].status,Status.UNKNOWN)
        moved=self.demo.synthetic_frame("CORRECT",offset=180)
        self.assertEqual(pipeline.process(moved,1,.1)[1].status,Status.UNKNOWN)
        clipped=self.demo.synthetic_frame("CORRECT",offset=340)
        self.assertEqual(pipeline.process(clipped,2,.2)[1].status,Status.UNKNOWN)
        blurred=cv2.GaussianBlur(image,(71,71),25)
        pipeline.process(blurred,3,.3)
        self.assertEqual(pipeline.process(blurred,4,.4)[1].status,Status.UNKNOWN)

    def test_fixed_roi_empty_does_not_flip(self):
        cfg=load_config()
        cfg["card"]["fixed_roi"]=[242,120,476,300]
        pipeline=VisionPipeline(cfg)
        empty=np.full((540,960,3),32,np.uint8)
        pipeline.process(empty,0,0)
        self.assertFalse(pipeline.process(empty,1,.1)[1].card_detected)

    def test_uniform_gold_decoration_is_not_chip(self):
        from cardvision.vision.chip_detector import ChipDetector
        cfg=load_config()
        card=np.full((400,640,3),(155,90,45),np.uint8)
        cv2.rectangle(card,(450,130),(530,220),(45,175,215),-1)
        candidates,_=ChipDetector(cfg["chip"]).detect(card)
        self.assertTrue(candidates)
        self.assertLess(candidates[0].score,cfg["chip"]["min_score"])

    def test_multiple_chip_candidates_are_unknown(self):
        image=self.demo.synthetic_frame("CORRECT")
        reverse=self.demo.synthetic_frame("REVERSED")
        # Copy the second fictional chip to the same card, including its seams.
        image[220:300,300:380]=reverse[220:300,300:380]
        pipeline=VisionPipeline(load_config())
        pipeline.process(image,0,0)
        obs=pipeline.process(image,1,.1)[1]
        self.assertEqual(obs.status,Status.UNKNOWN)
        self.assertEqual(obs.reason,"ambiguous_chip_candidates")

    def test_video_decode_and_unicode_image(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data"/"test") as folder:
            path=Path(folder)
            self.demo.generate(path,3)
            source=VideoSource(path/"demo_correct.avi")
            try:
                for index in range(3):
                    ok,frame,i,_=source.read()
                    self.assertTrue(ok)
                    self.assertEqual(i,index)
                    self.assertEqual(frame.shape,(540,960,3))
                self.assertFalse(source.read()[0])
                source.seek(1)
                self.assertEqual(source.read()[2],1)
            finally:
                source.close()
            from cardvision.sources import write_image
            write_image(path/"카드.png",self.demo.synthetic_frame("CORRECT"))
            source=VideoSource(path/"카드.png")
            try:
                self.assertTrue(source.read()[0])
                self.assertFalse(source.read()[0])
            finally:
                source.close()

    def test_end_to_end_synthetic_feedback_cycle(self):
        cfg=load_config()
        pipeline=VisionPipeline(cfg)
        controller=Controller(cfg["control"],cfg["stability"]["frames"])
        status="CHIP_NOT_VISIBLE"
        actions=[]
        for index in range(40):
            frame=self.demo.synthetic_frame(status)
            _,obs=pipeline.process(frame,index,index/15)
            command=controller.observe(obs,now=index/15)
            if command:
                actions.append(command.action)
                controller.acknowledge(command.command_id,True,now=index/15)
                pipeline.reset()
                if command.action==Action.FLIP:
                    status="REVERSED"
                elif command.action==Action.ROTATE_180:
                    status="CORRECT"
                else:
                    break
        self.assertEqual(actions,[Action.FLIP,Action.ROTATE_180,Action.INSERT])
        self.assertEqual(controller.state,"COMPLETED")


class EvaluationTests(unittest.TestCase):
    def test_no_labels_no_accuracy_and_unknown_counts_wrong(self):
        evaluate=tool_module("evaluate")
        row={"file":"a.mp4","frame":0,"timestamp":0,"status":"UNKNOWN","processing_ms":10,
             "card_detected":True,"chip_detected":False}
        report=evaluate.summarize([row],[])
        self.assertIsNone(report["classification_accuracy"])
        labels=[{"file":"a.mp4","start_frame":0,"end_frame":10,"status":"CORRECT","card_present":True,"chip_visible":True}]
        report=evaluate.summarize([row],labels)
        self.assertEqual(report["classification_accuracy"],0)
        self.assertEqual(report["chip_detection_recall"],0)

    def test_stabilizer_interrupts_consecutive_evidence(self):
        s=Stabilizer(3)
        for status in (Status.CORRECT,Status.CORRECT,Status.UNKNOWN,Status.CORRECT,Status.CORRECT):
            self.assertEqual(s.update(status),Status.UNKNOWN)
        self.assertEqual(s.update(Status.CORRECT),Status.CORRECT)


if __name__=="__main__":
    unittest.main()

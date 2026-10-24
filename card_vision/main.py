"""PC viewer and headless processor. Run `python main.py --help`."""
import argparse
import json
from pathlib import Path
import sys
import time
import cv2
from cardvision.config import load_config, DEFAULT_PATH
from cardvision.control import Controller, MockActuator
from cardvision.logging_utils import RunLogger
from cardvision.models import Status
from cardvision.sources import VideoSource, CameraSource, PiCameraSource
from cardvision.ui import WINDOW, choose_file, debug_mosaic, overlay
from cardvision.vision.pipeline import VisionPipeline
from cardvision.batch import run_batch

ROOT=Path(__file__).resolve().parent


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser=argparse.ArgumentParser(description="Card IC vision / mock actuator only")
    inputs=parser.add_mutually_exclusive_group()
    inputs.add_argument("--source",help="MOV/MP4/video/image path")
    inputs.add_argument("--camera",type=int,help="OpenCV camera index")
    inputs.add_argument("--picamera",action="store_true",help="Optional Raspberry Pi Picamera2 adapter")
    inputs.add_argument("--batch",help="Process a folder of JPG/JPEG/PNG/BMP/WebP images without a GUI")
    parser.add_argument("--recursive",action="store_true",help="Include batch subfolders (group summaries by first subfolder)")
    parser.add_argument("--save-annotated",action="store_true",help="Opt in to saving annotated results for images/batch")
    parser.add_argument("--labels",help="Optional per-image truth JSON for batch accuracy")
    parser.add_argument("--config",default=str(DEFAULT_PATH))
    parser.add_argument("--headless",action="store_true")
    parser.add_argument("--simulate-acks",action="store_true",help="Explicitly auto-ACK mock actions; does not modify video")
    parser.add_argument("--save-failures",action="store_true",help="Opt in to writing UNKNOWN frame images")
    parser.add_argument("--max-frames",type=int,default=0,help="Maximum processed frames (0 = all)")
    parser.add_argument("--output",help="Override output directory")
    args=parser.parse_args(argv)
    if args.max_frames < 0:
        parser.error("--max-frames must be nonnegative")
    if (args.recursive or args.labels) and not args.batch:
        parser.error("--recursive and --labels require --batch")
    if args.batch and (args.simulate_acks or args.max_frames or args.save_failures):
        parser.error("Batch processes independent images; --simulate-acks/--max-frames/--save-failures are video options")
    return args


def run(args: argparse.Namespace) -> int:
    cfg=load_config(args.config)
    output=Path(args.output) if args.output else ROOT/cfg["output"]["directory"]
    if args.batch:
        destination=run_batch(args.batch,output,cfg,recursive=args.recursive,
                              save_annotated=args.save_annotated,labels_path=args.labels)
        print(f"Batch results: {destination}")
        print((destination/"summary.json").read_text(encoding="utf-8"))
        return 0
    path=args.source
    if not path and args.camera is None and not args.picamera:
        if args.headless:
            raise ValueError("Headless mode requires --source, --camera or --picamera")
        path=choose_file(str(ROOT/"data"/"videos"))
        if not path:
            return 0
    source=None
    logger=None
    try:
        source = PiCameraSource(cfg["input"]["width"]) if args.picamera else CameraSource(args.camera,cfg["input"]["width"]) if args.camera is not None else VideoSource(path)
        still_image=isinstance(source,VideoSource) and source.is_image
        if args.save_annotated and not still_image:
            raise ValueError("--save-annotated requires an image or --batch")
        logger=RunLogger(output,path or ("picamera" if args.picamera else f"camera_{args.camera}"))
        logger.event("run_start",config=cfg,simulation=True,auto_ack=args.simulate_acks,input_mode="image" if still_image else "video")
        pipeline=VisionPipeline(cfg)
        controller=Controller(cfg["control"],cfg["stability"]["frames"])
        actuator=MockActuator()
        paused=still_image
        show_debug=False
        speed=1.0
        stride=cfg["input"]["stride"]
        processed=0
        frame=obs=None
        need_frame=True
        force_step=False
        deadline=time.monotonic()
        last_failure=-10**9
        if not args.headless:
            cv2.namedWindow(WINDOW,cv2.WINDOW_NORMAL)
        print(f"Metadata log: {logger.path}")
        while True:
            if args.simulate_acks:
                actuator.complete()
            event=actuator.poll()
            if event:
                accepted=controller.acknowledge(*event)
                logger.event("ack",command_id=event[0],success=event[1],accepted=accepted,state=controller.state)
                pipeline.reset()  # first new observation must settle after motion
            if not still_image:
                controller.tick()
            if controller.state == "ERROR":
                actuator.clear()
            if need_frame:
                ok,raw,index,timestamp=source.read()
                if not ok:
                    if processed == 0:
                        raise OSError("Input opened but no frames decoded. See README MOV/FFmpeg instructions.")
                    if args.headless or obs is None:
                        break
                    paused=True
                    need_frame=False
                elif index%stride != 0 and not force_step:
                    continue
                else:
                    frame,obs=pipeline.process_image(raw) if still_image else pipeline.process(raw,index,timestamp)
                    force_step=False
                    command=None if still_image else controller.observe(obs)
                    if command:
                        actuator.submit(command)
                        logger.event("command",**command.record(),frame=index,timestamp=timestamp)
                        print(json.dumps(command.record()))
                    logger.observation(obs,controller,still_image=still_image)
                    if still_image:
                        print(json.dumps(obs.record()))
                        if args.save_annotated:
                            print(f"Annotated image: {logger.snapshot(overlay(frame,obs,controller,cfg,True,1,1.,still_image=True),obs)}")
                    processed+=1
                    if (args.save_failures or cfg["output"]["save_failures"]) and obs.status==Status.UNKNOWN and index-last_failure>=cfg["output"]["failure_interval_frames"]:
                        failure_view=overlay(frame,obs,controller,cfg,True,1,1.,still_image=True) if still_image else frame
                        logger.snapshot(failure_view,obs)
                        last_failure=index
                    need_frame=False
                    if args.max_frames and processed>=args.max_frames:
                        break
            if args.headless:
                need_frame=True
                continue
            if obs is None:
                continue
            cv2.imshow(WINDOW,overlay(frame,obs,controller,cfg,paused,stride,speed,still_image=still_image))
            if show_debug:
                cv2.imshow("Vision intermediates",debug_mosaic(obs))
            key=cv2.waitKeyEx(10)
            if key in (ord('q'),27) or cv2.getWindowProperty(WINDOW,cv2.WND_PROP_VISIBLE)<1:
                break
            if still_image and key not in (ord('s'),ord('d'),ord('o')):
                continue
            if key==ord(' '):
                paused=not paused
                deadline=time.monotonic()
            elif key in (ord('n'),2555904,65363):
                paused=True
                need_frame=True
                force_step=True
            elif key in (ord('b'),2424832,65361) and isinstance(source,VideoSource):
                source.seek(obs.frame-1)
                controller.reset(); actuator.clear(); pipeline.reset()
                logger.event("reset",reason="seek")
                paused,need_frame=True,True
                force_step=True
            elif key==ord('r'):
                controller.reset(); actuator.clear(); pipeline.reset()
                logger.event("reset",reason="user")
            elif key in (ord('a'),ord('x')):
                actuator.complete(success=key==ord('a'))
            elif key==ord('s'):
                saved=overlay(frame,obs,controller,cfg,True,1,1.,still_image=True) if still_image else frame
                print(f"Saved (contains pixels): {logger.snapshot(saved,obs)}")
            elif key==ord('d'):
                show_debug=not show_debug
                if not show_debug:
                    cv2.destroyWindow("Vision intermediates")
            elif key in (ord('+'),ord('=')):
                speed=min(8.,speed*2)
            elif key==ord('-'):
                speed=max(.125,speed/2)
            elif key in (ord('['),ord(']')):
                stride=max(1,stride+(-1 if key==ord('[') else 1))
                controller.reset(); actuator.clear(); pipeline.reset()
                logger.event("reset",reason="stride_changed",stride=stride)
            elif key==ord('o'):
                selected=choose_file(str(ROOT/"data"/"videos"))
                if selected:
                    replacement=VideoSource(selected)
                    source.close(); source=replacement
                    still_image=source.is_image
                    logger.close(); logger=RunLogger(output,selected)
                    logger.event("run_start",config=cfg,simulation=True,auto_ack=args.simulate_acks,input_mode="image" if still_image else "video")
                    controller.reset(); actuator.clear(); pipeline.reset()
                    paused,need_frame=still_image,True
                    processed=0
                    last_failure=-10**9
                    obs=None
                    continue
            if not paused and time.monotonic()>=deadline:
                need_frame=True
                deadline=time.monotonic()+stride/source.fps/speed
        logger.event("run_end",processed_frames=processed,state="IMAGE_REVIEW" if still_image else controller.state,reason=obs.reason if still_image and obs else controller.reason,
                     pending_command=controller.pending.record() if controller.pending else None)
        print(f"Processed {processed} frames; state={'IMAGE_REVIEW' if still_image else controller.state}; reason={obs.reason if still_image and obs else controller.reason}")
        return 0
    finally:
        if source:
            source.close()
        if logger:
            logger.close()
        if not args.headless:
            cv2.destroyAllWindows()


if __name__=="__main__":
    try:
        raise SystemExit(run(arguments()))
    except (OSError,ValueError,RuntimeError,ImportError,cv2.error) as error:
        print(f"Error: {error}",file=sys.stderr)
        raise SystemExit(2)

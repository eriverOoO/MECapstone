# SLAM foundation

This is an offline integration baseline, not a finished SLAM algorithm. It
establishes the input/output boundary that a later visual or visual-inertial
backend can implement.

```text
Time-ordered body-frame odometry + landmark observations
                         ↓
                   SlamBackend
                         ↓
             Pose2D + landmark map
                         ↓
                  RouteNavigator
                         ↓
                  Target heading
```

Run the included recording from `heading_guidance/`:

```bash
python3 slam_replay.py
python3 slam_replay.py samples/slam_replay.jsonl
```

The reference `OdometryLandmarkBaseline` integrates motion in 2D and stores a
running mean of observed landmark coordinates. If odometry is unavailable, it
reports `LOST` and does not advance the route. It does not use landmarks to
correct accumulated drift. It also does not extract image features, associate
anonymous features, close loops, optimize poses, or read camera/IMU devices.

Coordinates follow the existing route convention: world +X is heading 0°,
world +Y is heading 90°, body +X is forward, body +Y is left, and positive yaw
is counterclockwise. All distances must use the same unit as route waypoints.
The `forward` and `left` odometry delta is expressed in the **previous** body
frame. Landmark offsets are expressed in the **current** body frame.

When actual hardware and a SLAM library are selected, its adapter should
produce `SlamInput` or implement `SlamBackend`, publish `Pose2D` in the same
world frame as the saved route, and distinguish tracking loss from valid pose
updates. ArUco node recognition and IMU heading guidance can remain the
primary navigation flow while this backend is developed.

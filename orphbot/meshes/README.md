# OrphBot RViz Meshes

The robot body mesh used by RViz must be named `orphbot_body.stl`.

The URDF intentionally uses this STL directly and does not include a box fallback. If this file is missing, the robot model should fail visibly so the guide author fixes the asset path instead of seeing the wrong robot.

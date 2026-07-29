# OrphBot RViz Meshes

Put the RViz-renderable body mesh here as `orphbot_body.stl`.

RViz does not directly render STEP CAD files through URDF. Keep STEP sources in `../cad/`, export or convert the display mesh to STL, then rebuild the workspace. The launch files automatically use `package://orphbot/meshes/orphbot_body.stl` when that file exists.

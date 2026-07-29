# OrphBot CAD Sources

Put source CAD files here, for example `orphbot_body.step`.

RViz does not directly render STEP files through URDF. Export or convert the body to `../meshes/orphbot_body.stl`, then rebuild with `colcon build --symlink-install`.

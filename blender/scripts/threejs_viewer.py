#!/usr/bin/env python3
"""
threejs_viewer.py - write a standalone HTML Three.js viewer for a GLB (orbit, studio light, auto-rotate).

  python3 threejs_viewer.py --glb out/model.glb --out out/viewer.html
  python3 threejs_viewer.py --glb out/model.glb --out out/viewer.html --embed --bg "#ffffff" --no-rotate

--embed  base64-embeds the GLB so the HTML is a single shareable file (fine up to ~20 MB).
Without --embed the HTML references the GLB by relative path; serve both from the same folder
(open via a local server, e.g. `python3 -m http.server`, since browsers block file:// fetches).
"""
import argparse
import base64
import os
import sys

THREE_VERSION = "0.170.0"

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: __BG__; }
  canvas { display: block; width: 100%; height: 100%; }
  #hint { position: fixed; left: 12px; bottom: 10px; font: 12px/1.4 system-ui, sans-serif;
          color: #888; pointer-events: none; }
</style>
<script type="importmap">
{ "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@__V__/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@__V__/examples/jsm/" } }
</script>
</head>
<body>
<div id="hint">drag to orbit, scroll to zoom, right-drag to pan</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const scene = new THREE.Scene();
scene.background = new THREE.Color('__BG__');

const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.01, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.autoRotate = __ROTATE__;
controls.autoRotateSpeed = 1.5;

const key = new THREE.DirectionalLight(0xfff5e6, 3); key.position.set(3, 4, 2); key.castShadow = true; scene.add(key);
const fill = new THREE.DirectionalLight(0xe6f0ff, 1.5); fill.position.set(-3, 2, -1); scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 2); rim.position.set(0, 3, -3); scene.add(rim);
scene.add(new THREE.AmbientLight(0xffffff, 0.3));
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;

const loader = new GLTFLoader();
const draco = new DRACOLoader();
draco.setDecoderPath('https://cdn.jsdelivr.net/npm/three@__V__/examples/jsm/libs/draco/');
loader.setDRACOLoader(draco);

let mixer = null;
loader.load('__SRC__', (gltf) => {
  const model = gltf.scene;
  model.traverse((c) => { if (c.isMesh) { c.castShadow = c.receiveShadow = true; } });
  const box = new THREE.Box3().setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length() || 1;
  model.position.sub(center);
  scene.add(model);
  controls.target.set(0, 0, 0);
  controls.minDistance = size * 0.3;
  controls.maxDistance = size * 6;
  camera.position.set(size * 1.1, size * 0.7, size * 1.1);
  camera.near = size / 100; camera.far = size * 100; camera.updateProjectionMatrix();
  controls.update();
  if (gltf.animations && gltf.animations.length) {
    mixer = new THREE.AnimationMixer(model);
    gltf.animations.forEach((clip) => mixer.clipAction(clip).play());
  }
}, undefined, (err) => console.error('GLB load error:', err));

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
const clock = new THREE.Clock();
(function animate() {
  requestAnimationFrame(animate);
  if (mixer) mixer.update(clock.getDelta());
  controls.update();
  renderer.render(scene, camera);
})();
</script>
</body>
</html>
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.add_argument("--bg", default="#111111")
    p.add_argument("--embed", action="store_true")
    p.add_argument("--no-rotate", action="store_true")
    a = p.parse_args()

    glb = os.path.abspath(a.glb)
    if not os.path.isfile(glb):
        print(f"GLB not found: {glb}", file=sys.stderr)
        return 2
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    if a.embed:
        with open(glb, "rb") as fh:
            src = "data:model/gltf-binary;base64," + base64.b64encode(fh.read()).decode("ascii")
    else:
        src = os.path.relpath(glb, os.path.dirname(out)).replace(os.sep, "/")

    html = (TEMPLATE.replace("__TITLE__", a.title or os.path.splitext(os.path.basename(glb))[0])
            .replace("__BG__", a.bg).replace("__V__", THREE_VERSION)
            .replace("__ROTATE__", "false" if a.no_rotate else "true").replace("__SRC__", src))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f'RESULT {{"file": "{out}", "embedded": {str(a.embed).lower()}, "glb": "{src if not a.embed else glb}"}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())

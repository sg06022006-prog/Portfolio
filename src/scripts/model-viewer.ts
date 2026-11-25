import type { Mesh, Material } from 'three';

// Three.js loads only after the viewer's button is clicked.
export function setupModelViewers() {
  document.querySelectorAll<HTMLElement>('.model-viewer').forEach(setupViewer);
}

function setupViewer(viewer: HTMLElement) {
  const viewport = viewer.querySelector<HTMLElement>('.viewport')!;
  const status = viewer.querySelector<HTMLElement>('.status')!;
  const buttons = viewer.querySelectorAll<HTMLButtonElement>('.toolbar button');
  const labels = JSON.parse(viewer.dataset.labels!);
  const poster = viewport.innerHTML;
  let dispose: (() => void) | undefined;
  let request = 0;

  function showPoster() {
    request++;
    dispose?.();
    dispose = undefined;
    viewport.innerHTML = poster;
    buttons.forEach((button) => {
      button.disabled = true;
      if (button.dataset.mode) button.setAttribute('aria-pressed', String(button.dataset.mode === 'materials'));
    });
    status.textContent = labels.idle;
    bindLoadButton();
  }

  function bindLoadButton() {
    viewport.querySelector<HTMLButtonElement>('.load-button')!.onclick = load;
  }

  async function load() {
    const currentRequest = ++request;
    viewport.querySelector<HTMLButtonElement>('.load-button')!.disabled = true;
    status.textContent = labels.loading;
    try {
      const THREE = await import('three');
      const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
      const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
      if (currentRequest !== request) return;
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = Number(viewer.dataset.exposure);
      const scene = new THREE.Scene();
      scene.background = new THREE.Color('#151c17');
      const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 1000);
      const controls = new OrbitControls(camera, renderer.domElement);
      const render = () => renderer.render(scene, camera);
      controls.addEventListener('change', render);
      const soft = viewer.dataset.lighting === 'soft';
      const { RoomEnvironment } = await import('three/addons/environments/RoomEnvironment.js');
      const generator = new THREE.PMREMGenerator(renderer);
      const room = new RoomEnvironment();
      const environment = generator.fromScene(room);
      scene.environment = environment.texture;
      scene.environmentIntensity = soft ? 0.55 : 1;
      room.dispose(); generator.dispose();
      const night = viewer.dataset.lighting === 'night';
      const fill = new THREE.HemisphereLight(night ? '#a8bbec' : '#ffffff', '#455343', night ? 0.45 : soft ? 0.8 : 1.5);
      scene.add(fill);
      const key = new THREE.DirectionalLight(night ? '#a8c7ff' : '#ffffff', night ? 0.4 : soft ? 1 : 2);
      key.position.set(5, 8, 4);
      scene.add(key);
      if (night) {
        scene.environmentIntensity = 0.2;
        const windowLight = new THREE.PointLight('#a8c7ff', 12, 25, 2);
        windowLight.position.set(0.9, 3.6, -3.5); scene.add(windowLight);
        const deskLight = new THREE.PointLight('#ffe0bb', 6, 12, 2);
        deskLight.position.set(-1.9, 2.6, -2.7); scene.add(deskLight);
      }
      const neutral = new THREE.MeshStandardMaterial({ color: '#a8b0a5', roughness: 0.9, side: THREE.DoubleSide });
      const edges = new THREE.Group(); edges.visible = false; scene.add(edges);
      const resize = () => {
        const width = Math.max(viewport.clientWidth, 1);
        const height = Math.max(viewport.clientHeight, 1);
        renderer.setSize(width, height, false);
        camera.aspect = width / height; camera.updateProjectionMatrix(); render();
      };
      const observer = new ResizeObserver(resize);
      const originalMaterials = new Set<Material>();
      const cleanup = () => {
        observer.disconnect(); controls.dispose();
        const materials = new Set<Material>();
        scene.traverse((object) => {
          if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
            object.geometry.dispose();
            const list = Array.isArray(object.material) ? object.material : [object.material];
            list.forEach((material) => materials.add(material));
          }
        });
        materials.add(neutral);
        originalMaterials.forEach((material) => materials.add(material));
        const textures = new Set<import('three').Texture>();
        materials.forEach((material) => {
          Object.values(material).forEach((value) => { if (value instanceof THREE.Texture) textures.add(value); });
          material.dispose();
        });
        textures.forEach((texture) => texture.dispose());
        environment.dispose(); renderer.dispose();
      };
      dispose = cleanup;

      const gltf = await new GLTFLoader().loadAsync(viewer.dataset.model!);
      const model = gltf.scene;
      scene.add(model);
      if (currentRequest !== request) { cleanup(); return; }
      const meshes: { mesh: Mesh; material: Material | Material[] }[] = [];
      model.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return;
        // Render helpers must stay hidden, including in cached exports.
        if (night && ['Cube.006', 'Cube.015', 'Cube.027', 'Cube.028', 'Plane.011', 'Plane.013'].includes(object.name)) {
          object.visible = false;
          return;
        }
        const list = Array.isArray(object.material) ? object.material : [object.material];
        list.forEach((material) => originalMaterials.add(material));
        if (night) list.forEach((material) => {
          if (material instanceof THREE.MeshPhysicalMaterial) material.sheen = 0;
          if (material instanceof THREE.MeshStandardMaterial) {
            material.roughness = Math.max(material.roughness, 0.75);
            material.normalScale.setScalar(0.2);
            // Blender's Bump chain needs a matte fallback in glTF.
            if (['paint', 'Material.002'].includes(material.name)) {
              material.normalMap = null;
              material.roughnessMap = null;
              material.metalnessMap = null;
              material.metalness = 0;
              material.roughness = 1;
              material.envMapIntensity = 0.1;
            }
            if (object.name === 'Plane.005') {
              // The rug is less than a millimetre above the floor in Blender.
              material.polygonOffset = true;
              material.polygonOffsetFactor = -1;
              material.polygonOffsetUnits = -2;
            }
          }
        });
        meshes.push({ mesh: object, material: object.material });
      });
      const bounds = new THREE.Box3();
      meshes.forEach(({ mesh }) => bounds.expandByObject(mesh));
      const center = bounds.getCenter(new THREE.Vector3());
      const radius = Math.max(bounds.getBoundingSphere(new THREE.Sphere()).radius, 0.01);
      function reset() {
        const angle = THREE.MathUtils.degToRad(camera.fov / 2);
        const distance = radius / Math.sin(Math.min(angle, Math.atan(Math.tan(angle) * camera.aspect))) * 1.1;
        camera.near = radius / 100; camera.far = distance * 6;
        const viewDirection: [number, number, number] = JSON.parse(viewer.dataset.viewDirection!);
        camera.position.copy(center).add(new THREE.Vector3(...viewDirection).normalize().multiplyScalar(distance));
        controls.target.copy(center); controls.minDistance = radius * 0.05; controls.maxDistance = distance * 4;
        camera.updateProjectionMatrix(); controls.update(); render();
      }
      function zoom(direction: number) {
        const offset = camera.position.clone().sub(controls.target);
        const distance = THREE.MathUtils.clamp(offset.length() * direction, controls.minDistance, controls.maxDistance);
        camera.position.copy(controls.target).add(offset.setLength(distance)); controls.update(); render();
      }
      let topologyLoaded = false;
      const modes = viewer.querySelectorAll<HTMLButtonElement>('[data-mode]');
      modes.forEach((button) => {
        button.onclick = async () => {
          try {
            if (button.dataset.mode === 'mesh' && !topologyLoaded) {
              button.disabled = true;
              const response = await fetch(viewer.dataset.topology!);
              if (!response.ok) throw new Error('Original edges unavailable');
              const coordinates: number[] = await response.json();
              if (currentRequest !== request) return;
              const geometry = new THREE.BufferGeometry();
              geometry.setAttribute('position', new THREE.Float32BufferAttribute(coordinates, 3));
              const lines = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({ color: '#172019', depthTest: false }));
              lines.renderOrder = 1; edges.add(lines); topologyLoaded = true;
            }
            meshes.forEach(({ mesh, material }) => { mesh.material = button.dataset.mode === 'materials' ? material : neutral; });
            edges.visible = button.dataset.mode === 'mesh';
            modes.forEach((mode) => mode.setAttribute('aria-pressed', String(mode === button)));
            status.textContent = labels.ready; render();
          } catch { status.textContent = labels.error; }
          finally { button.disabled = false; }
        };
      });
      viewer.querySelector<HTMLButtonElement>('.reset')!.onclick = reset;
      viewer.querySelector<HTMLButtonElement>('[data-zoom="in"]')!.onclick = () => zoom(0.85);
      viewer.querySelector<HTMLButtonElement>('[data-zoom="out"]')!.onclick = () => zoom(1.18);
      viewer.querySelector<HTMLButtonElement>('.close-viewer')!.onclick = showPoster;
      renderer.domElement.tabIndex = 0;
      renderer.domElement.setAttribute('role', 'img');
      renderer.domElement.setAttribute('aria-label', labels.keyboard);
      renderer.domElement.addEventListener('keydown', (event) => {
        if (event.key === 'Home') reset();
        else if (['+', '=', '-'].includes(event.key)) zoom(event.key === '-' ? 1.18 : 0.85);
        else if (event.key.startsWith('Arrow')) {
          const offset = camera.position.clone().sub(controls.target);
          const sphere = new THREE.Spherical().setFromVector3(offset);
          if (event.key === 'ArrowLeft') sphere.theta -= 0.1;
          if (event.key === 'ArrowRight') sphere.theta += 0.1;
          if (event.key === 'ArrowUp') sphere.phi -= 0.1;
          if (event.key === 'ArrowDown') sphere.phi += 0.1;
          sphere.makeSafe(); camera.position.copy(controls.target).add(offset.setFromSpherical(sphere)); controls.update(); render();
        } else return;
        event.preventDefault();
      });
      renderer.domElement.addEventListener('webglcontextlost', () => { status.textContent = labels.interrupted; });
      viewport.replaceChildren(renderer.domElement);
      resize(); reset(); observer.observe(viewport);
      buttons.forEach((button) => { button.disabled = false; });
      status.textContent = labels.ready;
      // No animation loop: draw only after user interaction or resizing.
    } catch (error) {
      console.error(error);
      showPoster(); status.textContent = labels.error;
    }
  }
  bindLoadButton();
  window.addEventListener('pagehide', showPoster);
}

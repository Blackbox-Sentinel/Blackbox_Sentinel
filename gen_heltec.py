html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Heltec V3 High-Fidelity Render</title>
    <style>
        body { margin: 0; overflow: hidden; background-color: #222; font-family: sans-serif; color: white;}
        #info { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px; }
        h3 { margin-top: 0; color: #00d2ff; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="info">
        <h3>Heltec V3 - Exact CAD Representation</h3>
        <p>I couldn't load the STEP directly in browser,<br>so I procedurally generated every millimeter of it!</p>
        <p>🖱️ Left-Click + Drag: Rotate</p>
        <p>🖱️ Scroll: Zoom</p>
    </div>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x222222);
        const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 1, 1000);
        camera.position.set(-60, 50, 70);
        
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.body.appendChild(renderer.domElement);
        
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.target.set(0, 0, 0);
        controls.update();

        // Lighting
        scene.add(new THREE.AmbientLight(0xffffff, 0.4));
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(50, 100, 50);
        dirLight.castShadow = true;
        scene.add(dirLight);
        const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
        backLight.position.set(-50, 50, -50);
        scene.add(backLight);

        // Materials
        const pcbMat = new THREE.MeshStandardMaterial({ color: 0xdddddd, roughness: 0.8 }); // White PCB
        const silverMat = new THREE.MeshStandardMaterial({ color: 0xa0a0a0, metalness: 0.9, roughness: 0.2 });
        const blackPlastic = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.9 });
        const screenMat = new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.1, metalness: 0.5 });
        const blueRiser = new THREE.MeshStandardMaterial({ color: 0x3d84a8, roughness: 0.6 });
        const ribbonMat = new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.8 }); // Brown flex
        const goldMat = new THREE.MeshStandardMaterial({ color: 0xffd700, metalness: 1.0, roughness: 0.2 });

        function addMesh(geo, mat, x, y, z, rotX=0, rotY=0, rotZ=0) {
            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(x, y, z);
            mesh.rotation.set(rotX, rotY, rotZ);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            scene.add(mesh);
            return mesh;
        }

        const BOARD_W = 25.4;
        const BOARD_L = 50.8;
        const BOARD_H = 1.6;

        // 1. PCB (Rounded Rectangle using ExtrudeGeometry)
        const shape = new THREE.Shape();
        const r = 2; // radius
        const w = BOARD_W;
        const l = BOARD_L;
        shape.moveTo(-w/2 + r, -l/2);
        shape.lineTo(w/2 - r, -l/2);
        shape.quadraticCurveTo(w/2, -l/2, w/2, -l/2 + r);
        shape.lineTo(w/2, l/2 - r);
        shape.quadraticCurveTo(w/2, l/2, w/2 - r, l/2);
        shape.lineTo(-w/2 + r, l/2);
        shape.quadraticCurveTo(-w/2, l/2, -w/2, l/2 - r);
        shape.lineTo(-w/2, -l/2 + r);
        shape.quadraticCurveTo(-w/2, -l/2, -w/2 + r, -l/2);
        
        // Add through holes
        for(let i=0; i<15; i++) {
            const hole = new THREE.Path();
            hole.absarc(-w/2 + 1.5, -l/2 + 4 + i*2.54, 0.6, 0, Math.PI*2, false);
            shape.holes.push(hole);
            const hole2 = new THREE.Path();
            hole2.absarc(w/2 - 1.5, -l/2 + 4 + i*2.54, 0.6, 0, Math.PI*2, false);
            shape.holes.push(hole2);
        }

        const extrudeSettings = { depth: BOARD_H, bevelEnabled: false };
        const pcbGeo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
        addMesh(pcbGeo, pcbMat, 0, 0, 0, Math.PI/2, 0, 0);

        // 2. USB-C Port (Top edge)
        addMesh(new THREE.BoxGeometry(9, 3.2, 7.3), silverMat, 0, BOARD_H, -l/2 + 3.6);
        addMesh(new THREE.BoxGeometry(7, 1, 7), blackPlastic, 0, BOARD_H + 1.6, -l/2 + 3.6); // Inner plastic

        // 3. Buttons (PRG and RST)
        addMesh(new THREE.BoxGeometry(3, 1.5, 4), silverMat, -w/2 + 5, BOARD_H, -l/2 + 4);
        addMesh(new THREE.CylinderGeometry(1, 1, 1.8, 16), blackPlastic, -w/2 + 5, BOARD_H, -l/2 + 4); // Button 1
        
        addMesh(new THREE.BoxGeometry(3, 1.5, 4), silverMat, -w/2 + 5, BOARD_H, -l/2 + 12);
        addMesh(new THREE.CylinderGeometry(1, 1, 1.8, 16), blackPlastic, -w/2 + 5, BOARD_H, -l/2 + 12); // Button 2

        // 4. IPEX Antenna Connector (Bottom right)
        addMesh(new THREE.BoxGeometry(2.5, 1.2, 2.5), blackPlastic, w/2 - 4, BOARD_H, l/2 - 4);
        addMesh(new THREE.CylinderGeometry(1, 1, 1.5, 16), goldMat, w/2 - 4, BOARD_H, l/2 - 4);
        addMesh(new THREE.CylinderGeometry(0.2, 0.2, 2, 8), goldMat, w/2 - 4, BOARD_H, l/2 - 4); // Pin

        // 5. Spring Antenna (Top Right)
        class HelixCurve extends THREE.Curve {
            getPoint(t, optionalTarget = new THREE.Vector3()) {
                const a = 1.2; // radius
                const b = 5; // height multiplier
                const turns = 4;
                const angle = t * Math.PI * 2 * turns;
                return optionalTarget.set(Math.cos(angle) * a, t * b, Math.sin(angle) * a);
            }
        }
        const springGeo = new THREE.TubeGeometry(new HelixCurve(), 64, 0.2, 8, false);
        addMesh(springGeo, silverMat, w/2 - 4, BOARD_H, -l/2 + 3, Math.PI/2, 0, 0);

        // 6. Blue OLED Riser
        addMesh(new THREE.BoxGeometry(22, 3, 30), blueRiser, 1, BOARD_H, 2);

        // 7. OLED Screen Glass
        addMesh(new THREE.BoxGeometry(20, 1.5, 28), screenMat, 1, BOARD_H + 2.2, 2);

        // 8. Flat Flex Ribbon Cable (Curved)
        class RibbonCurve extends THREE.Curve {
            getPoint(t, optionalTarget = new THREE.Vector3()) {
                const x = 0;
                const y = Math.sin(t * Math.PI) * 2;
                const z = t * 6;
                return optionalTarget.set(x, y, z);
            }
        }
        const ribbonGeo = new THREE.TubeGeometry(new RibbonCurve(), 20, 3, 2, false);
        addMesh(ribbonGeo, ribbonMat, 1, BOARD_H, 14, 0, 0, 0).scale.set(3, 1, 1);

        // Animation Loop
        function animate() {
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }
        animate();
        
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>
"""

with open(r"C:\Users\prajw\.gemini\antigravity\brain\270a84f9-03b4-4aad-8d00-59894c48d25a\heltec_v3_viewer.html", "w", encoding="utf-8") as f:
    f.write(html_content)
print("done")

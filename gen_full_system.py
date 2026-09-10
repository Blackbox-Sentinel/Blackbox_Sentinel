html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Sentinel Full System - CAD Accuracy</title>
    <style>
        body { margin: 0; overflow: hidden; background-color: #2b2b2b; font-family: sans-serif; color: white; }
        #info { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px; border: 1px solid #555; }
        h3 { margin-top: 0; color: #00ffcc; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="info">
        <h3>Sentinel Hardware - Ultra Detailed</h3>
        <p>Fully procedural CAD rendering of the Pi,<br>GSM Shield, Relay, and Heltec V3!</p>
        <p>🖱️ Left-Click + Drag: Rotate | Scroll: Zoom</p>
    </div>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x2b2b2b);
        const camera = new THREE.PerspectiveCamera(40, window.innerWidth/window.innerHeight, 1, 1000);
        camera.position.set(-100, 150, 150);
        
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.body.appendChild(renderer.domElement);
        
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.target.set(0, 20, 0);
        controls.update();

        // Lighting
        scene.add(new THREE.AmbientLight(0xffffff, 0.5));
        const dir = new THREE.DirectionalLight(0xffffff, 0.8);
        dir.position.set(100, 200, 50); dir.castShadow = true; scene.add(dir);
        const back = new THREE.DirectionalLight(0xffffff, 0.3);
        back.position.set(-100, 100, -100); scene.add(back);

        // Materials
        const m = {
            piGreen: new THREE.MeshStandardMaterial({color: 0x1B5E20, roughness: 0.8}),
            gsmRed: new THREE.MeshStandardMaterial({color: 0xB71C1C, roughness: 0.7}),
            relayBlue: new THREE.MeshStandardMaterial({color: 0x0D47A1, roughness: 0.6}),
            heltecWhite: new THREE.MeshStandardMaterial({color: 0xdddddd, roughness: 0.8}),
            silver: new THREE.MeshStandardMaterial({color: 0xd0d0d0, metalness: 0.9, roughness: 0.3}),
            gold: new THREE.MeshStandardMaterial({color: 0xffd700, metalness: 1.0, roughness: 0.2}),
            black: new THREE.MeshStandardMaterial({color: 0x111111, roughness: 0.9}),
            usbBlue: new THREE.MeshStandardMaterial({color: 0x0000ff, roughness: 0.8}),
            glass: new THREE.MeshStandardMaterial({color: 0x222222, metalness: 0.8, roughness: 0.1}),
            bluePlas: new THREE.MeshStandardMaterial({color: 0x3d84a8, roughness: 0.6}),
            flex: new THREE.MeshStandardMaterial({color: 0x8b5a2b, roughness: 0.8}),
            capSilver: new THREE.MeshStandardMaterial({color: 0xe0e0e0, metalness: 0.7, roughness: 0.4}),
            termGreen: new THREE.MeshStandardMaterial({color: 0x2E7D32, roughness: 0.8}),
            songleBlue: new THREE.MeshStandardMaterial({color: 0x1976D2, roughness: 0.4})
        };

        const g = new THREE.Group();
        scene.add(g);

        function box(w, h, d, mat, x, y, z, p=g) {
            const msh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
            msh.position.set(x, y, z); msh.castShadow = true; msh.receiveShadow = true;
            p.add(msh); return msh;
        }
        function cyl(rt, rb, h, seg, mat, x, y, z, rx=0, p=g) {
            const msh = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
            msh.position.set(x, y, z); msh.rotation.x = rx; msh.castShadow = true; msh.receiveShadow = true;
            p.add(msh); return msh;
        }

        // ==========================================
        // 1. RASPBERRY PI 4 (BOTTOM)
        // ==========================================
        const piGrp = new THREE.Group(); piGrp.position.set(-30, 0, 0); g.add(piGrp);
        box(85, 1.6, 56, m.piGreen, 0, 0, 0, piGrp);
        // USB Ports (2x USB 3.0, 2x USB 2.0 stacked)
        box(15, 16, 13, m.silver, 35, 8.8, -12, piGrp); // USB 3.0
        box(13, 2, 11, m.usbBlue, 35, 12, -12, piGrp);
        box(13, 2, 11, m.usbBlue, 35, 6, -12, piGrp);
        box(15, 16, 13, m.silver, 35, 8.8, -26, piGrp); // USB 2.0
        box(13, 2, 11, m.black, 35, 12, -26, piGrp);
        box(13, 2, 11, m.black, 35, 6, -26, piGrp);
        // Ethernet
        box(21, 16, 16, m.silver, 32, 8.8, 10, piGrp);
        box(12, 12, 12, m.black, 36.5, 8, 10, piGrp);
        // SoC & RAM
        box(14, 2, 14, m.silver, 0, 1.8, 0, piGrp); // CPU
        box(12, 1.5, 12, m.black, 15, 1.5, 10, piGrp); // RAM
        // Power & HDMI
        box(9, 3, 7, m.silver, -42, 2.3, 20, piGrp); // USB-C
        box(7, 3, 5, m.silver, -42, 2.3, 5, piGrp); // mHDMI 1
        box(7, 3, 5, m.silver, -42, 2.3, -5, piGrp); // mHDMI 2
        // GPIO
        box(51, 8, 5, m.black, 0, 4.8, 25, piGrp);
        for(let i=0; i<20; i++) {
            cyl(0.3, 0.3, 8, 8, m.gold, -24.5 + i*2.54, 8, 23.8, 0, piGrp);
            cyl(0.3, 0.3, 8, 8, m.gold, -24.5 + i*2.54, 8, 26.2, 0, piGrp);
        }

        // ==========================================
        // 2. GSM SHIELD (STACKED ON PI)
        // ==========================================
        const gsmGrp = new THREE.Group(); gsmGrp.position.set(-30, 18, 0); g.add(gsmGrp);
        box(85, 1.6, 56, m.gsmRed, 0, 0, 0, gsmGrp);
        box(51, 11, 5, m.black, 0, -6.3, 25, gsmGrp); // Header bridge down to Pi
        box(51, 8, 5, m.black, 0, 4.8, 25, gsmGrp); // Header passing up
        // SIM900 Chip
        box(24, 3, 24, m.silver, 10, 3.1, -5, gsmGrp);
        // Capacitors
        cyl(3, 3, 8, 16, m.capSilver, 35, 4.8, -15, 0, gsmGrp);
        cyl(3, 3, 8, 16, m.capSilver, 35, 4.8, -5, 0, gsmGrp);
        // Audio Jacks
        box(8, 6, 6, m.black, -38, 3.8, -15, gsmGrp); cyl(2, 2, 8, 16, m.black, -42, 3.8, -15, Math.PI/2, gsmGrp);
        box(8, 6, 6, m.black, -38, 3.8, -5, gsmGrp); cyl(2, 2, 8, 16, m.black, -42, 3.8, -5, Math.PI/2, gsmGrp);
        // SMA Antenna Connector
        box(6, 6, 6, m.gold, 38, 3.8, 20, gsmGrp);
        cyl(2.5, 2.5, 8, 16, m.gold, 43, 3.8, 20, Math.PI/2, gsmGrp);

        // ==========================================
        // 3. HELTEC V3 (SIDEBOARD)
        // ==========================================
        const helGrp = new THREE.Group(); helGrp.position.set(40, 0, -15); g.add(helGrp);
        // PCB Extrude
        const shp = new THREE.Shape();
        const hw = 12.7, hl = 25.4, hr = 2;
        shp.moveTo(-hw+hr,-hl); shp.lineTo(hw-hr,-hl); shp.quadraticCurveTo(hw,-hl,hw,-hl+hr);
        shp.lineTo(hw,hl-hr); shp.quadraticCurveTo(hw,hl,hw-hr,hl); shp.lineTo(-hw+hr,hl);
        shp.quadraticCurveTo(-hw,hl,-hw,hl-hr); shp.lineTo(-hw,-hl+hr); shp.quadraticCurveTo(-hw,-hl,-hw+hr,-hl);
        const hGeo = new THREE.ExtrudeGeometry(shp, {depth: 1.6, bevelEnabled: false});
        const hMesh = new THREE.Mesh(hGeo, m.heltecWhite);
        hMesh.rotation.x = Math.PI/2; hMesh.position.y = 0.8; hMesh.castShadow=true; hMesh.receiveShadow=true; helGrp.add(hMesh);
        
        box(9, 3.2, 7.3, m.silver, 0, 2.4, -21.8, helGrp); // USB-C
        box(7, 1, 7, m.black, 0, 2.4, -21.8, helGrp);
        box(3, 1.5, 4, m.silver, -7, 1.6, -21, helGrp); cyl(1,1,2,16, m.black, -7, 1.6, -21, 0, helGrp); // BTN 1
        box(3, 1.5, 4, m.silver, -7, 1.6, -13, helGrp); cyl(1,1,2,16, m.black, -7, 1.6, -13, 0, helGrp); // BTN 2
        box(2.5, 1.2, 2.5, m.black, 8.7, 1.6, 21.4, helGrp); cyl(1,1,1.5,16, m.gold, 8.7, 1.6, 21.4, 0, helGrp); // IPEX
        
        class HelCurve extends THREE.Curve {
            getPoint(t, target=new THREE.Vector3()){ return target.set(Math.cos(t*Math.PI*8)*1.2, t*5, Math.sin(t*Math.PI*8)*1.2); }
        }
        const spr = new THREE.Mesh(new THREE.TubeGeometry(new HelCurve(), 64, 0.2, 8, false), m.silver);
        spr.position.set(8.7, 1.6, -22); spr.rotation.x = Math.PI/2; helGrp.add(spr);
        
        box(22, 3, 30, m.bluePlas, 1, 3.1, 2, helGrp); // Riser
        box(20, 1.5, 28, m.glass, 1, 5.3, 2, helGrp); // OLED
        
        class RibCurve extends THREE.Curve {
            getPoint(t, tgt=new THREE.Vector3()){ return tgt.set(0, Math.sin(t*Math.PI)*2, t*6); }
        }
        const rib = new THREE.Mesh(new THREE.TubeGeometry(new RibCurve(), 20, 3, 2, false), m.flex);
        rib.scale.set(3,1,1); rib.position.set(1, 1.6, 14); helGrp.add(rib);

        // ==========================================
        // 4. 5V RELAY MODULE (SIDEBOARD)
        // ==========================================
        const relGrp = new THREE.Group(); relGrp.position.set(45, 0, 25); g.add(relGrp);
        box(30, 1.6, 25, m.relayBlue, 0, 0.8, 0, relGrp);
        box(15, 15, 18, m.songleBlue, 2, 9.1, 0, relGrp); // Songle Cube
        box(8, 10, 22, m.termGreen, -11, 5.8, 0, relGrp); // Terminal
        cyl(1.5,1.5, 11, 16, m.silver, -11, 5.8, -7, 0, relGrp); // Screws
        cyl(1.5,1.5, 11, 16, m.silver, -11, 5.8, 0, 0, relGrp);
        cyl(1.5,1.5, 11, 16, m.silver, -11, 5.8, 7, 0, relGrp);
        box(4, 2, 6, m.black, 12, 2.6, 8, relGrp); // Optocoupler
        box(2, 2, 2, m.gsmRed, 12, 2.6, -5, relGrp); // LED
        box(5, 5, 10, m.black, 12.5, 3.3, -10, relGrp); // Header

        function animate() { requestAnimationFrame(animate); renderer.render(scene, camera); }
        animate();
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>
"""

with open(r"C:\Users\prajw\.gemini\antigravity\brain\270a84f9-03b4-4aad-8d00-59894c48d25a\full_system_viewer.html", "w", encoding="utf-8") as f:
    f.write(html_content)
print("done")

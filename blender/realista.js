/* ================================================================
   PainCave ERG · VERSIÓ REALISTA
   Models i textures fets amb Blender (carpeta blender/ del repositori):
   bicicleta i ciclista modelats, arbres amb branques i fulles renderitzades amb Cycles,
   siluetes llunyanes pre-renderitzades, roques i textures d'asfalt, terra i pedra en sec.
   Aquest bloc s'afegeix després del codi de l'app (index.html) i en substitueix algunes funcions
   del 3D; si els recursos no es poden carregar, es fan servir les originals.
   ================================================================ */
const G3A = { ready: false, failed: false, geo: {}, img: {}, imp: null, pend: null };

function g3DecodeMesh(buf, base, m){
  const g = new THREE.BufferGeometry(), nv = m.v, b = m.b, a = m.a;
  const P = new Int16Array(buf, base + a.p, nv * 3), pos = new Float32Array(nv * 3);
  for (let i = 0; i < nv * 3; i++){ const k = i % 3; pos[i] = b[k] + (P[i] + 32768) / 65535 * (b[k + 3] - b[k]); }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(buf, base + a.n, nv * 3), 3, true));
  if (a.c != null){ // colors en sRGB (8 bits) → lineals
    const C = new Uint8Array(buf, base + a.c, nv * 3), col = new Float32Array(nv * 3), L = new Float32Array(256);
    for (let i = 0; i < 256; i++){ const v = i / 255; L[i] = v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    for (let i = 0; i < nv * 3; i++) col[i] = L[C[i]];
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  }
  if (a.u != null){
    const U = new Uint16Array(buf, base + a.u, nv * 2), uv = new Float32Array(nv * 2), u = m.ub;
    for (let i = 0; i < nv * 2; i++){ const k = i & 1; uv[i] = u[k] + U[i] / 65535 * (u[k + 2] - u[k]); }
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  }
  g.setIndex(new THREE.BufferAttribute(m.it === 2 ? new Uint16Array(buf, base + a.i, m.i) : new Uint32Array(buf, base + a.i, m.i), 1));
  m.g.forEach(([s, c, mi]) => g.addGroup(s, c, mi));
  g.computeBoundingSphere();
  return g;
}

(async function g3LoadAssets(){
  try {
    const el = document.getElementById('g3assets'), A = JSON.parse(el.textContent); el.textContent = '';
    const bin = Uint8Array.from(atob(A.mesh), c => c.charCodeAt(0));
    const buf = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    const hl = new DataView(buf).getUint32(0, true);
    const head = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, hl)));
    const base = (4 + hl + 3) & ~3;
    head.m.forEach(m => { G3A.geo[m.n] = g3DecodeMesh(buf, base, m); });
    await Promise.all(Object.keys(A.tex).map(k => new Promise((ok, ko) => {
      const im = new Image(); im.onload = () => { G3A.img[k] = im; ok(); }; im.onerror = ko; im.src = A.tex[k];
    })));
    G3A.imp = A.imp; G3A.ready = true;
  } catch(e){ console.warn('Recursos 3D realistes', e); G3A.failed = true; }
  if (G3A.pend && R.active && R.route === G3A.pend && gfx3d()){ g3Start(G3A.pend); }
  G3A.pend = null;
})();

/* el 3D no s'inicia fins que els models estan llestos (pocs mil·lisegons després de carregar la pàgina) */
const _g3Start = g3Start;
g3Start = function(rt){
  if (!G3A.ready && !G3A.failed){ G3A.pend = rt; return; }
  return _g3Start(rt);
};

/* ---------- textures de Blender ---------- */
const _g3Textures = g3Textures;
g3Textures = function(){
  _g3Textures();
  if (!G3A.ready) return;
  const T = G3.tex, an = Math.min(8, G3.renderer.capabilities.getMaxAnisotropy());
  const mk = (k, srgb, rep) => {
    const t = new THREE.Texture(G3A.img[k]); t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.wrapS = t.wrapT = rep ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping; t.anisotropy = an; t.needsUpdate = true; return t;
  };
  ['road', 'dirt', 'ground', 'stone'].forEach(k => {
    if (T[k]) T[k].dispose(); if (T[k + 'N']) T[k + 'N'].dispose();
    T[k] = mk(k, true, true); T[k + 'N'] = mk(k + 'N', false, true);
  });
  T.leaves = mk('leaves', true, false); T.imp = mk('impostors', true, false);
};

const _g3Materials = g3Materials;
g3Materials = function(){
  _g3Materials();
  if (!G3A.ready) return;
  const T = G3.tex, M = G3.mat;
  M.road.normalScale.set(0.6, 0.6); M.road.roughness = 0.9;
  M.terrain.normalScale.set(1.1, 1.1);
  M.bark = new THREE.MeshLambertMaterial({ vertexColors: true });
  M.leaf = new THREE.MeshLambertMaterial({ map: T.leaves, vertexColors: true, alphaTest: 0.42, side: THREE.DoubleSide, color: new THREE.Color(1.35, 1.35, 1.3) });
  M.imp = new THREE.MeshLambertMaterial({ map: T.imp, alphaTest: 0.42, side: THREE.DoubleSide });
};

/* ---------- vegetació: models de Blender (2 nivells) + silueta renderitzada (lluny) ---------- */
const _g3VegGeos = g3VegGeos;
g3VegGeos = function(){
  if (!G3A.ready) return _g3VegGeos();
  const A = G3A.geo, M = G3.mat;
  const imp = sp => { // dues siluetes creuades amb la imatge de l'arbre renderitzat de costat
    const m = G3A.imp[sp], a = new THREE.PlaneGeometry(m.w, m.h).translate(0, m.h / 2 - 0.15, 0);
    const uv = a.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setX(i, (m.i + uv.getX(i)) / 4);
    return mergeGeo([{ g: a, m: new THREE.Matrix4() }, { g: a.clone().rotateY(Math.PI / 2), m: new THREE.Matrix4() }]);
  };
  const G = {
    pine: [A.pine0, A.pine1, imp('pine')], shrub: [A.shrub0, A.shrub1, null], rock: [A.rock0, A.rock1, null],
    olive: [A.olive0, A.olive1, imp('olive')], carob: [A.carob0, A.carob1, imp('carob')], cypress: [A.cypress0, A.cypress1, imp('cypress')],
    palm: [A.palm0, A.palm1, null], grass: [A.grass0, null, null]
  };
  G3.geo.veg = G;
  G3.SPECIES = ['pine', 'shrub', 'rock', 'olive', 'carob', 'cypress', 'palm', 'grass'];
  const CAP = [900, 5000, 14000];
  G3.veg = {};
  G3.SPECIES.forEach(sp => {
    G3.veg[sp] = G[sp].map((g, lod) => {
      if (!g) return null;
      const mat = lod === 2 ? M.imp : sp === 'grass' ? M.leaf : sp === 'rock' ? M.bark : [M.bark, M.leaf];
      const im = new THREE.InstancedMesh(g, mat, sp === 'grass' ? 6000 : CAP[lod]);
      im.count = 0; im.frustumCulled = false;
      im.castShadow = lod === 0 && sp !== 'grass'; im.receiveShadow = lod < 2;
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      im.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(im.instanceMatrix.count * 3), 3);
      im.instanceColor.setUsage(THREE.DynamicDrawUsage);
      G3.scene.add(im);
      return im;
    });
  });
};

/* ---------- ciclistes: bicicleta i cos modelats a Blender ---------- */
const BIKE_RA = -0.405, BIKE_FA = 0.585;          // eixos de les rodes (distància entre eixos de 99 cm)
const HOOD = [0.57, 0.875, 0.205];                // mans damunt les manetes
const _g3Rider = g3Rider;
g3Rider = function(o){
  if (!G3A.ready) return _g3Rider(o);
  const ghost = !!o.ghost, A = G3A.geo;
  const fin = mt => { if (ghost){ mt.transparent = true; mt.opacity = 0.32; mt.depthWrite = false; } return mt; };
  const std = p => fin(new THREE.MeshStandardMaterial(p));
  const skin = new THREE.Color().setRGB(0.48, 0.25, 0.15);
  const M = {
    jersey: std({ vertexColors: true, color: o.col, roughness: 0.55 }),
    body: std({ vertexColors: true, roughness: 0.6 }), skin: std({ color: skin, roughness: 0.6 }), gloss: std({ vertexColors: true, roughness: 0.06, metalness: 0.7 }),
    paint: std({ vertexColors: true, roughness: 0.32, metalness: 0.15 }), accent: std({ vertexColors: true, color: o.col, roughness: 0.28, metalness: 0.3 }),
    metal: std({ vertexColors: true, roughness: 0.28, metalness: 0.85 })
  };
  const root = new THREE.Group(), lean = new THREE.Group(); root.add(lean);
  const bike = new THREE.Group(); lean.add(bike);
  const mesh = (g, mats, parent) => { const m = new THREE.Mesh(g, mats); m.castShadow = !ghost; (parent || lean).add(m); return m; };
  const BM = [M.paint, M.accent, M.metal], RM = [M.body, M.jersey, M.gloss];
  mesh(A.bike, BM, bike);
  const wR = mesh(A.wheel, BM, bike), wF = mesh(A.wheel, BM, bike);
  wR.position.set(BIKE_RA, 0.35, 0); wF.position.set(BIKE_FA, 0.35, 0);
  const crank = new THREE.Group(); crank.position.set(0, 0.3, 0); bike.add(crank);
  mesh(A.crank, BM, crank);
  const part = (n, unit) => { const m = mesh(A['r_' + n], RM); m.userData.unit = !!unit; return m; };
  const delt = G3.geo.delt || (G3.geo.delt = (() => { const g = new THREE.SphereGeometry(0.058, 16, 10); g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 3).fill(1), 3)); return g; })());
  const body = {
    torso: part('torso', true), pelvis: part('pelvis'), neck: mesh(G3.geo.neck || (G3.geo.neck = new THREE.CapsuleGeometry(0.045, 1, 3, 10)), M.skin),
    head: part('head'), helmet: part('helmet'), glasses: part('glasses'),
    delL: mesh(delt, RM[1]), delR: mesh(delt, RM[1]),
    thighL: part('thigh', true), thighR: part('thigh', true), calfL: part('calf', true), calfR: part('calf', true),
    footL: part('shoe'), footR: part('shoe'),
    uarmL: part('uarm', true), uarmR: part('uarm', true), farmL: part('farm', true), farmR: part('farm', true),
    handL: part('glove'), handR: part('glove')
  };
  body.neck.userData.unit = false;
  return { o, root, lean, bike, wR, wF, crank, body, M, dist: 0 };
};

const _g3Pose = g3Pose;
g3Pose = function(r, crankA, stand){
  if (!r.body.helmet || !r.body.helmet.geometry.groups.length) return _g3Pose(r, crankA, stand);
  const B = r.body, st = stand || 0;
  const cr = -crankA;
  r.crank.rotation.z = cr;
  const hx = -0.16 + 0.12 * st, hy = 0.95 + 0.1 * st;           // maluc
  const nx = hx + 0.46 - 0.1 * st, ny = hy + 0.3 + 0.12 * st;   // base del coll
  r.bike.rotation.x = st * 0.12 * Math.sin(crankA);
  g3Seg(B.torso, hx, hy, 0, nx, ny, 0);
  B.pelvis.position.set(hx - 0.01, hy - 0.01, 0); B.pelvis.rotation.z = -0.35 + 0.3 * st;
  const tx = nx - hx, ty = ny - hy, tl = Math.hypot(tx, ty);
  const shx = hx + tx * 0.86 - ty / tl * 0.015, shy = hy + ty * 0.86 + tx / tl * 0.015;
  g3Seg(B.neck, nx - 0.02, ny - 0.01, 0, nx + 0.07, ny + 0.08, 0);
  const hdx = nx + 0.1, hdy = ny + 0.12;
  B.head.position.set(hdx, hdy, 0); B.head.rotation.z = 0.05;
  B.glasses.position.set(hdx + 0.002, hdy + 0.012, 0); B.glasses.rotation.z = 0.05;
  B.helmet.position.set(hdx - 0.004, hdy + 0.012, 0); B.helmet.rotation.z = 0.0;
  for (let q = 0; q < 2; q++){
    const sd = q ? 1 : -1, ph = cr + (q ? Math.PI : 0);
    const px = 0.17 * Math.cos(ph), py = 0.3 + 0.17 * Math.sin(ph), pz = sd * 0.112;
    // peu: la cala (sota la planta) damunt del pedal; el turmell queda darrere i amunt; el taló baixa a dalt del cicle
    const fr = 0.18 * Math.sin(ph) - 0.06, fc = Math.cos(fr), fs = Math.sin(fr);
    const ox = px - 0.06 * fc - 0.024 * fs, oy = py + 0.012 - 0.06 * fs + 0.024 * fc;   // origen de la sabatilla
    const ax = ox - 0.03 * fc - 0.065 * fs, ay = oy - 0.03 * fs + 0.065 * fc, az = pz;
    const hz = sd * 0.085;
    const K = ik2(hx, hy, hz, ax, ay, az, 0.44, 0.43, 1, 0.25, sd * 0.05);
    const kx = K[0], ky = K[1], kz = K[2];
    g3Seg(q ? B.thighR : B.thighL, hx, hy, hz, kx, ky, kz);
    g3Seg(q ? B.calfR : B.calfL, kx, ky, kz, ax, ay, az);
    const F = q ? B.footR : B.footL;
    F.position.set(ox, oy, pz); F.rotation.z = fr;
    // braç: espatlla → colze → mans damunt les manetes
    const sz = sd * 0.175, hx2 = HOOD[0], hy2 = HOOD[1], hz2 = sd * HOOD[2];
    (q ? B.delR : B.delL).position.set(shx, shy, sd * 0.165);
    const E = ik2(shx, shy, sz, hx2, hy2, hz2, 0.29, 0.28, -0.2, -1, sd * 0.55), ex = E[0], ey = E[1], ez = E[2];
    g3Seg(q ? B.uarmR : B.uarmL, shx, shy, sz, ex, ey, ez);
    g3Seg(q ? B.farmR : B.farmL, ex, ey, ez, hx2 - 0.02, hy2, hz2);
    (q ? B.handR : B.handL).position.set(hx2 + 0.005, hy2 + 0.005, hz2);
  }
};

document.title = 'PainCave ERG · Realista';

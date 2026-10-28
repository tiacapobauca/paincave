# PainCave ERG · v3

App web per al rodet **Wahoo Kickr Core** (mode ERG i rutes simulades) amb el pols del **Garmin**.
Funciona a Chrome (Android i Windows) per Bluetooth. Aquesta carpeta és l'app sencera:

| Fitxer | Per a què serveix |
|---|---|
| `index.html` | l'app (tot en un sol fitxer; també funciona si l'obres directament) |
| `manifest.webmanifest`, `sw.js` | fan que es pugui **instal·lar** i que funcioni **sense connexió** |
| `icon-*.png` | icones de l'app |

---

## 1. Publicar-la a GitHub Pages (un sol cop)

1. Entra a <https://github.com> i crea un compte (si no en tens).
2. **New repository** → nom `paincave` → **Public** → *Create repository*.
3. A la pàgina del repositori: **uploading an existing file** → arrossega-hi els fitxers d'aquesta carpeta
   (`index.html`, `manifest.webmanifest`, `sw.js`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`) → **Commit changes**.
4. **Settings → Pages** → *Source*: **Deploy from a branch** · *Branch*: **main** i **/(root)** → **Save**.
5. Al cap d'un o dos minuts l'app és a **`https://EL-TEU-USUARI.github.io/paincave/`**.

**Instal·lar-la**
- **Android (Chrome):** obre l'adreça → menú ⋮ → **Instal·la l'aplicació** (o *Afegeix a la pantalla d'inici*).
- **Windows (Chrome o Edge):** obre l'adreça → icona d'instal·lar a la barra d'adreces (o el botó **Instal·la l'app** de la secció *Dades*).

Queda com una app més, a pantalla completa, i s'obre encara que no tinguis connexió.

**Actualitzar-la:** puja el nou `index.html` al repositori (substitueix l'antic). La propera vegada que obris l'app amb connexió ja tindràs la versió nova.

---

## 2. Sincronitzar el progrés amb Google Drive (un sol cop, ~10 minuts)

Les dades es desen en una **carpeta privada del teu Drive que només veu aquesta app** (no apareix entre els teus fitxers).
Se sincronitzen: workouts, rutes, rècords i millors voltes, historial, FTP, pesos i dificultat.
Les preferències de pantalla (2D/3D, càmera, so, zoom del mapa) són de cada dispositiu.

### 2a. Crear l'«ID de client» a Google Cloud

1. Entra a <https://console.cloud.google.com> amb el teu compte de Google.
2. A dalt: **Selecciona un projecte → Projecte nou** → nom `PainCave` → *Crea*.
3. Menú ☰ → **APIs i serveis → Biblioteca** → cerca **Google Drive API** → **Habilita**.
4. Menú ☰ → **APIs i serveis → Pantalla de consentiment d'OAuth** (o *Google Auth Platform*):
   - Tipus d'usuari **Extern** · nom de l'app `PainCave` · el teu correu com a correu d'assistència i de contacte.
   - A **Públic / Audience → Usuaris de prova**, afegeix el teu correu de Google.
5. Menú ☰ → **APIs i serveis → Credencials → Crea credencials → ID de client d'OAuth**:
   - Tipus d'aplicació: **Aplicació web**.
   - **Orígens de JavaScript autoritzats** → *Afegeix URI* → `https://EL-TEU-USUARI.github.io` (sense `/paincave` ni barra final).
   - *Crea* → copia l'**ID de client** (acaba en `.apps.googleusercontent.com`).

### 2b. Posar-lo a l'app

- A l'app: **Dades → Configuració de la sincronització** → enganxa l'ID de client → **Connecta**.
  Et demanarà entrar amb Google i donar permís. És la teva pròpia app: si surt l'avís «Google no ha verificat aquesta aplicació», toca *Continua*.
- Fes el mateix a l'altre dispositiu. Si no vols haver d'enganxar l'ID a cada dispositiu, escriu-lo a
  `const GOOGLE_CLIENT_ID = '…'` dins `index.html` i torna a pujar el fitxer.

### Com funciona
- En obrir l'app, en acabar cada sessió i uns segons després de cada canvi, es sincronitza sola si l'accés és vigent.
- L'accés de Google dura **1 hora**. Passat aquest temps, la fila *Google Drive* diu «toca per sincronitzar»: un toc i llestos (la finestra de Google s'obre i es tanca sola).
- Si el mateix element s'ha canviat als dos dispositius, guanya el canvi més recent. Els esborrats també es propaguen.

**Sense núvol:** *Exporta còpia* desa un `.json` amb tot el progrés, i *Importa còpia* el fusiona a l'altre dispositiu.

**Passar-hi el que ja tenies a la versió antiga:** obre aquest `index.html` de la mateixa manera que obries l'antic
(des de Baixades, al mateix navegador). Les dades antigues es converteixen soles. Toca **Exporta còpia** i, després, a l'app publicada, **Importa còpia**.

---

## 3. Novetats d'aquesta versió

- **Voltes lliures:** si un track acaba on comença, és un **circuit**. Per defecte es roda en **Lliure** (acabes quan vols amb *Fi*); amb − / + pots fixar el nombre de voltes.
  Durant el recorregut, **Última volta** fa que acabis en passar per meta. Cada volta es desa com a volta al `.fit`.
- **Fantasma de la millor volta** als circuits (a les rutes obertes, el de la ruta sencera).
- **Mapa un 15 % més gran** amb tres zooms (toca'l): *tot el recorregut*, *zona 2 km* i *a prop 600 m*. Hi surten els altres ciclistes i el fantasma.
- **Gràfics 3D:**
  - on el recorregut torna pel mateix lloc, les dues passades són una sola carretera de doble sentit (abans se solapaven);
  - encreuaments a nivell, ponts quan un tram passa per damunt d'un altre i murs de contenció entre trams propers a diferent altura;
  - res de vegetació, fites ni murs damunt l'asfalt;
  - ciclista nou (tors, espatlles, braços) i pedaleig en el sentit correcte.
- **Historial** de sessions (7 i 30 dies: hores, TSS i km).
- **App instal·lable** i **sincronització amb Google Drive**.

**Els altres ciclistes** van segons el teu FTP i el teu pes. El ritme base és el 72 % del teu FTP en W/kg (amb un mínim d'1,5 W/kg),
i cadascun va entre el 72 % i el 130 % d'aquest ritme. En pla, en W/kg, fan entre el 52 % i el 94 % del teu FTP; a les pujades un 10 % més, i a les baixades
gairebé no pedalen. Es calcula en començar cada recorregut, amb l'FTP i el pes que tinguis posats.

---

## 4. Versió realista (`realista.html`)

És la mateixa app, amb el 3D refet a partir de models i textures fets amb **Blender**:
bicicleta de carretera amb geometria real (rodes de perfil alt, discs, transmissió), ciclista modelat
(casc amb ventilació, ulleres, sabatilles), pins, oliveres, garrovers, xiprers, mates, margallons i roques
modelats amb branques i fulles, siluetes llunyanes renderitzades amb Cycles, i textures d'asfalt, terra,
grava i marges de pedra en sec. Les dades (workouts, rutes, historial…) són les mateixes que les de l'app normal.

S'obre a **`https://tiacapobauca.github.io/paincave/realista.html`**. L'app normal (`index.html`) no canvia.

**Com es genera** (no s'ha d'editar `realista.html` a mà):

```bash
pip install bpy pillow numpy        # Blender com a mòdul de Python (només per refer els models)
python3 blender/build.py            # models i textures → blender/out/assets.json (~1 min)
python3 blender/make_realista.py    # index.html + assets.json + blender/realista.js → realista.html
```

Si només canvies `index.html`, n'hi ha prou amb el darrer pas: així la versió realista també té les millores.

| Fitxer | Què fa |
|---|---|
| `blender/bike.py`, `rider.py`, `veg.py`, `textures.py` | modelen la bici, el ciclista, la vegetació i les textures |
| `blender/realista.js` | substitueix les funcions del 3D de l'app per fer servir els models |
| `blender/preview.py` | render ràpid d'un mòdul amb Cycles per revisar-lo (`python3 blender/preview.py bike prova.png`) |

# PainCave ERG · v4

App web per al rodet **Wahoo Kickr Core** (mode ERG i rutes simulades) amb el pols del **Garmin**.
Funciona a Chrome (Android i Windows) per Bluetooth. Aquesta carpeta és l'app sencera:

| Fitxer | Per a què serveix |
|---|---|
| `index.html` | l'app (tot en un sol fitxer; també funciona si l'obres directament) |
| `manifest.webmanifest`, `sw.js` | fan que es pugui **instal·lar** i que funcioni **sense connexió** |
| `icon-*.png` | icones de l'app |
| `assets/` | models 3D, textures i cel fets amb Blender (l'app els carrega quan s'obre des del web) |
| `blender/` | els programes que generen `assets/` (no calen per fer servir l'app) |
| `versions/` | **còpia de cada versió anterior** de l'app (`versions/v3/index.html` és la v3 sencera) |

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

## 3. Novetats de la versió 4

- **Gràfics 3D fets amb Blender**, ara dins l'app normal (ja no hi ha `realista.html`):
  - **cel real** amb núvols volumètrics (renderitzat amb Cycles), que també il·lumina l'escena i es reflecteix a la bici;
  - **ciclista d'una sola peça** amb articulacions suaus (malla amb ossos), casc, ulleres i sabatilles modelats, i bicicleta de carretera detallada;
  - **terreny amb textures** d'herba, terra i roca que es barregen segons el lloc;
  - pins, oliveres, garrovers, xiprers, margallons, mates i roques modelats.
  Si s'obre `index.html` directament com a fitxer (sense web), es fan servir els gràfics senzills d'abans.
- **Mode cursa** (botó **Cursa** a cada ruta, o **Cursa ràpida** a la portada): tries 5–20 rivals i el nivell (*Fàcil*, *Igualat*, *Dur*,
  relatiu al teu FTP en W/kg), compte enrere i sortida en grup. Els rivals són escaladors, rodadors o esprintadors: surten forts,
  van a roda, ataquen i esprinten al final. **El rebuf és automàtic** (fins a un 32 % menys d'aire). Classificació en viu, podi i
  taula de temps al final; el resultat es desa a l'historial.
- **Aspecte nou**: portada amb imatge i resum de la setmana, dispositius més compactes, pestanyes fixes i targetes en dues columnes a l'ordinador.
  Les dades i la sincronització són al plegable de baix de tot.
- **Còpia de la versió anterior**: `versions/v3/index.html` (a la web: `…/paincave/versions/v3/`). Fa servir les mateixes dades.

De la versió 3 es mantenen les voltes lliures, el fantasma, el mapa amb tres zooms, l'historial, la instal·lació i la sincronització amb Google Drive.

**Els altres ciclistes (fora de cursa)** van segons el teu FTP i el teu pes. El ritme base és el 72 % del teu FTP en W/kg (amb un mínim d'1,5 W/kg),
i cadascun va entre el 72 % i el 130 % d'aquest ritme.

---

## 4. Com es generen els gràfics (`blender/` → `assets/`)

Només cal si vols canviar models o textures. Blender es fa servir com a mòdul de Python, sense obrir el programa:

```bash
pip install bpy pillow numpy
python3 blender/build.py                 # tot (el cel triga uns minuts)
python3 blender/build.py body veg        # o només algunes etapes: bike rider body veg tex sky
```

Cada etapa es desa a `blender/out/` i al final sempre es torna a muntar `assets/` (`g3.bin` amb les malles, les textures `.webp`
i `g3.json` amb l'índex i els colors del cel). `assets/hero.webp` és una captura de l'app per a la portada.

| Fitxer | Què fa |
|---|---|
| `blender/bike.py`, `rider.py`, `body.py` | bicicleta, cap/casc/ulleres/sabatilles i cos amb ossos |
| `blender/veg.py`, `textures.py`, `sky.py` | vegetació, textures (carretera, terreny, pedra) i cel amb núvols |
| `blender/preview.py` | render ràpid d'un mòdul per revisar-lo (`python3 blender/preview.py bike prova.png`) |

**Abans de publicar una versió nova**, copia l'`index.html` actual a `versions/vN/` perquè l'anterior no es perdi mai.

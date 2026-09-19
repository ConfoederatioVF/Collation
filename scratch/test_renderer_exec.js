let { app, BrowserWindow } = require("electron");
let path = require("path");
let fs = require("fs");
let pngjs = require("pngjs");

app.commandLine.appendSwitch("disable-site-isolation-trials");
app.commandLine.appendSwitch("enable-features", "SharedArrayBuffer");
app.commandLine.appendSwitch("js-flags", "--max-old-space-size=262144 --expose-gc");

app.whenReady().then(() => {
  let win = new BrowserWindow({
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "../core/preload.js"),
      contextIsolation: false,
      enableRemoteModule: false,
      nodeIntegration: true,
      webSecurity: false
    }
  });

  win.webContents.on("console-message", (event, ...args) => {
    let msg = (event && event.message !== undefined) ? event.message : args[1];
    console.log(`[RENDERER] ${msg}`);
  });

  win.loadFile(path.join(__dirname, "../index.html"));

  win.webContents.on("did-finish-load", async () => {
    setTimeout(async () => {
      try {
        let result = await win.webContents.executeJavaScript(`
          (async () => {
            try {
              console.log("[IN RENDERER] Generating Base Raster for 1600...");
              let out_path = await population_Stadester_rasters.generateStadesterBaseRaster(1600);
              console.log("[IN RENDERER] Done generating Base Raster:", out_path);
              return { success: true, path: out_path };
            } catch (err) {
              console.error("[IN RENDERER ERROR]", err.stack || err);
              return { error: String(err) };
            }
          })()
        `);
        console.log("[TEST RESULT]", result);
        
        if (result && result.path) {
          let buf = fs.readFileSync(result.path);
          let png = pngjs.PNG.sync.read(buf);
          let non_zero = 0;
          let sample_pixels = [];
          for (let y = 0; y < png.height; y++) {
            for (let x = 0; x < png.width; x++) {
              let idx = (y * png.width + x) * 4;
              let r = png.data[idx];
              let g = png.data[idx+1];
              let b = png.data[idx+2];
              let a = png.data[idx+3];
              if (r !== 0 || g !== 0 || b !== 0 || a !== 0) {
                non_zero++;
                if (sample_pixels.length < 10) {
                  sample_pixels.push({ x, y, rgba: [r, g, b, a] });
                }
              }
            }
          }
          console.log("=== 1600 BASE RASTER ANALYSIS ===");
          console.log("Non-zero pixels count:", non_zero);
          console.log("Sample pixels (x, y):", sample_pixels);
        }
      } catch (err) {
        console.error("[EXEC ERROR]", err);
      }
      setTimeout(() => app.quit(), 1000);
    }, 4000);
  });
});

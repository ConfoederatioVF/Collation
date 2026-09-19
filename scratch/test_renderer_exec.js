let { app, BrowserWindow } = require("electron");
let path = require("path");

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

  win.webContents.on("console-message", (event, level, message, line, sourceId) => {
    console.log(`[RENDERER] ${message}`);
  });

  win.webContents.on("render-process-gone", (event, detailed) => {
    console.error("[RENDER PROCESS GONE]", detailed);
  });

  win.loadFile(path.join(__dirname, "../index.html"));

  win.webContents.on("did-finish-load", async () => {
    console.log("[TEST] Page loaded. Waiting 3s for Vercengen startup...");
    setTimeout(async () => {
      console.log("[TEST] Executing population_Stadester in Electron renderer...");
      try {
        let result = await win.webContents.executeJavaScript(`
          (async () => {
            try {
              console.log("[TEST IN RENDERER] population_Stadester type:", typeof population_Stadester);
              console.log("[TEST IN RENDERER] Running processRasters for year -3000...");
              let res = await population_Stadester.processRasters({
                exclude: ["A", "B", "C", "D", "E"],
                years: [-3000]
              });
              console.log("[TEST IN RENDERER] processRasters finished successfully!");
              return { success: true };
            } catch (err) {
              console.error("[TEST IN RENDERER ERROR]", err.stack || err);
              return { error: String(err) };
            }
          })()
        `);
        console.log("[TEST RESULT]", result);
      } catch (err) {
        console.error("[EXEC ERROR]", err);
      }
      setTimeout(() => app.quit(), 2000);
    }, 4000);
  });
});

let { app, BrowserWindow } = require("electron");
let path = require("path");

app.whenReady().then(() => {
  let win = new BrowserWindow({
    show: false,
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true,
      webSecurity: false
    }
  });

  win.webContents.on("console-message", (e, ...args) => {
    let msg = (e && e.message !== undefined) ? e.message : args[1];
    console.log("[ELECTRON RENDERER]", msg);
  });

  win.loadURL("data:text/html,<html><body><h1>Worker Test</h1></body></html>");

  win.webContents.on("did-finish-load", async () => {
    let res = await win.webContents.executeJavaScript(`
      (async () => {
        let cp = require("child_process");
        let { Worker } = require("worker_threads");
        
        let test_results = {};
        
        //Test child_process in renderer
        try {
          let stdout = cp.execSync("node -e \\"console.log('cp_ok')\\"").toString().trim();
          test_results.child_process = stdout;
        } catch (e) {
          test_results.child_process = "error: " + e.message;
        }
        
        //Test worker_threads in renderer
        try {
          let w = new Worker("const { parentPort } = require('worker_threads'); parentPort.postMessage('wt_ok');", { eval: true });
          let wt_promise = new Promise((resolve) => {
            w.on('message', m => resolve(m));
            w.on('error', err => resolve('error: ' + err.message));
          });
          test_results.worker_threads = await wt_promise;
        } catch (e) {
          test_results.worker_threads = "error: " + e.message;
        }
        
        return test_results;
      })()
    `);
    console.log("[TEST RESULTS FROM RENDERER]", res);
    app.quit();
  });
});

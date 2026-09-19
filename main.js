
//Import libraries
let { app, BrowserWindow, dialog, ipcMain, Menu, session, shell } = require("electron");
let discord = require("@xhayper/discord-rpc");
let fs = require("fs");
let path = require("path");
let readline = require("readline");
let remote_main = require("@electron/remote/main");
let { performance } = require("perf_hooks");

//Metadata - Social Media
let client_id = "1541118076932722698"; //Application ID for Naissance in Discord Developer Portal
let discord_config_path = "./common/defines/social_media/discord.json";
let is_rpc_ready = false;
let rpc = new discord.Client({ clientId: client_id });

//Metadata - Title
let latest_fps = 0;
let naissance_version = "1.96b Lion";
let title_update_interval;
let win;

//Initialise functions
{
  function createWindow () {
    //Declare local instance variables
    win = new BrowserWindow({
      width: 3840,
      height: 2160,
      webPreferences: {
        preload: path.join(__dirname, "core/preload.js"),
        
        contextIsolation: false,
        enableRemoteModule: false,
        nodeIntegration: true,
        webSecurity: false,
        webviewTag: true
      },
      
      icon: path.join(process.cwd(), `gfx/logo.png`)
    });
    
    //Load file; open Inspect Element
    win.webContents.openDevTools();
    win.setMenuBarVisibility(false);
    
    //Forward renderer console output to terminal stdout
    win.webContents.on("console-message", (event, ...args) => {
      let msg = (event && event.message !== undefined) ? event.message : args[1];
      console.log(`[RENDERER] ${msg}`);
    });
    win.webContents.on("render-process-gone", (event, detailed) => {
      console.error("[RENDER PROCESS GONE]", detailed);
      if (process.platform !== "darwin") app.quit();
    });
    
    win.loadFile("index.html");
    
    //Listen for FPS updates from the renderer process
    ipcMain.on("update-fps", (event, fps) => {
      latest_fps = fps;
    });
    
    //Update the title every second with the latest data
    title_update_interval = setInterval(function () {
      let is_destroyed = !win || win.isDestroyed();
      if (is_destroyed) {
        clearInterval(title_update_interval);
        return;
      }
      
      let memory_usage = process.memoryUsage();
      let heap_used_mb = (memory_usage.heapUsed/1024/1024).toFixed(2);
      let rss_mb = (memory_usage.rss/1024/1024).toFixed(2);
      let title_string = `Naissance World Model ${naissance_version} - FPS: ${latest_fps} | RAM: RSS ${rss_mb}MB/Heap ${heap_used_mb}MB`;
      
      win.setTitle(title_string);
    }, 1000);
    
    //Clean up memory and intervals on close
    win.on("closed", function () {
      clearInterval(title_update_interval);
      win = null;
      if (process.platform !== "darwin") app.quit();
    });
    
    //<a href> handling
    //Intercept link clicks that would navigate the current window
    win.webContents.on("will-navigate", (event, url) => {
      if (url !== win.webContents.getURL()) {
        event.preventDefault();
        shell.openExternal(url);
      }
    });
    
    //Intercept target="_blank" or window.open()
    win.webContents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url);
      return { action: "deny" };
    });
    
    //Return statement
    return win;
  }
}

//Initialise social media functions
{
  Discord_initRPC = async function () {
    try {
      //Strict 3-second timeout so offline or unresponsive Discord never stalls startup
      let login_promise = rpc.login();
      let timeout_promise = new Promise((_, reject) => setTimeout(() => reject(new Error("Discord RPC timeout")), 3000));
      
      await Promise.race([login_promise, timeout_promise]);
      is_rpc_ready = true;
      
      if (fs.existsSync(discord_config_path)) {
        let discord_config_obj = JSON.parse(fs.readFileSync(discord_config_path, "utf8"));
        
        Discord_setRPCActivity({
          startTimestamp: Date.now(),
          
          ...discord_config_obj.default_activity,
          ...discord_config_obj.onlaunch_activity
        });
      }
    } catch (e) {
      console.warn(`Failed to connect to Discord RPC:`, e.message || e);
    }
  };
  
  Discord_setRPCActivity = function (arg0_activity) {
    //Convert from parameters
    let activity = arg0_activity;
    
    if (!is_rpc_ready) return;
    rpc.user?.setActivity(activity);
  };
}

//App handling
{
  app.commandLine.appendSwitch("disable-site-isolation-trials");
  app.commandLine.appendSwitch("disk-cache-size", "67108864"); //64 MB disk cache cap
  app.commandLine.appendSwitch("media-cache-size", "67108864");
  app.commandLine.appendSwitch("enable-features", "SharedArrayBuffer");
  app.commandLine.appendSwitch("js-flags", "--max-old-space-size=262144 --expose-gc");
  
  //Launch app when ready
  app.whenReady().then(() => {
    remote_main.initialize();
    
    //Prune disk cache if requested via command line flag
    if (process.argv.includes("--clear-cache")) {
      try {
        session.defaultSession.clearCache();
      } catch (e) {}
    }
    
    //Create the window and instantiate it; initialise social media
    let win = createWindow();
    remote_main.enable(win.webContents);
    Discord_initRPC();
    
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
    if (Menu && Menu.setApplicationMenu) Menu.setApplicationMenu(null);
    
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      let headers = { ...details.responseHeaders };
      if (headers["Access-Control-Allow-Origin"]) {
        headers["Access-Control-Allow-Origin"] = ["*"];
      }
      headers["Access-Control-Allow-Methods"] = ["GET", "POST", "OPTIONS", "PUT", "PATCH", "DELETE"];
      headers["Access-Control-Allow-Headers"] = ["Content-Type", "Authorization"];
      
      callback({ responseHeaders: headers });
    });
  });
  
  //Window lifecycle defaults
  app.on("before-quit", async () => {
    if (is_rpc_ready) await rpc.destroy();
  });
  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}

//IPC handling
{
  let ve = require("./UF/js/vercengen/engine/vercengen_electron");
  ve.initialiseIPC();
  
  ipcMain.on("discord-update-presence", (_event, activity) => {
    Discord_setRPCActivity(activity);
  });
}
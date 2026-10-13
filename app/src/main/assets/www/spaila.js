// Spaila bridge: lets web pages ask Android to do things.
(function () {
  var _callbacks = {};  // id -> {resolve, reject} for waiting two-way calls
  var _nextId = 1;      // increases by 1 for each new call

  function send(fn, args) {
    if (window.SpailaNative) {
      window.SpailaNative.postMessage(JSON.stringify({ fn: fn, args: args }));
    } else {
      console.log("Spaila: not running inside the Android app", fn, args);
    }
  }

  // Like send(), but returns a Promise. Android will call _handleReply with the result.
  function sendAndWait(fn, args) {
    return new Promise(function (resolve, reject) {
      if (!window.SpailaNative) {
        reject(new Error("Not running inside the Android app"));
        return;
      }
      var id = _nextId++;
      _callbacks[id] = { resolve: resolve, reject: reject };
      window.SpailaNative.postMessage(JSON.stringify({ fn: fn, args: args, id: id }));
    });
  }

  // Load local config asynchronously
  var _config = {};
  try {
    fetch('app-config.json').then(function(r){return r.json();}).then(function(c){
      _config = c;
      window.Spaila.config = c;
    }).catch(function(){});
  } catch(e) {}

  window.Spaila = {
    config: _config,
    toast: function (text) {
      send("toast", [String(text)]);
    },
    showNotification: function (title, message) {
      send("showNotification", [String(title), String(message)]);
    },
    // id: a whole number you choose. Using the same id again replaces the old one.
    scheduleNotification: function (id, title, message, seconds) {
      send("scheduleNotification", [
        Math.round(Number(id)), String(title), String(message), Math.round(Number(seconds))
      ]);
    },
    cancelScheduledNotification: function (id) {
      send("cancelScheduledNotification", [Math.round(Number(id))]);
    },
    // Buzz the phone for some milliseconds (1 to 5000).
    vibrate: function (ms) {
      send("vibrate", [Math.round(Number(ms) || 200)]);
    },
    // Opens the Android share sheet with some text.
    share: function (text) {
      send("share", [String(text)]);
    },
    copyToClipboard: function (text) {
      send("copyToClipboard", [String(text)]);
    },
    // true = screen stays on, false = back to normal.
    keepScreenOn: function (on) {
      send("keepScreenOn", [!!on]);
    },
    flashlight: function (on) {
      send("flashlight", [!!on]);
    },
    // Opens the phone's battery settings (so the user can set this app to "No restrictions").
    openBatterySettings: function () {
      send("openBatterySettings", []);
    },
    // Starts a background service with a small ongoing notification.
    startKeepAlive: function (title, text) {
      send("startKeepAlive", [String(title || "Running"), String(text || "Tap to open")]);
    },
    stopKeepAlive: function () {
      send("stopKeepAlive", []);
    },
    // Two-way: returns a Promise that resolves with battery level 0-100 (or -1).
    getBatteryLevel: function () {
      return sendAndWait("getBatteryLevel", []);
    },
    // Speak text using the phone's built-in voice engine (offline)
    speak: function (text, pitch, rate) {
      send("speak", [String(text || ""), Number(pitch || 1.0), Number(rate || 1.0)]);
    },
    stopSpeaking: function () {
      send("stopSpeaking", []);
    },
    // Precise tactile click: "click", "tick", "heavy", or "double"
    haptic: function (style) {
      send("haptic", [String(style || "click")]);
    },
    // Two-way: returns { osVersion, brand, model, appVersion, isOnline, networkType }
    getDeviceInfo: function () {
      return sendAndWait("getDeviceInfo", []);
    },
    // Updates the home screen widget with title, text, and optional progress (0-100 or -1 to hide)
    updateWidget: function (title, text, progress) {
      var p = typeof progress === "number" ? Math.round(progress) : -1;
      send("updateWidget", [String(title || ""), String(text || ""), p]);
    },
    // Plays a zero-latency system tone: "click", "beep", "success", "alert"
    playSound: function (type) {
      send("playSound", [String(type || "click")]);
    },
    // Sets screen brightness: 0.0 (dimmest) to 1.0 (full brightness), or -1 for system default
    setBrightness: function (level) {
      send("setBrightness", [Number(level)]);
    },
    // Opens WhatsApp chat directly to phone number (e.g. "+27123456789") with pre-filled message
    openWhatsApp: function (phone, message) {
      send("openWhatsApp", [String(phone || ""), String(message || "")]);
    },
    // Authenticates using Fingerprint, Face, or Phone PIN. Returns Promise<boolean>
    authenticate: function (prompt) {
      return sendAndWait("authenticate", [String(prompt || "Verify your identity")]);
    },
    // Opens voice recognition dialog and returns recognized spoken text as a Promise<string>
    startSpeechRecognition: function (prompt) {
      return sendAndWait("startSpeechRecognition", [String(prompt || "Speak now...")]);
    },
    // Opens Google Play Store to rate this app
    rateApp: function () {
      send("rateApp", []);
    },
    // Android calls this to deliver a reply. Do not call this yourself.
    _handleReply: function (id, result, error) {
      var cb = _callbacks[id];
      if (!cb) return;
      delete _callbacks[id];
      if (error != null) { cb.reject(new Error(error)); }
      else { cb.resolve(result); }
    }
  };
})();

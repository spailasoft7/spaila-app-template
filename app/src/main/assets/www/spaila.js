// Spaila bridge: lets web pages ask Android to do things.
(function () {
  function send(fn, args) {
    if (window.SpailaNative) {
      window.SpailaNative.postMessage(JSON.stringify({ fn: fn, args: args }));
    } else {
      console.log("Spaila: not running inside the Android app", fn, args);
    }
  }

  window.Spaila = {
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
    }
  };
})();

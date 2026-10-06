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
    }
  };
})();

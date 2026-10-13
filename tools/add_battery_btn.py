f = "app/src/main/assets/www/features-test.html"
with open(f, encoding="utf-8") as fp:
    src = fp.read()

# Add button after the cancel button
src = src.replace(
    '  <button id="cancelBtn">Cancel the 15 second one</button>',
    '  <button id="cancelBtn">Cancel the 15 second one</button>\n'
    '  <button id="batteryBtn">Get Battery Level</button>'
)

# Add JS handler before the cancelBtn handler
src = src.replace(
    '    document.getElementById("cancelBtn").addEventListener("click", function () {',
    '    document.getElementById("batteryBtn").addEventListener("click", function () {\n'
    '      Spaila.getBatteryLevel().then(function (level) {\n'
    '        say("Battery: " + level + "%");\n'
    '      }).catch(function (err) {\n'
    '        say("Error: " + err.message);\n'
    '      });\n'
    '    });\n'
    '    document.getElementById("cancelBtn").addEventListener("click", function () {'
)

with open(f, "w", encoding="utf-8") as fp:
    fp.write(src)
print("Done.")

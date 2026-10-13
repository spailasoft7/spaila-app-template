f = 'app/src/main/assets/www/features-test.html'
with open(f, encoding='utf-8') as fp: src = fp.read()

target = '<button onclick="Spaila.updateWidget(\'Spaila Soft\', \'Updated from JS at \' + new Date().toLocaleTimeString()); Spaila.toast(\'Home widget updated!\');">Update Home Widget Text</button>'
new_buttons = """<button onclick="Spaila.updateWidget('Task Progress', '3 of 4 tasks finished', 75); Spaila.toast('Widget set to 75% progress');">Update Widget (75% Progress)</button>
    <button onclick="Spaila.updateWidget('Habit Goal', 'Goal 100% completed', 100); Spaila.toast('Widget set to 100%');">Update Widget (100% Progress)</button>
    <button onclick="Spaila.updateWidget('Spaila Soft', 'No progress bar', -1); Spaila.toast('Widget text updated');">Update Widget (Hide Progress)</button>"""

if target in src:
    src = src.replace(target, new_buttons)

js_target = 'window.onSpailaSharedText = function (text) {'
js_add = """window.onSpailaWidgetAction = function (action) {
      alert('Widget action tapped: ' + action);
    };
    window.onSpailaSharedText = function (text) {"""

if js_target in src:
    src = src.replace(js_target, js_add)

with open(f, 'w', encoding='utf-8') as fp: fp.write(src)
print('Test page updated successfully')

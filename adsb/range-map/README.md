# Download the outline.json from ultrafeeder:/run/readsb/outline.json, and name it {1..4}-outline.json


ssh neon.ioui.eu 'docker exec ultrafeeder cat /run/readsb/outline.json' > "./range-map/outline/$(date +%Y_%m_%d-%H-%M)-Spider+LNA.json"

python3 -m http.server & xdg-open http://0.0.0.0:8000/map.html

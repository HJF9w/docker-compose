## Complete List of tar1090 URL Parameters

  These parameters can be appended to your URL (e.g., http://ip/tar1090/?pTracks&mapDim=0.5). Note that parameters are case-insensitive.

  1. View & UI Customization
   * zoom=1-20: Set initial zoom level.
   * scale=X: Global interface scaling (e.g., scale=1.2).
   * iconScale=X: Scale aircraft icons (multiplies with global scale).
   * labelScale=X: Scale aircraft labels.
   * enableLabels: Show aircraft labels by default (same as 'L' button).
   * extendedLabels=0|1|2: Label detail level (same as 'O' button).
   * trackLabels: Show labels on the trail/track (same as 'K' button).
   * noVanish: Persistence mode; planes don't disappear when signal is lost (same as 'P' button).
   * mapDim=0.1-1.0: Map dimming (0.1 is very dark, 1.0 is normal).
   * mapContrast=0.1-1.0: Adjust map contrast.
   * hideSidebar: Hides the sidebar on load.
   * sidebarWidth=X: Set sidebar width in pixels.
   * hideButtons: Hides all UI buttons (useful for displays).
   * mobile / desktop: Force specific layout mode.
   * kiosk: Enables trails, hides buttons, and scales UI for public displays.
   * baseMap=mapname: Set initial map (e.g., osm, carto_light, b_map).
   * atcStyle: Minimalistic ATC-style rendering.
   * darkerColors: Uses more saturated/darker colors for tracks.
   * squareMania: Replaces aircraft icons with colored squares.

  2. Filtering
   * icao=hex: Select and isolate specific hex ID(s). Comma-separated for multiple.
   * reg=registration: Select by registration (e.g., N123AB).
   * mil: Show only military aircraft (same as 'U' button).
   * filterAltMin=FT / filterAltMax=FT: Altitude range filter.
   * filterCallSign=regex: Filter by callsign (e.g., ^UAL for United).
   * filterType=type: Filter by aircraft type code (e.g., B738).
   * filterDescription=desc: Filter by type description (e.g., L2J).
   * filterSources=src1,src2: Filter by source (e.g., adsb,mlat,uat).
   * filterDbFlag=flag: Filter by flags (e.g., military,pia,ladd).
   * icaoFilter=hex1,hex2: Show only these aircraft and nothing else.
   * icaoBlacklist=hex1,hex2: Hide these specific aircraft.

  3. Special Features (Heatmap, Replay, History)
   * pTracks: Show persistent tracks (coverage map) for the last 8 hours.
   * pTracks=X: Show coverage for the last X hours.
   * replay: Enable the Replay/Playback interface.
   * heatmap: Enable coverage heatmap (dots).
   * realHeat: Enable "true" blurry heatmap.
   * heatDuration=X: Hours of data to include in heatmap (default 24).
   * heatEnd=X: Shift heatmap window into the past (e.g., heatEnd=24 starts heatmap from yesterday).
   * showTrace=YYYY-MM-DD: Show full history for a specific date (requires globe-history on the backend).

  4. Location & Navigation
   * SiteLat=LAT / SiteLon=LON: Temporarily set receiver location for range rings/distance.
   * centerReceiver: Center the map on your receiver.
   * lockDotCentered: Force map to stay centered on receiver.
   * autoselect: Automatically select the aircraft closest to the map center.

  ---

  How to Add Custom Buttons to the UI

  Since you are using the ultrafeeder Docker container, you can inject custom JavaScript to add buttons using the TAR1090_CONFIGJS_APPEND environment variable.

  The following snippet adds buttons for Replay, Heatmap, and pTracks to the top button bar.

  Add this to your docker-compose.yml:

```yaml
    1 services:
    2   ultrafeeder:
    3     environment:
    4       # ... your other environment variables ...
    5       - TAR1090_CONFIGJS_APPEND=
    6           window.addEventListener('load', function() {
    7             var container = document.querySelector('#header_top .buttonContainer');
    8             if (!container) return;
    9             function createBtn(text, title, url) {
   10               var btn = document.createElement('span');
   11               btn.className = 'button inActiveButton';
   12               btn.title = title;
   13               btn.style.marginLeft = '5px';
   14               btn.innerHTML = '<span class="buttonText">' + text + '</span>';
   15               btn.onclick = function() { window.location.href = url; };
   16               return btn;
   17             }
   18             container.appendChild(createBtn('RP', 'Replay Mode', '?replay'));
   19             container.appendChild(createBtn('HM', 'Heatmap', '?heatmap&realHeat'));
   20             container.appendChild(createBtn('PT', 'pTracks (Coverage)', '?pTracks'));
   21           });
```

  Note: In YAML, you may need to keep the TAR1090_CONFIGJS_APPEND value on a single line or use the | block scalar as shown above. If the one-liner doesn't work, ensure there are no line-breaks inside the JavaScript string.

  Built-in Sidebar Link
  If you just want one simple link in the sidebar, you can use these built-in variables:
   * TAR1090_IMAGE_CONFIG_LINK="https://yourlink.com"
   * TAR1090_IMAGE_CONFIG_TEXT="My Custom Link"


   

document.addEventListener('DOMContentLoaded', function () {
    const hueSlider = document.getElementById('hue');
    const brightnessSlider = document.getElementById('brightness');
    const popup = document.getElementById('colorPickerPopup');
    const openPopupLink = document.getElementById('openPopup');
    const okButton = document.getElementById('okButton');

    openPopupLink.addEventListener('click', (e) => {
        e.preventDefault();
        popup.style.display = 'block';
    });

    okButton.addEventListener('click', () => {
        popup.style.display = 'none';
    });

    function updateColor() {
        const hue = hueSlider.value;
        const brightness = brightnessSlider.value;
        const selectedColor = hslToHex(hue, 100, brightness * 100 / 255);
        setCookie("userColorPick", selectedColor, 30);

        const backgroundColor = adjustBrightness(selectedColor, -50);
        const menuColorSD = adjustBrightness(selectedColor, -35);
        const menuColor = adjustBrightness(selectedColor, -25);
        const menuColorSL = adjustBrightness(selectedColor, -10);
        const foregroundColor = adjustBrightness(selectedColor, 0);
        const descriptionColorSD = adjustBrightness(selectedColor, 10);
        const descriptionColor = adjustBrightness(selectedColor, 25);
        const descriptionColorSL = adjustBrightness(selectedColor, 30);
        const highlightColor = adjustBrightness(selectedColor, 100);
        
        document.documentElement.style.setProperty('--color-background', backgroundColor);
        document.documentElement.style.setProperty('--color-menu-sd', menuColorSD);
        document.documentElement.style.setProperty('--color-menu', menuColor);
        document.documentElement.style.setProperty('--color-menu-sl', menuColorSL);
        document.documentElement.style.setProperty('--color-description', descriptionColor);
        document.documentElement.style.setProperty('--color-foreground', foregroundColor);
        document.documentElement.style.setProperty('--color-description-sd', descriptionColorSD);
        document.documentElement.style.setProperty('--color-highlight', highlightColor);
        document.documentElement.style.setProperty('--color-description-sl', descriptionColorSL);

        const textColor = getTextColor(selectedColor);
        document.documentElement.style.setProperty('--color-text-gb', textColor);
        document.documentElement.style.setProperty('--color-text-sgb', textColor);
        document.documentElement.style.setProperty('--color-text-tgb', textColor);
        document.documentElement.style.setProperty('--color-text-titel', textColor);
        document.documentElement.style.setProperty('--color-right-h3', textColor);
        document.documentElement.style.setProperty('--color-middle-h5', textColor);

        const iconColor = getIconColor(selectedColor);
        document.documentElement.style.setProperty('--color-button-img', iconColor);
    }

    function hslToHex(h, s, l) {
        l /= 100;
        const a = s * Math.min(l, 1 - l) / 100;
        const f = n => {
            const k = (n + h / 30) % 12;
            const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
            return Math.round(255 * color).toString(16).padStart(2, '0');
        };
        return `#${f(0)}${f(8)}${f(4)}`;
    }

    function adjustBrightness(color, amount) {
        let usePound = false;

        if (color[0] === "#") {
            color = color.slice(1);
            usePound = true;
        }

        let num = parseInt(color, 16);

        let r = (num >> 16) + amount;
        if (r > 255) r = 255;
        else if (r < 0) r = 0;

        let g = ((num >> 8) & 0x00FF) + amount;
        if (g > 255) g = 255;
        else if (g < 0) g = 0;

        let b = (num & 0x0000FF) + amount;
        if (b > 255) b = 255;
        else if (b < 0) b = 0;

        return (usePound ? "#" : "") + (r.toString(16).padStart(2, '0')) + (g.toString(16).padStart(2, '0')) + (b.toString(16).padStart(2, '0'));
    }

    function getTextColor(color) {
        let r = parseInt(color.slice(1, 3), 16);
        let g = parseInt(color.slice(3, 5), 16);
        let b = parseInt(color.slice(5, 7), 16);

        let luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.44 ? "#000000" : "#ffffff";
    }

    function getIconColor(color) {
        let r = parseInt(color.slice(1, 3), 16);
        let g = parseInt(color.slice(3, 5), 16);
        let b = parseInt(color.slice(5, 7), 16);

        let luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.44 ? "0%" : "100%";
    }

    function setCookie(name, value, days) {
        const d = new Date();
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = "expires=" + d.toUTCString();
        document.cookie = name + "=" + value + ";" + expires + ";path=/";
    }

    function getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }

    // Read the cookie and set the sliders and color based on the stored value
    const userColorPick = getCookie("userColorPick");
    if (userColorPick) {
        const [hue, saturation, lightness] = hexToHsl(userColorPick);
        hueSlider.value = hue;
        brightnessSlider.value = Math.round(lightness * 2.55); // converting to the range of 0-255 for the slider
        updateColor();
    } else {
        updateColor();
    }

    function hexToHsl(hex) {
        hex = hex.replace(/^#/, '');
        let r = parseInt(hex.slice(0, 2), 16) / 255;
        let g = parseInt(hex.slice(2, 4), 16) / 255;
        let b = parseInt(hex.slice(4, 6), 16) / 255;

        let max = Math.max(r, g, b);
        let min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;

        if (max === min) {
            h = s = 0; // achromatic
        } else {
            let d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
    }

    hueSlider.addEventListener('input', updateColor);
    brightnessSlider.addEventListener('input', updateColor);
});

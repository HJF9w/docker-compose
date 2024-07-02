<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video</title>
    <link rel="stylesheet" href="material/style/colors.css">
    <link rel="stylesheet" href="material/style/style.css">
    <link rel="stylesheet" href="material/style/glass-button-style.css">
    <link rel="stylesheet" href="material/style/right.css">
    <link rel="stylesheet" href="material/style/middle.css">
    <script src="material/script.js"></script>
    <script src="material/colorPicker.js"></script>
    <link rel="icon" type="image/x-icon" href="material/images/favicon.gif">
</head>
<body>
    <div id="colorPickerPopup" class="popup">
        <button id="okButton">X</button>
        <label for="hue">Hue:</label>
        <input type="range" id="hue" class="slider" min="0" max="360">
        <label for="brightness">Brightness:</label>
        <input type="range" id="brightness" class="slider" min="50" max="200">
    </div>
    <?php include('material/getBaseURL.php'); ?>
    <div class="container">
        <div class="left">
            <?php include('material/left.php'); ?>
        </div>
        <div class="top">
            <a href="#" class="toggleElements tglass-button"><img class="button-img" src="material/images/menu.svg"/>Menu</a>
        </div>
        <div class="middle">
            <?php include('material/middle.php'); ?>
        </div>
        <div class="right">
            <?php include('material/right.php'); ?>
        </div>
    </div>
</body>
</html>

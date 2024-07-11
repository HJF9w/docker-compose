<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jet</title>
    <link rel="stylesheet" href="bubbles/style/style.css">
    <link rel="stylesheet" href="bubbles/style/dark-mode-style.css">    
    <link rel="stylesheet" href="bubbles/style/glass-button-style.css">    
    <link rel="stylesheet" href="bubbles/style/news-style.css">
    <link rel="icon" type="image/x-icon" href="bubbles/images/favicon.gif">
</head>
<body>
    <div class="foreground">
        <div class="header">
            <h2>Veranstalungs-Termine</h2>
            <p style="text-align: center;">SBW</p>
        </div>
        <div class="main">
            <?php include('content.php'); ?>
        </div>
        <div class="footer">
            <?php include('bubbles/menu.php'); ?>
        </div>
    </div>
    <div class="background">
        <section>
            <img src="bubbles/images/loewenzahn.jpg" style="width: auto; height: auto;">
        </section>
        <script src="bubbles/script.js"></script>
    </div>
</body>
</html>

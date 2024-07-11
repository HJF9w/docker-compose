<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="umami-script.js" data-website-id="8ae45013-37e6-4bb4-bbbe-b651ba3378d7"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jet</title>
    <link rel="stylesheet" href="bubbles/style/style.css">
    <link rel="stylesheet" href="bubbles/style/dark-mode-style.css">    
    <link rel="stylesheet" href="bubbles/style/glass-button-style.css">  
    <link rel="stylesheet" href="bubbles/style/image.css">  
    <link rel="icon" type="image/x-icon" href="bubbles/images/favicon.gif">
</head>
<body>
    <div class="foreground">
        <div class="header">
            <?php
            // Get the image name from the URL parameter
            if (isset($_GET['image'])) {
                $image = $_GET['image'];
                $imagePath = 'bubbles/images/' . $image;
                
                // Check if the image file exists
                if (file_exists($imagePath)) {
                    // Extract the name without the first 8 characters and the underscore
                    $displayName = substr($image, 9);
                    echo "<h2>" . htmlspecialchars($displayName) . "</h2>";
                } else {
                    echo "<h2>Image not found</h2>";
                }
            } else {
                echo "<h2>No image specified</h2>";
                echo "<p>" . $image . "</p>";
            }
            ?>
        </div>
        <div class="main">
            <?php
            // Display the image if it exists
            if (isset($image) && file_exists($imagePath)) {
                echo "<img src='" . htmlspecialchars($imagePath) . "' alt='" . htmlspecialchars($displayName) . "' />";
            } else {
                echo "<p>Image could not be found or no image was specified.</p>";
            }
            ?>
        </div>
        <div class="footer">
            <?php
            // Only show the download button if the image exists
            if (isset($image) && file_exists($imagePath)) {
                echo "<a href='javascript:history.back()' class='glass-button' id='orange'>🔙 Back</a>";
                echo "<a href> </a>";
                echo "<a href='bubbles/images/" . htmlspecialchars($image) . "' class='glass-button' id='blue' download>⬇️ Save this Image</a>";
            } else {
                echo "<a href='javascript:history.back()' class='glass-button' id='orange'>🔙 Back</a>";
            }
            ?>
            <button class="glass-button" id="themeToggle">Dark / Light</button>
        </div>
    </div>
    <div class="background">
        <section>
        </section>
        <script src="bubbles/script.js"></script>
    </div>
</body>
</html>

<?php
// Step 1: Get the 'v' parameter from the URL
if (isset($_GET['v'])) {
    $v = $_GET['v'];
    
    // Step 2: Construct paths and read README.md
    $readme_path = "material/videos/$v/README.md";
    
    if (file_exists($readme_path)) {
        $readme_content = file($readme_path);
        
        // Step 3: Extract title, play duration, and description
        if (!empty($readme_content)) {
            $titel = trim(str_replace("# ", "", $readme_content[0]));
            $playduration = trim(str_replace("## ", "", $readme_content[1]));
            $description = '';
            
            // Extract multiple lines starting with "###"
            for ($i = 2; $i < count($readme_content); $i++) {
                if (strpos($readme_content[$i], "### ") === 0) {
                    $description .= trim(str_replace("### ", "", $readme_content[$i])) . "\n";
                } else {
                    break; // Stop reading if it's not "### "
                }
            }
            $description = trim($description);
            
        } else {
            // Handle case where README.md is empty or unreadable
            $titel = "Video Titel";
            $playduration = "==:==";
            $description = "Beschreibung";
        }
    } else {
        // Handle case where README.md does not exist
        $titel = "Dieses Video konnte nicht gefunden werden.";
        $playduration = "Nicht Gefunden";
        $description = "Überprüfen sie die URL, eventuell<br>ist ihr link Fehlerhaft.";
    }?>
    <div class="player">
        <video controls loop muted src="material/videos/<?php echo $v; ?>/video.webm"></video>
    </div>
    <div class="title">
        <h2 style="text-align: left;"><?php echo $titel; ?></h2>
    </div>
    <div class="description">
        <div class="buttons">
            <a href="" class="sglass-button"><img class="button-img" src="material/images/info.svg"/><br>Info</a>
            <a href="" class="share sglass-button"><img class="button-img" src="material/images/share.svg"/><br>Teilen</a>
            <a href="<?php echo $baseURL?>material/videos/<?php echo $v; ?>/video.webm" class="sglass-button" download="<?php echo $titel; ?>"><img class="button-img" src="material/images/download.svg"/><br>Download</a>
        </div>
        <h5><?php echo nl2br($description); ?></h5>
    </div>
    <?php
} else {
    // Handle case where 'v' parameter is missing
    $titel = "Title not specified";
    $playduration = "Duration not specified";
    $description = "Description not specified";
    echo '<div class="description">
        <h2>Wählen sie ein Video aus.   <img id="responsiveImage" class="button-img" style="max-height: 2rem;" src="[]"></h2>
    </div>';
}
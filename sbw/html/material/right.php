<?php
// Directory where videos are stored
$videosDirectory = 'material/videos/';

// Read all directories in the videos directory
$directories = glob($videosDirectory . '*', GLOB_ONLYDIR);

// Check if there are directories available
if (empty($directories)) {
    echo '<p>No Videos found</p>';
} else {
    // Shuffle the array of directories to randomize order
    shuffle($directories);
    
    // Limit to maximum 5 directories or all available if fewer than 5
    $selectedDirectories = array_slice($directories, 0, min(10, count($directories)));

    // Function to read title and duration from README.md
    function getTitleAndDurationFromReadme($directory) {
        $readmeFile = $directory . '/README.md';
        if (file_exists($readmeFile)) {
            $readmeContent = file($readmeFile);
            if (!empty($readmeContent)) {
                $title = 'No Title Found';
                $duration = '==:==';

                // Loop through lines in README.md to find title and duration
                foreach ($readmeContent as $line) {
                    $line = trim($line);
                    if (strpos($line, '# ') === 0) {
                        // Found title
                        $title = substr($line, 2); // Remove "# "
                        // Limit title length to 40 characters
                        $title = strlen($title) > 40 ? substr($title, 0, 40) . '...' : $title;
                    } elseif (strpos($line, '## ') === 0) {
                        // Found duration
                        $duration = trim(substr($line, 3)); // Remove "## "
                        break; // Exit loop once duration is found
                    }
                }

                return ['title' => $title, 'duration' => $duration];
            }
        }
        return ['title' => 'No Title Found', 'duration' => ''];
    }

    // Output HTML
    foreach ($selectedDirectories as $directory) {
        $directoryName = basename($directory); // Get the directory name
        $info = getTitleAndDurationFromReadme($directory);
        $title = $info['title'];
        $duration = $info['duration'];
        $thumbnailPath = $directory . '/thumbnail.png';
        $videoLink = $baseURL . 'video.php?v=' . urlencode($directoryName); // Construct dynamic link
        echo '<div class="video-next">';
        echo '<a href="' . htmlspecialchars($videoLink) . '">';
        echo '<img src="' . htmlspecialchars($thumbnailPath) . '">';
        echo '<div class="top-right">' . htmlspecialchars($duration) . '</div>';
        echo '<h3>' . htmlspecialchars($title) . '</h3>';
        echo '</a>';
        echo '</div>';
    }
}
?>

<?php
function getBaseURL() {
    // Get the scheme (http or https)
    $scheme = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? "https" : "http";
    
    // Get the host (e.g., example.org)
    $host = $_SERVER['HTTP_HOST'];
    
    // Get the request URI (e.g., /path/that/i/want/)
    $requestURI = $_SERVER['REQUEST_URI'];
    
    // Remove the filename from the URI if it exists
    $path = preg_replace('/\/[^\/]+(\.[^\/]+)?$/', '/', $requestURI);
    
    // Construct the base URL
    $baseURL = $scheme . "://" . $host . $path;
    
    return $baseURL;
}

// Call the function and save the result in a variable
$baseURL = getBaseURL();

// Print the base URL
//echo $baseURL;
?>
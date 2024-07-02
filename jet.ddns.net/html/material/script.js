/* Show or hide .left div */
document.addEventListener('DOMContentLoaded', function() {
    var buttons = document.querySelectorAll('.toggleElements');
    buttons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent the default link behavior
            var elements = document.querySelectorAll('.left');
            elements.forEach(function(element) {
                var computedStyle = window.getComputedStyle(element);
                if (computedStyle.display === 'none') {
                    element.style.display = 'block';
                } else {
                    element.style.display = 'none';
                }
            });
        });
    });
});

/* Share button to copy the url */
document.addEventListener('DOMContentLoaded', function() {
    // Get all elements with class 'share'
    var shareLinks = document.querySelectorAll('.share');

    // Add click event listener to each share link
    shareLinks.forEach(function(shareLink) {
        shareLink.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent the default action of the link

            // Copy current URL to clipboard
            var url = window.location.href;

            // Create a temporary textarea element to copy the URL
            var textarea = document.createElement('textarea');
            textarea.value = url;
            document.body.appendChild(textarea);

            // Select and copy the URL from the textarea
            textarea.select();
            document.execCommand('copy');

            // Clean up - remove the textarea from the DOM
            document.body.removeChild(textarea);

            // Optionally, provide some visual feedback that the URL was copied
            alert('URL copied to clipboard: ' + url);
        });
    });
});

/* Change Arrow on empty page depending on width */
document.addEventListener("DOMContentLoaded", function() {
    const responsiveImage = document.getElementById('responsiveImage');
    if (responsiveImage) {
        const screenWidth = window.innerWidth;
        const path = screenWidth > (60 * 16) ? 'material/images/right.svg' : 'material/images/down.svg'; // 60rem converted to pixels (assuming 1rem = 16px)
        responsiveImage.src = path;
    }
});

// Optional: Update the image path on window resize
window.addEventListener('resize', function() {
    const responsiveImage = document.getElementById('responsiveImage');
    if (responsiveImage) {
        const screenWidth = window.innerWidth;
        const path = screenWidth > (60 * 16) ? 'material/images/right.svg' : 'material/images/down.svg'; // 60rem converted to pixels (assuming 1rem = 16px)
        responsiveImage.src = path;
    }
});
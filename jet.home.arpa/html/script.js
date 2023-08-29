// Get the theme toggle button and body element
const themeToggle = document.getElementById('themeToggle');
const body = document.body;

// Function to set the theme based on user preference
function setTheme() {
  // Check if user prefers dark mode
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  // Apply the appropriate class and update the theme toggle button text
  body.classList.toggle('dark-mode', prefersDark);
  themeToggle.textContent = prefersDark ? '🔆' : '🌒';
}

// Toggle theme when the button is clicked
themeToggle.addEventListener('click', () => {
  body.classList.toggle('light-mode');
  body.classList.toggle('dark-mode');
  // Update theme toggle button text based on the active class
  themeToggle.textContent = body.classList.contains('dark-mode') ? '🔆' : '🌒';
});

// Function to create bubbles with dynamic colors and sizes
function createBubble() {
  // Generate a random number between min and max (inclusive)
  const randomNumber = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
  
  // Define color ranges for bubbles
  const colorRanges = [
    [0, 255, 200, 255, 0, 75],    // Range for bubble type 0
    [200, 255, 0, 75, 0, 255],    // Range for bubble type 1
    [0, 75, 0, 255, 200, 255]     // Range for bubble type 2
  ];
  
  // Choose a random color range from colorRanges array
  const [minRed, maxRed, minGreen, maxGreen, minBlue, maxBlue] = colorRanges[randomNumber(0, 2)];

  // Select the section element and create a new bubble element
  const section = document.querySelector('section');
  const createElement = document.createElement('span');
  const size = Math.random() * 10; // Random size for the bubble

  // Set bubble size and position
  createElement.style.width = `${5 + size}rem`;
  createElement.style.height = `${5 + size}rem`;
  createElement.style.left = `${Math.random() * innerWidth}px`;

  // Apply a dynamic box shadow with random color values
  createElement.style.boxShadow = `inset 0 0 2rem rgba(${randomNumber(minRed, maxRed)}, ${randomNumber(minGreen, maxGreen)}, ${randomNumber(minBlue, maxBlue)}, 0.7)`;

  // Append the bubble to the section
  section.appendChild(createElement);

  // Remove the bubble after 30 seconds
  setTimeout(() => {
    createElement.remove();
  }, 30000);
}

// Initialize theme and start creating bubbles at intervals
setTheme();
setInterval(createBubble, 3000);
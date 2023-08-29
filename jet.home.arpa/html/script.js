const themeToggle = document.getElementById('themeToggle');
const body = document.body;

function setTheme() {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  body.classList.toggle('dark-mode', prefersDark);
  themeToggle.textContent = prefersDark ? '🔆' : '🌒';
}

themeToggle.addEventListener('click', () => {
  body.classList.toggle('light-mode');
  body.classList.toggle('dark-mode');
  themeToggle.textContent = body.classList.contains('dark-mode') ? '🔆' : '🌒';
});

function createBubble() {
  const randomNumber = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
  const colorRanges = [
    [0, 255, 200, 255, 0, 75],
    [200, 255, 0, 75, 0, 255],
    [0, 75, 0, 255, 200, 255]
  ];
  
  const [minRed, maxRed, minGreen, maxGreen, minBlue, maxBlue] = colorRanges[randomNumber(0, 2)];

  const section = document.querySelector('section');
  const createElement = document.createElement('span');
  const size = Math.random() * 10;

  createElement.style.width = `${5 + size}rem`;
  createElement.style.height = `${5 + size}rem`;
  createElement.style.left = `${Math.random() * innerWidth}px`;
  createElement.style.boxShadow = `inset 0 0 2rem rgba(${randomNumber(minRed, maxRed)}, ${randomNumber(minGreen, maxGreen)}, ${randomNumber(minBlue, maxBlue)}, 0.7)`;

  section.appendChild(createElement);

  setTimeout(() => {
    createElement.remove();
  }, 30000);
}

setTheme();
setInterval(createBubble, 3000);
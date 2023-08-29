const themeToggle = document.getElementById('themeToggle');
const body = document.body;

function setTheme() {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (prefersDark) {
    body.classList.add('dark-mode');
    themeToggle.textContent = '🔆';
  } else {
    body.classList.remove('dark-mode');
    themeToggle.textContent = '🌒';
  }
}

themeToggle.addEventListener('click', () => {
  body.classList.toggle('light-mode');
  body.classList.toggle('dark-mode');
  if (body.classList.contains('dark-mode')) {
    themeToggle.textContent = '🔆';
  } else {
    themeToggle.textContent = '🌒';
  }
});


function createBubble() {
  // Generate random numbers between 0 and 255
  const randomNumber = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

  // Decide randomly which number is low and which is high
  const lowIndex = randomNumber(0, 2);
  const highIndex = randomNumber(0, 2);

  let randomRed, randomGreen, randomBlue;

  if (lowIndex === 0) {
    randomRed = randomNumber(0, 255);
    randomGreen = randomNumber(200, 255);
    randomBlue = randomNumber(0, 75);
  } else if (lowIndex === 1) {
    randomRed = randomNumber(200, 255);
    randomGreen = randomNumber(0, 75);
    randomBlue = randomNumber(0, 255);
  } else {
    randomRed = randomNumber(0, 75);
    randomGreen = randomNumber(0, 255);
    randomBlue = randomNumber(200, 255);
  }

  //console.log("randomRed:", randomRed);
  //console.log("randomGreen:", randomGreen);
  //console.log("randomBlue:", randomBlue);
  // Acualy start making bubbles, everything until now is just for randome colors.
  const section = document.querySelector('section')
  const createElement = document.createElement('span')
  var size = Math.random() * 10;

  createElement.style.width = 5 + size + 'rem';
  createElement.style.height = 5 + size + 'rem';
  createElement.style.left = Math.random() * innerWidth + "px";

  createElement.style.boxShadow = `inset 0 0 2rem rgba(${randomRed}, ${randomGreen}, ${randomBlue}, 0.7)`;

  section.appendChild(createElement);

  setTimeout(() => {
    createElement.remove();
  }, 30000)
}


setTheme();
setInterval(createBubble, 3000)
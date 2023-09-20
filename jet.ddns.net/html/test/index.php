<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horizontal Image Slider</title>
    <style>
        /* Styles for the image slider container */
        .slider-container {
            width: 80%;
            margin: 0 auto;
            overflow: hidden;
        }

        /* Styles for the slider frame */
        .slider-frame {
            display: flex;
            transition: transform 0.5s ease;
        }

        /* Styles for individual slider items (images) */
        .slider-item {
            flex: 0 0 33.33%; /* Three items visible at a time */
            padding: 10px;
            box-sizing: border-box;
        }

        /* Styles for navigation buttons */
        .slider-btn {
            cursor: pointer;
            padding: 10px;
            background-color: #0074d9;
            color: #fff;
            border: none;
        }

        /* Styles for left and right buttons */
        .slider-btn-left {
            float: left;
        }

        .slider-btn-right {
            float: right;
        }
    </style>
</head>
<body>
    <div class="slider-container">
        <div class="slider-frame">
            <div class="slider-item"><img src="https://picsum.photos/300/400?random=1" alt="Image 1"></div>
            <div class="slider-item"><img src="https://picsum.photos/300/400?random=2" alt="Image 2"></div>
            <div class="slider-item"><img src="https://picsum.photos/300/400?random=3" alt="Image 3"></div>
            <div class="slider-item"><img src="https://picsum.photos/300/400?random=4" alt="Image 4"></div>
            <div class="slider-item"><img src="https://picsum.photos/300/400?random=5" alt="Image 5"></div>
            <div class="slider-item"><img src="https://picsum.photos/300/400?random=6" alt="Image 6"></div>
        </div>
    </div>

    <button class="slider-btn slider-btn-left" onclick="slideLeft()">Previous</button>
    <button class="slider-btn slider-btn-right" onclick="slideRight()">Next</button>

    <script>
        const frame = document.querySelector('.slider-frame');
        let currentIndex = 0;

        function slideLeft() {
            if (currentIndex > 0) {
                currentIndex--;
                updateSlider();
            }
        }

        function slideRight() {
            if (currentIndex < 3) { // Change this number to the total number of slides - 3
                currentIndex++;
                updateSlider();
            }
        }

        function updateSlider() {
            const translateX = -currentIndex * 33.33; // Adjust based on the number of items visible
            frame.style.transform = `translateX(${translateX}%)`;
        }
    </script>
</body>
</html>
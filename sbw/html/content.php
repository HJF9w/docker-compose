<?php
$servername = "db";
$username = "user";
$password = "pw4user";
$dbname = "sbw";
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}
$sql = "CREATE TABLE IF NOT EXISTS termine (
    id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    titel VARCHAR(255) NOT NULL,
    datum DATETIME NOT NULL,
    ort VARCHAR(255) NOT NULL,
    beschreibung TEXT NOT NULL,
    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) CHARACTER SET utf8 COLLATE utf8_general_ci";
if ($conn->query($sql) === TRUE) {} else {echo "Error creating table: " . $conn->error;}
$sql = "SELECT titel, datum, ort, beschreibung FROM termine";
$result = $conn->query($sql);
if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        $titel = htmlspecialchars(trim($row["titel"]));
        $datum = htmlspecialchars(trim($row["datum"]));
        $ort = htmlspecialchars(trim($row["ort"]));
        $beschreibung = htmlspecialchars(trim($row["beschreibung"]));
        $google_maps_link = "https://www.google.com/maps/search/" . str_replace(" ", "+", $ort);
        echo '<div class="news">
                <a href="">
                    <h3>' . $titel . '</h3>
                    <div class="left">
                    <p>' . $beschreibung . '</p>
                    </div><div class="right">
                    <p>Datum: ' . $datum . '</p>
                    <p>Ort: </p><a style="color: blue;" href="' . $google_maps_link . '">' . $ort . '</a>
                    </div>
                </a>
            </div>';
    }
} else {
    echo '<div class="news">
            <div class="left">
            <h4>Aktuell Sind keine Termine Verfügbar, bei fragen Kontaktieren sie bitte Vorname Nachname.</h4>
            </div><div class="right">
            <a href="mailto:email@example.com">E-Mail Senden</a><br>
            <a href="tel:+0123456789">Telefon: 0123456789</a>
            </div>
        </div>';
}

$conn->close();
?>

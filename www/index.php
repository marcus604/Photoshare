<!DOCTYPE html>
<html>
<title>W3.CSS Template</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Montserrat">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
<style>
body,h1 {font-family: "Montserrat", sans-serif}
img {margin-bottom: -7px}
.w3-row-padding img {margin-bottom: 12px}
</style>
<body>
<!-- 
To Do
remove all template and w3 references
properly orient portrait photos
add sidebar
add upload feature


-->
<!-- Sidebar -->
<nav class="w3-sidebar w3-black w3-animate-top w3-xxlarge" style="display:none;padding-top:150px" id="mySidebar">
  <a href="javascript:void(0)" onclick="w3_close()" class="w3-button w3-black w3-xxlarge w3-padding w3-display-topright" style="padding:6px 24px">
    <i class="fa fa-remove"></i>
  </a>
  <div class="w3-bar-block w3-center">
    <a href="#" class="w3-bar-item w3-button w3-text-grey w3-hover-black">About</a>
    <a href="#" class="w3-bar-item w3-button w3-text-grey w3-hover-black">Photos</a>
    <a href="#" class="w3-bar-item w3-button w3-text-grey w3-hover-black">Shop</a>
    <a href="#" class="w3-bar-item w3-button w3-text-grey w3-hover-black">Contact</a>
  </div>
</nav>

<!-- !PAGE CONTENT! -->
<div class="w3-content" style="max-width:1500px">

<!-- Header -->
<div class="w3-opacity">

<div class="w3-clear"></div>

</header>
</div>

<div class="test">

<!-- Connects to AWS instance of server -->
<?php
$address = '34.207.252.132';
$port = 9875;

$sock = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
$sockconnect = socket_connect($sock, $address, $port);

if ($sock === false) {
    echo "socket_create() failed: reason: " . socket_strerror(socket_last_error()) . "\n";
} else {
    echo "OK.\n";
}

$result = socket_connect($sock, $address, $port);

if ($result === false) {
    echo "socket_connect() failed.\nReason: ($result) " . socket_strerror(socket_last_error($socket)) . "\n";
} else {
    echo "OK.\n";
}

$out = socket_read($sock, 1024);

echo $out;

socket_close($sock);
?>

</div>


<!-- Photo Grid -->
<div class="w3-row-padding" id="myGrid" style="margin-bottom:128px">

  <div class="w3-third">
        <?php
        $files = glob("Library/1/*.*");
        for ($i=1; $i<count($files); $i++)
        {
            $fileName = $files[$i];
            echo '<img src="'.$fileName.'" alt="random image" style="width:100%">'."";
        }
        ?>
  </div>

  <div class="w3-third">
  <?php
        $files = glob("Library/2/*.*");
        for ($i=1; $i<count($files); $i++)
        {
            $fileName = $files[$i];
            echo '<img src="'.$fileName.'" alt="random image" style="width:100%">'."";
        }
        ?>
  </div>

  <div class="w3-third">
  <?php
        $files = glob("Library/3/*.*");
        for ($i=1; $i<count($files); $i++)
        {
            $fileName = $files[$i];
            echo '<img src="'.$fileName.'" alt="random image" style="width:100%">'."";
        }
        ?>
  </div>
</div>

<!-- End Page Content -->
</div>

<!-- Footer -->
<footer style="margin-top:128px"> 
</footer>
 
<script>

// Toggle grid padding
function myFunction() {
    var x = document.getElementById("myGrid");
    if (x.className === "w3-row") {
        x.className = "w3-row-padding";
    } else { 
        x.className = x.className.replace("w3-row-padding", "w3-row");
    }
}

// Open and close sidebar
function w3_open() {
    document.getElementById("mySidebar").style.width = "100%";
    document.getElementById("mySidebar").style.display = "block";
}

function w3_close() {
    document.getElementById("mySidebar").style.display = "none";
}
</script>

</body>
</html>

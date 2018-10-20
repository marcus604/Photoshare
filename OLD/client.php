<?php
$address = '34.227.46.96';
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
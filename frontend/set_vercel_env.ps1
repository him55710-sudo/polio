$vars = @{
    "VITE_FIREBASE_API_KEY" = "AIzaSyBhNRaQSOV2OoBJ66lJvoVWxlYOOxgugsE"
    "VITE_FIREBASE_AUTH_DOMAIN" = "folia-e206f.firebaseapp.com"
    "VITE_FIREBASE_PROJECT_ID" = "folia-e206f"
    "VITE_FIREBASE_STORAGE_BUCKET" = "folia-e206f.firebasestorage.app"
    "VITE_FIREBASE_MESSAGING_SENDER_ID" = "707518199279"
    "VITE_FIREBASE_APP_ID" = "1:707518199279:web:f87990c747ad7e9efa321a"
    "VITE_FIREBASE_MEASUREMENT_ID" = "G-L3P7FF0K86"
}

foreach ($name in $vars.Keys) {
    $value = $vars[$name]
    Write-Host "Setting $name..."
    $value | npx vercel env add $name production
}

#include <Arduino.h>

// Pin LED bawaan pada ESP32-S3-DevKitC-1
// Ganti dengan pin yang sesuai jika Anda menggunakan board lain
const int LED_PIN = 43; 

// --- Fungsi Setup ---

void setup() {
  // Inisialisasi komunikasi serial pada baud rate 115200
  Serial.begin(115200);
  
  // Konfigurasi pin LED sebagai OUTPUT
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // Pastikan LED mati saat memulai
}

// --- Loop Utama ---

void loop() {
  // Cek apakah ada data yang tersedia di Serial Port
  if (Serial.available() > 0) {
    // Baca byte data yang dikirimkan
    char incomingByte = Serial.read();

    // Jika karakter yang diterima adalah 'F' (Face Detected)
    if (incomingByte == 'N') {
      digitalWrite(LED_PIN, HIGH); // Nyalakan LED
      Serial.println("LED menyala");
    } 
    // Jika karakter yang diterima adalah 'N' (No Face)
    else if (incomingByte == 'F') {
      digitalWrite(LED_PIN, LOW); // Matikan LED
      Serial.println("LED mati");
    }
  }

  // Tunda sebentar untuk menghindari pembacaan yang terlalu cepat
  delay(10);
}

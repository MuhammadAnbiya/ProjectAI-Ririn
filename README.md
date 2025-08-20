ProjectAI-Ririn
Pendahuluan
Proyek ini adalah sistem deteksi wajah sederhana menggunakan kombinasi Python, OpenCV, dan ESP32-S3. Tujuannya adalah untuk mendeteksi wajah melalui webcam laptop dan mengirimkan sinyal ke ESP32-S3 untuk mengontrol LED. Ketika wajah terdeteksi, LED akan menyala, dan ketika wajah tidak terdeteksi, LED akan mati.

Fitur
Deteksi Wajah: Menggunakan model haarcascade_frontalface_default.xml dari OpenCV untuk mendeteksi wajah secara real-time.

Komunikasi Serial: Menggunakan kabel USB untuk komunikasi langsung antara laptop dan ESP32, tanpa memerlukan konfigurasi jaringan yang rumit.

Kontrol LED: Menyalakan atau mematikan LED di ESP32 berdasarkan status deteksi wajah.

Sederhana dan Ringan: Kode difokuskan pada fungsionalitas inti, membuatnya mudah dipahami dan efisien.

Persyaratan Sistem
Perangkat Keras
Laptop dengan webcam

Board ESP32-S3-DevKitC-1

Kabel USB

Perangkat Lunak
Arduino IDE: Untuk mengunggah kode ke ESP32.

Python 3.x: Untuk menjalankan skrip deteksi wajah.

Pustaka Python:

opencv-python

pyserial

Panduan Instalasi dan Penggunaan
1. Persiapan Arduino
Buka Arduino IDE. Pastikan Anda telah menginstal board ESP32.

Salin dan tempel kode arduino.ino (atau nama file yang Anda simpan) ke Arduino IDE.

Pilih board ESP32S3 Dev Module dan port yang sesuai.

Unggah kode ke ESP32 Anda.

2. Persiapan Python
Navigasi ke direktori proyek Anda di terminal.

Instal pustaka Python yang diperlukan menggunakan pip:

pip install opencv-python pyserial

Buka file python_face_detector.py dan sesuaikan variabel berikut:

SERIAL_PORT: Ganti dengan port serial yang benar dari ESP32 Anda (contoh: COM3 di Windows, /dev/ttyACM0 di Linux, /dev/cu.usbmodemXXXX di macOS).

WEBCAM_INDEX: Ganti dengan indeks webcam yang benar. Biasanya 0 untuk webcam bawaan.

3. Menjalankan Proyek
Pastikan ESP32 terhubung ke laptop Anda.

Jalankan skrip Python dari terminal:

python python_face_detector.py

Sebuah jendela akan muncul menampilkan video dari webcam Anda.

Ketika wajah terdeteksi di dalam bingkai, LED di ESP32 akan menyala. Ketika wajah hilang, LED akan mati. Untuk menghentikan program, tekan tombol q pada keyboard.

File Proyek
arduino.ino: Kode untuk ESP32 yang menerima sinyal serial.

python_face_detector.py: Skrip Python yang mendeteksi wajah dan mengirim sinyal.

haarcascade_frontalface_default.xml: File model untuk deteksi wajah.

.gitignore: Mengabaikan file dan folder yang tidak diperlukan seperti venv/ dan __pycache__/.

Kontribusi
Jika Anda memiliki ide untuk perbaikan atau fitur baru, silakan ajukan pull request atau issue di repositori ini.

import cv2
import serial
import time

# --- Pengaturan Proyek ---
# Atur port serial yang terhubung ke ESP32 Anda.
# Contoh: 'COM3' di Windows, '/dev/ttyACM0' di Linux, atau '/dev/cu.usbmodemXXXX' di macOS.
SERIAL_PORT = '/dev/ttyACM0' 
BAUDRATE = 115200

# Atur indeks untuk webcam Anda.
# Coba ganti angkanya (0, 1, 2, dst.) jika webcam tidak terdeteksi.
WEBCAM_INDEX = 4

# Waktu jeda antara pengiriman sinyal (dalam detik)
# Ini penting untuk mencegah data dikirim terlalu cepat.
SIGNAL_DELAY = 0.5 

# --- Inisialisasi Perangkat ---
# Hubungkan ke ESP32 melalui port serial yang sudah ditentukan.
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    print(f"[INFO] Terhubung ke ESP32 di {SERIAL_PORT}")
    time.sleep(2) # Beri waktu sejenak agar koneksi serial siap
except serial.SerialException as e:
    print(f"[ERROR] Gagal terhubung ke ESP32: {e}")
    ser = None
    
# Nyalakan webcam.
cap = cv2.VideoCapture(WEBCAM_INDEX)
if not cap.isOpened():
    print("[ERROR] Tidak bisa membuka kamera. Pastikan webcam terhubung atau ganti indeks.")
    exit()

# Muat model deteksi wajah dari OpenCV.
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Variabel untuk melacak status dan waktu.
last_signal_time = 0
face_was_detected = False

# --- Fungsi Bantuan ---
def send_signal(signal):
    """
    Mengirim sinyal (satu karakter) ke ESP32 melalui kabel.
    Sinyal:
    - 'F' untuk Wajah Terdeteksi
    - 'N' untuk Tidak Ada Wajah
    """
    global last_signal_time
    # Kirim sinyal hanya jika sudah lewat waktu jeda.
    if time.time() - last_signal_time > SIGNAL_DELAY:
        if ser and ser.is_open:
            try:
                ser.write(signal.encode())
                print(f"[INFO] Sinyal '{signal}' berhasil dikirim.")
            except Exception as e:
                print(f"[ERROR] Gagal mengirim sinyal serial: {e}")
        last_signal_time = time.time()

# --- Program Utama ---
print("[INFO] Program dimulai. Tekan 'q' untuk keluar.")

while True:
    # Ambil satu bingkai (frame) dari webcam.
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Tidak bisa membaca bingkai dari kamera.")
        break

    # Ubah warna bingkai ke skala abu-abu untuk deteksi yang lebih cepat.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Deteksi wajah di dalam bingkai.
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    # Gambar kotak biru di sekeliling wajah yang terdeteksi.
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # Logika sederhana untuk mengontrol LED di ESP32.
    # Jika wajah terdeteksi dan status berubah, kirim sinyal 'F'.
    if len(faces) > 0 and not face_was_detected:
        send_signal('F')
        face_was_detected = True
    # Jika tidak ada wajah dan status berubah, kirim sinyal 'N'.
    elif len(faces) == 0 and face_was_detected:
        send_signal('N')
        face_was_detected = False

    # Tampilkan video hasil deteksi.
    cv2.imshow("Face Detection", frame)
    
    # Keluar dari program jika tombol 'q' ditekan.
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Akhir Program ---
print("[INFO] Menghentikan program...")
cap.release()
cv2.destroyAllWindows()
if ser and ser.is_open:
    ser.close()
    print("[INFO] Koneksi serial ditutup.")

import cv2
import serial
import time

# --- Pengaturan ---
# Ganti dengan port serial yang terhubung ke ESP32 Anda
# Contoh: 'COM3' di Windows, '/dev/ttyACM0' di Linux, '/dev/cu.usbmodemXXXX' di macOS
SERIAL_PORT = '/dev/ttyACM0' 
BAUDRATE = 115200

# Ganti index ke webcam Anda. Coba 0, 1, 2, dst.
WEBCAM_INDEX = 4

# Waktu tunda antara pengiriman sinyal (dalam detik)
# Ini mencegah pengiriman data yang terlalu cepat
SIGNAL_DELAY = 0.5 

# --- Inisialisasi ---
# Inisialisasi koneksi serial ke ESP32
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    print(f"[INFO] Terhubung ke ESP32 di {SERIAL_PORT}")
    time.sleep(2) # Beri waktu untuk koneksi serial stabil
except serial.SerialException as e:
    print(f"[ERROR] Gagal terhubung ke ESP32: {e}")
    ser = None
    
# Inisialisasi kamera
cap = cv2.VideoCapture(WEBCAM_INDEX)
if not cap.isOpened():
    print("[ERROR] Tidak bisa membuka kamera. Periksa indeks webcam atau driver kamera.")
    exit()

# Load Haar Cascade untuk deteksi wajah
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Variabel untuk melacak waktu dan status
last_signal_time = 0
face_was_detected = False

# --- Fungsi untuk Mengirim Sinyal Serial ---
def send_signal(signal):
    """
    Mengirim sinyal (satu karakter) melalui koneksi serial.
    Parameters:
    - signal (str): 'F' (Face Detected) atau 'N' (No Face)
    """
    global last_signal_time
    # Hanya kirim sinyal jika sudah melewati waktu tunda
    if time.time() - last_signal_time > SIGNAL_DELAY:
        if ser and ser.is_open:
            try:
                ser.write(signal.encode())
                print(f"[INFO] Sinyal '{signal}' berhasil dikirim.")
            except Exception as e:
                print(f"[ERROR] Gagal mengirim sinyal serial: {e}")
        last_signal_time = time.time()

# --- Loop Utama untuk Deteksi Wajah ---
print("[INFO] Mulai deteksi wajah. Tekan 'q' untuk keluar.")

while True:
    # Baca satu frame dari kamera
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Tidak bisa membaca frame dari kamera.")
        break

    # Konversi frame ke grayscale untuk deteksi
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Lakukan deteksi wajah
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    # Gambar kotak di sekitar wajah yang terdeteksi untuk visualisasi
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # Logika untuk mengontrol LED berdasarkan deteksi wajah
    # Jika wajah terdeteksi dan statusnya berubah, kirim sinyal 'F'
    if len(faces) > 0 and not face_was_detected:
        send_signal('F')
        face_was_detected = True
    # Jika tidak ada wajah dan statusnya berubah, kirim sinyal 'N'
    elif len(faces) == 0 and face_was_detected:
        send_signal('N')
        face_was_detected = False

    # Tampilkan frame di jendela
    cv2.imshow("Face Detection", frame)
    
    # Hentikan loop jika tombol 'q' ditekan
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Pembersihan ---
print("[INFO] Menghentikan program...")
cap.release()
cv2.destroyAllWindows()
if ser and ser.is_open:
    ser.close()
    print("[INFO] Koneksi serial ditutup.")

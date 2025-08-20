import cv2
import serial
import time
import os
import datetime
from threading import Thread
from queue import Queue
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# --- Project Configuration ---
# Set the serial port for your ESP32.
# Example: 'COM3' on Windows, '/dev/ttyACM0' on Linux, or '/dev/cu.usbmodemXXXX' on macOS
SERIAL_PORT = '/dev/ttyACM0'
BAUDRATE = 115200

# Set the index for your webcam.
# Try changing the number (0, 1, 2, etc.) if your webcam is not detected.
WEBCAM_INDEX = 4

# The time delay between sending signals (in seconds).
# This prevents data from being sent too quickly.
SIGNAL_DELAY = 0.5

# The directory to temporarily store captured photos before uploading.
TEMP_SAVE_DIR = "captured_temp"
os.makedirs(TEMP_SAVE_DIR, exist_ok=True)

# Google Drive folder ID to upload files to.
# You can find this in the folder's URL.
GOOGLE_DRIVE_FOLDER_ID = '1Wu3dpllw4w8KvCQ7OxenG2MZwIqpD790'

# --- Initialization of Devices ---
# Initialize serial connection to the ESP32.
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    print(f"[INFO] Connected to ESP32 on {SERIAL_PORT}")
    time.sleep(2)  # Give some time for the serial connection to stabilize
except serial.SerialException as e:
    print(f"[ERROR] Failed to connect to ESP32: {e}")
    ser = None

# Initialize the webcam.
cap = cv2.VideoCapture(WEBCAM_INDEX)
if not cap.isOpened():
    print("[ERROR] Failed to open the camera. Please check the webcam index or its drivers.")
    exit()

# Load the face detection model from OpenCV.
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Variables to track status and time.
last_signal_time = 0
face_was_detected = False

# Queue for asynchronous uploads.
upload_queue = Queue()

# --- Google Drive Setup with PyDrive ---
def setup_drive():
    """
    Sets up and authenticates with Google Drive using PyDrive.
    It will handle browser-based authentication on the first run.
    """
    gauth = GoogleAuth()
    
    # Konfigurasi Pydrive untuk menggunakan file credentials.json
    gauth.settings['client_config_file'] = 'credentials.json'

    # Coba load saved credentials dari file lokal.
    gauth.LoadCredentialsFile("mycreds.txt")

    if gauth.credentials is None:
        # Autentikasi jika kredensial tidak ditemukan.
        print("[INFO] First-time login. A browser will open for authentication...")
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Perbarui token akses jika sudah kedaluwarsa.
        gauth.Refresh()
    else:
        # Otorisasi menggunakan kredensial yang ada.
        gauth.Authorize()

    # Simpan kredensial ke file untuk penggunaan di masa depan.
    gauth.SaveCredentialsFile("mycreds.txt")

    return GoogleDrive(gauth)

# --- Upload Worker Function ---
def upload_worker(queue, drive):
    """
    A worker thread that takes file paths from a queue and uploads them to Google Drive.
    """
    while True:
        filepath = queue.get()
        if filepath is None:  # Sinyal untuk menghentikan worker.
            break
            
        print(f"[INFO] Starting upload process for file: {os.path.basename(filepath)}")
        try:
            # Buat objek file Google Drive.
            gdrive_file = drive.CreateFile({
                'title': os.path.basename(filepath),
                'parents': [{'id': GOOGLE_DRIVE_FOLDER_ID}]
            })
            # Atur konten file dan unggah.
            gdrive_file.SetContentFile(filepath)
            gdrive_file.Upload()
            
            print(f"✅ Upload successful: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"[ERROR] Failed to upload: {e}")
        finally:
            # Hapus file lokal setelah diunggah.
            if os.path.exists(filepath):
                os.remove(filepath)
            # Beri tahu antrean bahwa tugas telah selesai.
            queue.task_done()

# --- Helper Function for Serial Communication ---
def send_signal(signal):
    """
    Sends a signal (a single character) via the serial connection to the ESP32.
    - 'F' for Face Detected
    - 'N' for No Face
    """
    global last_signal_time
    # Hanya kirim sinyal jika waktu tunda sudah berlalu.
    if time.time() - last_signal_time > SIGNAL_DELAY:
        if ser and ser.is_open:
            try:
                ser.write(signal.encode())
                print(f"[INFO] Signal '{signal}' successfully sent.")
            except Exception as e:
                print(f"[ERROR] Failed to send serial signal: {e}")
        last_signal_time = time.time()

# --- Main Program ---
print("[INFO] Program started. Press 'q' to exit.")

# Google Drive setup
gdrive_service = setup_drive()
# Start the upload worker thread.
Thread(target=upload_worker, args=(upload_queue, gdrive_service), daemon=True).start()

last_capture_time = 0
CAPTURE_INTERVAL = 5  # Waktu tunda antara pengambilan foto (dalam detik)

while True:
    # Tangkap satu bingkai dari webcam.
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to read frame from the camera.")
        break

    # Ubah bingkai ke skala abu-abu untuk deteksi yang lebih cepat.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Deteksi wajah di dalam bingkai.
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    # Gambar kotak biru di sekitar wajah yang terdeteksi.
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # Logika untuk mengontrol LED ESP32 dan mengambil foto.
    if len(faces) > 0:
        # Jika wajah terdeteksi dan statusnya berubah, kirim sinyal 'F'.
        if not face_was_detected:
            send_signal('F')
            face_was_detected = True
        
        # Ambil foto jika sudah waktunya.
        if time.time() - last_capture_time > CAPTURE_INTERVAL:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"face_{timestamp}.jpg"
            filepath = os.path.join(TEMP_SAVE_DIR, filename)
            cv2.imwrite(filepath, frame.copy())
            print(f"[INFO] Foto diambil: {filepath}")
            # Masukkan jalur foto ke antrean untuk diunggah.
            upload_queue.put(filepath)
            last_capture_time = time.time()
    else:
        # Jika tidak ada wajah dan statusnya berubah, kirim sinyal 'N'.
        if face_was_detected:
            send_signal('N')
            face_was_detected = False

    # Tampilkan hasilnya.
    cv2.imshow("Face Detection", frame)
    
    # Keluar dari program jika tombol 'q' ditekan.
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Akhir Program ---
print("[INFO] Mematikan program...")
# Sinyal untuk menghentikan worker.
upload_queue.put(None)
upload_queue.join()
cap.release()
cv2.destroyAllWindows()
if ser and ser.is_open:
    ser.close()
    print("[INFO] Koneksi serial ditutup.")

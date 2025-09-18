/*********************************************************************************
 * ESP32-CAM Face Detection and Save to SD Card Project AI Takana Juo
 *********************************************************************************/

// Required libraries
#include "esp_camera.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "fb_gfx.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "driver/ledc.h"
#include <WiFi.h>
#include "SD_MMC.h"
#include "FS.h"
#include <vector>
#include <list>

// Libraries for face detection
#include "human_face_detect_msr01.hpp"
#include "human_face_detect_mnp01.hpp"

// --- CONFIGURATION ---
const char* ssid = "TakanaJuoCibolang";
const char* password = "rendangnyajuara";

// Kamera & Kualitas
#define STREAM_FRAME_SIZE FRAMESIZE_VGA
#define STREAM_JPEG_QUALITY 15
#define SAVE_COOLDOWN_SECONDS 5

// Efisiensi
#define DETECTION_INTERVAL 5

// Warna untuk kotak deteksi
#define FACE_COLOR_GREEN 0x0000FF00

// --- Pengaturan IP Statis ---
IPAddress static_IP(192, 168, 1, 151);
IPAddress gateway_IP(192, 168, 1, 1);
IPAddress subnet_IP(255, 255, 255, 0);

// --- Pinout untuk AI-THINKER model ---
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define FLASH_GPIO_NUM     4

// Global variables
static int face_detect_enabled = 1;
static int save_to_sd_enabled = 1;
static int photo_count = 0;
static unsigned long last_save_time = 0;
static long frame_counter = 0;

// Initialize face detection models
static HumanFaceDetectMSR01 s1(0.1F, 0.5F, 10, 0.2F);
static HumanFaceDetectMNP01 s2(0.5F, 0.3F, 5);

// Function to draw boxes around faces
static void draw_face_boxes(fb_data_t *fb, std::list<dl::detect::result_t> *results) {
    int x, y, w, h;
    uint32_t color = FACE_COLOR_GREEN;
    if (fb->bytes_per_pixel == 2) {
        color = ((color >> 16) & 0x001F) | ((color >> 3) & 0x07E0) | ((color << 8) & 0xF800);
    }
    for (auto const& prediction : *results) {
        x = (int)prediction.box[0];
        y = (int)prediction.box[1];
        w = (int)prediction.box[2] - x + 1;
        h = (int)prediction.box[3] - y + 1;
        fb_gfx_drawFastHLine(fb, x, y, w, color);
        fb_gfx_drawFastHLine(fb, x, y + h - 1, w, color);
        fb_gfx_drawFastVLine(fb, x, y, h, color);
        fb_gfx_drawFastVLine(fb, x + w - 1, y, h, color);
    }
}

void saveJpgToSD(const uint8_t *jpg_buf, size_t jpg_buf_len) {
  if (!jpg_buf || jpg_buf_len == 0) {
    Serial.println("JPEG buffer for saving is invalid.");
    return;
  }
  
  digitalWrite(FLASH_GPIO_NUM, LOW); // LED indicator off while saving

  String path = "/face_capture_" + String(photo_count) + ".jpg";
  fs::FS &fs = SD_MMC;
  File file = fs.open(path.c_str(), FILE_WRITE);

  if (!file) {
    Serial.printf("Failed to open file %s for writing\n", path.c_str());
  } else {
    file.write(jpg_buf, jpg_buf_len);
    Serial.printf("Photo saved: %s (%u bytes)\n", path.c_str(), jpg_buf_len);
    photo_count++;
  }
  file.close();
}

static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t *_jpg_buf = NULL;
  char *part_buf[128];
  bool should_save_photo = false;

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=123456789000000000000987654321");
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    should_save_photo = false; // Reset flag for each frame
    fb = esp_camera_fb_get();
    
    if (!fb) {
      Serial.println("Failed to get frame");
      res = ESP_FAIL;
    } else {
      frame_counter++;
      // Perform face detection only every N frames for efficiency
      if (face_detect_enabled && fb->format == PIXFORMAT_RGB565 && (frame_counter % DETECTION_INTERVAL == 0)) {
          std::list<dl::detect::result_t> &candidates = s1.infer((uint16_t *)fb->buf, {(int)fb->height, (int)fb->width, 3});
          std::list<dl::detect::result_t> &results = s2.infer((uint16_t *)fb->buf, {(int)fb->height, (int)fb->width, 3}, candidates);
          
          if (!results.empty()) {
            // If a face is detected, draw a box
            fb_data_t rfb;
            rfb.width = fb->width; rfb.height = fb->height; rfb.data = fb->buf;
            rfb.bytes_per_pixel = 2; rfb.format = FB_RGB565;
            draw_face_boxes(&rfb, &results);

            // Check if it's time to save a photo again
            if (save_to_sd_enabled && (millis() - last_save_time > SAVE_COOLDOWN_SECONDS * 1000)) {
               last_save_time = millis();
               should_save_photo = true; // Flag that a photo should be saved
            }
          }
      }
      
      // JPEG conversion is done ONLY ONCE here.
      if (!fmt2jpg(fb->buf, fb->len, fb->width, fb->height, PIXFORMAT_RGB565, STREAM_JPEG_QUALITY, &_jpg_buf, &_jpg_buf_len)) {
        Serial.println("JPEG conversion failed");
        res = ESP_FAIL;
      }
      
      // Return the frame buffer as soon as possible after use
      esp_camera_fb_return(fb);
      fb = NULL;
      
      // If flagged for saving, call the save function with the ready-made JPEG buffer
      if (should_save_photo && res == ESP_OK) {
        saveJpgToSD(_jpg_buf, _jpg_buf_len);
      }
    }

    // Send the JPEG buffer to the client (streaming)
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)"\r\n--123456789000000000000987654321\r\n", 38);
      if (res == ESP_OK) {
        size_t hlen = snprintf((char *)part_buf, 128, "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", _jpg_buf_len);
        res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
      }
      if (res == ESP_OK) {
        res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
      }
    }

    // Free the JPEG buffer memory
    if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }

    // If an error occurred, break the loop
    if (res != ESP_OK) break;
  }
  return res;
}

// Handler untuk Access Point
static esp_err_t index_handler(httpd_req_t *req){
  httpd_resp_set_type(req, "text/html");
  String ip = WiFi.localIP().toString();
  int last_dot = ip.lastIndexOf('.');
  String last_part = ip.substring(last_dot + 1);
  String html = "<html><head><title>ESP CAM Takana Juo - " + last_part + "</title><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><style>body{font-family: Arial, sans-serif; text-align: center; margin: 20px; background-color: #CC3322;}h1{color: #FFED00;}#stream-container{border: 2px solid #FFED00; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.2); max-width: 95%;}img{max-width: 100%; height: auto; display: block;}p{font-weight: bold; color: #FFED00;}</style></head><body><h1>Dashboard ESP CAM Takana Juo - " + last_part + "</h1><div id=\"stream-container\"><img src=\"/stream\"></div><p>When a face is detected, a photo will be saved to the SD Card.</p><p>Photo quality: 640x480 (same as stream)</p></body></html>";
  return httpd_resp_send(req, html.c_str(), html.length());
}

// Function to start the server (no changes)
void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.stack_size = 8192;
  httpd_handle_t server = NULL;
  httpd_uri_t index_uri = { "/", HTTP_GET, index_handler, NULL };
  httpd_uri_t stream_uri = { "/stream", HTTP_GET, stream_handler, NULL };
  if (httpd_start(&server, &config) == ESP_OK) {
    httpd_register_uri_handler(server, &index_uri);
    httpd_register_uri_handler(server, &stream_uri);
  }
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println("\n--- ESP32-CAM Face Detect & Save (VGA Efficient) ---");

  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW);

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM; config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM; config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM; config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM; config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM; config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  
  config.pixel_format = PIXFORMAT_RGB565;
  config.frame_size = STREAM_FRAME_SIZE;
  
  config.jpeg_quality = STREAM_JPEG_QUALITY;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error: 0x%x", err);
    ESP.restart();
  }
  Serial.println("Camera initialized successfully");

  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, 1);     
  s->set_hmirror(s, 0);   

  if (!SD_MMC.begin()) {
    Serial.println("Failed to mount SD Card.");
    save_to_sd_enabled = 0;
  } else {
    Serial.println("SD Card initialized successfully.");
    
    photo_count = 0;
    while (true) {
      String path = "/face_capture_" + String(photo_count) + ".jpg";
      if (!SD_MMC.exists(path)) {
        break; 
      }
      photo_count++;
    }
    Serial.printf("Photo saving will start from: face_capture_%d.jpg\n", photo_count);
  }
  
  if (!WiFi.config(static_IP, gateway_IP, subnet_IP)) {
    Serial.println("Failed to configure static IP");
  }

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  startCameraServer();
  Serial.println("Camera server started.");
  Serial.printf("Open browser to: http://%s\n", WiFi.localIP().toString().c_str());
}

void loop() {
  delay(10000);
}
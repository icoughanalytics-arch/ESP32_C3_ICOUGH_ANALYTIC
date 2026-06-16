#include "wifi_module.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <FS.h>
#include <LittleFS.h>


void wifi_init() {
    WiFi.mode(WIFI_STA);
}

void wifi_connect() {
    if (wifi_is_connected()) return;
    if (strlen(WIFI_SSID) == 0) {
        Serial.println("[WIFI] WIFI_SSID is empty");
        return;
    }

    Serial.printf("[WIFI] Connecting to %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long start_ms = millis();
    while (!wifi_is_connected() && millis() - start_ms < WIFI_CONNECT_TIMEOUT_MS) {
        delay(250);
        Serial.print(".");
    }
    Serial.println();

    if (wifi_is_connected()) {
        Serial.print("[WIFI] Connected IP=");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("[WIFI] Connect timeout");
    }
}

void wifi_disconnect() {
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
}

bool wifi_is_connected() {
    return WiFi.status() == WL_CONNECTED;
}

void wifi_upload_files() {
}

bool wifi_upload_audio_wav(const char* filename, const uint8_t* data, size_t size) {
    if (!filename || !data || size == 0) {
        Serial.println("[HTTP] Invalid upload payload");
        return false;
    }

    Serial.printf("[HTTP] Upload start file=%s bytes=%u\n", filename, (unsigned int)size);
    if (!wifi_is_connected()) wifi_connect();
    if (!wifi_is_connected()) {
        Serial.println("[HTTP] Upload stopped: Wi-Fi not connected");
        return false;
    }

    // ใช้ WiFiClientSecure สำหรับ HTTPS (ngrok)
    WiFiClientSecure client;
    client.setInsecure();  // skip certificate verification สำหรับ ngrok

    Serial.printf("[HTTP] Connecting to %s:%u%s (HTTPS)\n", SERVER_HOST, SERVER_PORT, SERVER_UPLOAD_PATH);
    if (!client.connect(SERVER_HOST, SERVER_PORT)) {
        Serial.println("[HTTP] Server connect failed");
        return false;
    }
    Serial.println("[HTTP] Server connected (TLS)");

    const char* boundary = "----icough-boundary";
    String head =
        String("--") + boundary + "\r\n"
        "Content-Disposition: form-data; name=\"file\"; filename=\"" + filename + "\"\r\n"
        "Content-Type: audio/wav\r\n\r\n";
    String tail = String("\r\n--") + boundary + "--\r\n";
    size_t content_length = head.length() + size + tail.length();

    Serial.printf("[HTTP] content_length=%u head=%u body=%u tail=%u\n",
                  (unsigned int)content_length,
                  (unsigned int)head.length(),
                  (unsigned int)size,
                  (unsigned int)tail.length());

    client.printf("POST %s HTTP/1.1\r\n", SERVER_UPLOAD_PATH);
    client.printf("Host: %s\r\n", SERVER_HOST);
    client.println("Connection: close");
    client.printf("Content-Type: multipart/form-data; boundary=%s\r\n", boundary);
    client.printf("Content-Length: %u\r\n\r\n", (unsigned int)content_length);
    size_t sent_head = client.print(head);
    size_t sent_body = 0;
    const size_t chunk_size = 1024;
    while (sent_body < size && client.connected()) {
        size_t remaining = size - sent_body;
        size_t to_send = remaining > chunk_size ? chunk_size : remaining;
        size_t sent_now = client.write(data + sent_body, to_send);
        if (sent_now == 0) {
            delay(10);
            continue;
        }
        sent_body += sent_now;
    }
    size_t sent_tail = client.print(tail);
    Serial.printf("[HTTP] sent head=%u body=%u tail=%u\n",
                  (unsigned int)sent_head,
                  (unsigned int)sent_body,
                  (unsigned int)sent_tail);

    if (sent_body != size) {
        Serial.println("[HTTP] Body send incomplete");
        client.stop();
        return false;
    }

    unsigned long start_ms = millis();
    while (client.connected() && !client.available() && millis() - start_ms < HTTP_RESPONSE_TIMEOUT_MS) {
        delay(10);
    }

    if (!client.available()) {
        Serial.printf("[HTTP] No response timeout connected=%d\n", client.connected() ? 1 : 0);
        client.stop();
        return false;
    }

    String status_line = client.readStringUntil('\n');
    bool ok = status_line.indexOf("200") >= 0;
    status_line.trim();
    Serial.print("[HTTP] status=");
    Serial.println(status_line);

    String response_body = "";
    unsigned long read_start_ms = millis();
    while (client.available() && millis() - read_start_ms < 2000) {
        response_body += client.readString();
    }
    response_body.trim();
    if (response_body.length() > 0) {
        Serial.print("[HTTP] response=");
        Serial.println(response_body);
    }

    client.stop();
    return ok;
}

bool wifi_upload_audio_wav_from_file(const char* filepath) {
    if (!filepath) {
        Serial.println("[HTTP] Invalid filepath");
        return false;
    }

    // เปิดไฟล์จาก LittleFS
    String path = filepath;
    if (!path.startsWith("/")) {
        path = "/" + path;
    }

    File file = LittleFS.open(path, FILE_READ);
    if (!file) {
        Serial.printf("[HTTP] Failed to open file %s for upload\n", path.c_str());
        return false;
    }

    size_t size = file.size();
    if (size == 0) {
        Serial.println("[HTTP] File is empty");
        file.close();
        return false;
    }

    // เอาเฉพาะชื่อไฟล์ในการส่ง header
    String filename = path;
    int slash_idx = filename.lastIndexOf('/');
    if (slash_idx >= 0) {
        filename = filename.substring(slash_idx + 1);
    }

    Serial.printf("[HTTP] Upload start file=%s bytes=%u (from LittleFS)\n", filename.c_str(), (unsigned int)size);
    if (!wifi_is_connected()) wifi_connect();
    if (!wifi_is_connected()) {
        Serial.println("[HTTP] Upload stopped: Wi-Fi not connected");
        file.close();
        return false;
    }

    // ใช้ WiFiClientSecure
    WiFiClientSecure client;
    client.setInsecure();  // skip certificate verification

    Serial.printf("[HTTP] Connecting to %s:%u%s (HTTPS)\n", SERVER_HOST, SERVER_PORT, SERVER_UPLOAD_PATH);
    if (!client.connect(SERVER_HOST, SERVER_PORT)) {
        Serial.println("[HTTP] Server connect failed");
        file.close();
        return false;
    }
    Serial.println("[HTTP] Server connected (TLS)");

    const char* boundary = "----icough-boundary";
    String head =
        String("--") + boundary + "\r\n"
        "Content-Disposition: form-data; name=\"file\"; filename=\"" + filename + "\"\r\n"
        "Content-Type: audio/wav\r\n\r\n";
    String tail = String("\r\n--") + boundary + "--\r\n";
    size_t content_length = head.length() + size + tail.length();

    client.printf("POST %s HTTP/1.1\r\n", SERVER_UPLOAD_PATH);
    client.printf("Host: %s\r\n", SERVER_HOST);
    client.println("Connection: close");
    client.printf("Content-Type: multipart/form-data; boundary=%s\r\n", boundary);
    client.printf("Content-Length: %u\r\n\r\n", (unsigned int)content_length);

    size_t sent_head = client.print(head);
    size_t sent_body = 0;
    
    // อ่านและส่งในรูป chunks ของ 1024-byte
    uint8_t buffer[1024];
    while (file.available() && client.connected()) {
        int read_len = file.read(buffer, sizeof(buffer));
        if (read_len <= 0) break;

        size_t sent_now = client.write(buffer, read_len);
        sent_body += sent_now;
        if (sent_now != read_len) {
            Serial.println("[HTTP] Write to TLS socket failed");
            break;
        }
    }
    file.close();

    size_t sent_tail = client.print(tail);
    Serial.printf("[HTTP] sent head=%u body=%u tail=%u\n",
                  (unsigned int)sent_head,
                  (unsigned int)sent_body,
                  (unsigned int)sent_tail);

    if (sent_body != size) {
        Serial.println("[HTTP] Body send incomplete");
        client.stop();
        return false;
    }

    unsigned long start_ms = millis();
    while (client.connected() && !client.available() && millis() - start_ms < HTTP_RESPONSE_TIMEOUT_MS) {
        delay(10);
    }

    if (!client.available()) {
        Serial.printf("[HTTP] No response timeout connected=%d\n", client.connected() ? 1 : 0);
        client.stop();
        return false;
    }

    String status_line = client.readStringUntil('\n');
    bool ok = status_line.indexOf("200") >= 0;
    status_line.trim();
    Serial.print("[HTTP] status=");
    Serial.println(status_line);

    String response_body = "";
    unsigned long read_start_ms = millis();
    while (client.available() && millis() - read_start_ms < 2000) {
        response_body += client.readString();
    }
    response_body.trim();
    if (response_body.length() > 0) {
        Serial.print("[HTTP] response=");
        Serial.println(response_body);
    }

    client.stop();
    return ok;
}


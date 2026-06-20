#include "wifi_config_module.h"
#include "wifi_module.h"
#include "test_mode_module.h" // สำหรับ TEST_LED_PIN
#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>

static DNSServer dnsServer;
static WebServer server(80);

static bool config_active = false;
static unsigned long config_start_ms = 0;
static const unsigned long CONFIG_TIMEOUT_MS = 120000; // 2 นาที
static unsigned long last_blink_ms = 0;
static bool led_state = false;
static bool should_reboot = false;
static unsigned long reboot_timer_ms = 0;

// หน้า HTML สไตล์โมเดิร์น
const char HTML_INDEX[] PROGMEM = R"rawhtml(
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <title>iCough Wi-Fi Setup</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .container {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        h2 {
            margin-top: 0;
            color: #38bdf8;
            font-size: 24px;
        }
        p {
            color: #94a3b8;
            font-size: 14px;
            margin-bottom: 24px;
        }
        .form-group {
            text-align: left;
            margin-bottom: 16px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #334155;
            background-color: #0f172a;
            color: #f8fafc;
            font-size: 16px;
            box-sizing: border-box;
            outline: none;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            border-color: #38bdf8;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #0284c7, #0369a1);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
            margin-top: 10px;
        }
        button:hover {
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>iCough Setup</h2>
        <p>เชื่อมต่ออุปกรณ์เข้ากับ Wi-Fi เครือข่ายของคุณ</p>
        <form action="/save" method="POST">
            <div class="form-group">
                <label>Wi-Fi Name (SSID)</label>
                <input type="text" name="ssid" placeholder="กรอกชื่อ Wi-Fi" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="กรอกรหัสผ่าน">
            </div>
            <button type="submit">บันทึกและเชื่อมต่อ</button>
        </form>
    </div>
</body>
</html>
)rawhtml";

const char HTML_SUCCESS[] PROGMEM = R"rawhtml(
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <title>บันทึกสำเร็จ</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            text-align: center;
        }
        .container {
            background: rgba(30, 41, 59, 0.7);
            padding: 30px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 360px;
        }
        h2 { color: #4ade80; }
        p { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h2>บันทึกสำเร็จ!</h2>
        <p>อุปกรณ์กำลังบันทึกค่า Wi-Fi และเริ่มทำงานในโหมดปกติ...</p>
    </div>
</body>
</html>
)rawhtml";

void handleRoot() {
    server.send_P(200, "text/html", HTML_INDEX);
}

void handleSave() {
    String ssid = server.arg("ssid");
    String password = server.arg("password");
    
    Serial.printf("[WIFI_CFG] Received SSID: %s, PASS: %s\n", ssid.c_str(), password.c_str());
    wifi_save_credentials(ssid, password);
    
    server.send_P(200, "text/html", HTML_SUCCESS);
    
    should_reboot = true;
    reboot_timer_ms = millis();
}

void handleNotFound() {
    // สำหรับ Captive Portal: ส่งหน้า Index กลับไปเมื่อโดนดัก DNS
    server.sendHeader("Location", "http://192.168.4.1/", true);
    server.send(302, "text/plain", "");
}

void wifi_config_start() {
    if (config_active) return;
    
    Serial.println("[WIFI_CFG] Entering Wi-Fi Config Mode...");
    config_active = true;
    config_start_ms = millis();
    should_reboot = false;

    // เปลี่ยนโหมด WiFi เป็น AP
    WiFi.disconnect(true);
    delay(100);
    WiFi.mode(WIFI_AP);
    
    // ตั้งชื่อ AP
    WiFi.softAP("iCough-Setup");
    
    // ตั้งค่า DNS Redirect (พอร์ต 53 ดักทุกโดเมนไปที่ IP 192.168.4.1 ของบอร์ด)
    dnsServer.start(53, "*", IPAddress(192, 168, 4, 1));
    
    // ตั้งค่า Server Route
    server.on("/", HTTP_GET, handleRoot);
    server.on("/save", HTTP_POST, handleSave);
    server.on("/hotspot-detect.html", HTTP_GET, handleRoot); // ดัก Captive Portal iOS
    server.onNotFound(handleNotFound);
    
    server.begin();
    Serial.println("[WIFI_CFG] Web Server and DNS started on iCough-Setup AP");
}

void wifi_config_loop() {
    if (!config_active) return;
    
    dnsServer.processNextRequest();
    server.handleClient();
    
    // จัดการไฟ LED กระพริบ 100ms
    unsigned long now = millis();
    if (now - last_blink_ms >= 100) {
        last_blink_ms = now;
        led_state = !led_state;
        digitalWrite(TEST_LED_PIN, led_state ? HIGH : LOW);
    }
    
    // เช็คกรณีได้รับค่า Wi-Fi และเตรียมปิดตัว/รีบูตกลับโหมดปกติ
    if (should_reboot && (now - reboot_timer_ms >= 2000)) {
        wifi_config_stop();
        // ทำการ restart บอร์ดเพื่อเริ่มการทำงานใหม่ในโหมดปกติพร้อมเชื่อมต่อ WiFi ตัวใหม่ทันที
        ESP.restart();
    }

    // เช็ค Timeout 2 นาที
    if (now - config_start_ms >= CONFIG_TIMEOUT_MS) {
        Serial.println("[WIFI_CFG] Setup Timeout. Returning to normal mode...");
        wifi_config_stop();
    }
}

void wifi_config_stop() {
    if (!config_active) return;
    
    server.stop();
    dnsServer.stop();
    WiFi.softAPdisconnect(true);
    digitalWrite(TEST_LED_PIN, LOW); // ดับไฟ LED
    
    config_active = false;
    Serial.println("[WIFI_CFG] Wi-Fi Config Mode stopped.");
}

bool wifi_config_is_active() {
    return config_active;
}

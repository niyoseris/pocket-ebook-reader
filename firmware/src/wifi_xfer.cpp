/*
 * wifi_xfer.cpp -- WebServer + upload handling, no external JSON library.
 */

#include "wifi_xfer.h"
#include "storage.h"
#include "power.h"
#include "book.h"
#include "config.h"

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <LittleFS.h>
#include <string.h>

#define AP_PASS        "readbooks"
#define STA_TIMEOUT_MS 15000
#define UPLOAD_TMP     "/books/.upload.tmp"
#define MAX_RAW_UPLOAD (64u * 1024u)   /* limit for the raw-body path (it is
                                        * buffered in RAM by the WebServer --
                                        * multipart streams and has no limit) */

static WebServer  s_server(80);
static DNSServer  s_dns;
static bool       s_server_up = false;

static WifiXferState s_state = WIFI_XFER_OFF;
static uint32_t      s_state_since = 0;
static char          s_ap_ssid[24] = {0};
static char          s_address[20] = {0};
static uint32_t      s_book_ops = 0;

/* upload bookkeeping */
static File     s_up_file;
static String   s_up_final;        /* where the finished book should live */
static uint32_t s_up_size = 0;
static uint32_t s_up_magic = 0;    /* first 4 bytes, assembled across chunks */
static uint8_t  s_up_magic_len = 0;
static bool     s_up_has_file = false;
static bool     s_up_ok = false;
static String   s_up_error;
static char     s_up_name[96] = {0};

/* --------------------------------------------------------------------------
 *  Embedded upload page (self-contained: no external CSS, fonts or scripts)
 * ------------------------------------------------------------------------ */
static const char kPageHtml[] PROGMEM = R"HTMLPAGE(<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pocket Reader</title>
<style>
:root{--ink:#111;--paper:#fff;--line:#111;--dim:#666}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
     color:var(--ink);background:var(--paper);padding:20px;max-width:720px;margin:0 auto}
h1{font-size:22px;margin:0 0 2px}
h2{font-size:15px;margin:26px 0 8px;letter-spacing:.06em;text-transform:uppercase}
.sub{color:var(--dim);margin:0 0 18px}
.card{border:2px solid var(--line);padding:14px;margin:12px 0}
#drop{border:2px dashed var(--line);padding:26px 14px;text-align:center;cursor:pointer}
#drop.over{background:#eee}
#bar{height:12px;border:2px solid var(--line);margin-top:12px;display:none}
#bar>i{display:block;height:100%;width:0;background:var(--ink)}
ul{list-style:none;margin:0;padding:0}
li{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #ddd}
li .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
li .s{color:var(--dim);font-size:13px}
input,button{font:inherit;padding:8px 10px;border:2px solid var(--line);background:var(--paper);color:var(--ink)}
button{cursor:pointer}
button:hover{background:var(--ink);color:var(--paper)}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.row input{flex:1;min-width:150px}
#msg{margin-top:10px;font-weight:600;min-height:1.4em}
#stat{color:var(--dim);font-size:13px;white-space:pre-wrap}
</style></head><body>
<h1>Pocket Reader</h1>
<p class="sub">Kitap y&uuml;kleme sayfas&#305;</p>

<div class="card">
  <h2>Kitap y&uuml;kle</h2>
  <div id="drop">
    <b>.epr</b> dosyas&#305;n&#305; buraya b&#305;rak&#305;n<br>
    <span class="sub">veya dokunup se&ccedil;in</span>
    <input type="file" id="file" accept=".epr" hidden>
  </div>
  <div id="bar"><i></i></div>
  <div id="msg"></div>
</div>

<div class="card">
  <h2>Kitaplar</h2>
  <ul id="books"><li class="s">y&uuml;kleniyor...</li></ul>
</div>

<div class="card">
  <h2>WiFi a&#287;&#305;</h2>
  <p class="sub">Kaydedilirse cihaz bir dahaki sefere bu a&#287;a ba&#287;lanmay&#305; dener.</p>
  <div class="row">
    <input id="ssid" placeholder="A&#287; ad&#305;">
    <input id="pass" placeholder="&#350;ifre" type="password">
    <button onclick="saveWifi()">Kaydet</button>
  </div>
</div>

<div class="card">
  <h2>Durum</h2>
  <div id="stat">...</div>
</div>

<script>
const $ = s => document.querySelector(s);
const msg = (t, bad) => { $("#msg").innerHTML = t; $("#msg").style.color = bad ? "#a00" : "#060"; };

async function loadList(){
  try{
    const r = await fetch("/list");
    const books = await r.json();
    const ul = $("#books");
    ul.innerHTML = "";
    if(!books.length){ ul.innerHTML = '<li class="s">Hen&uuml;z kitap yok</li>'; return; }
    for(const b of books){
      const li = document.createElement("li");
      const t = document.createElement("div");
      t.className = "t";
      t.textContent = b.title || b.name;
      const s = document.createElement("div");
      s.className = "s";
      s.textContent = (b.author && b.author !== "-" ? b.author + " - " : "") + fmt(b.size);
      const btn = document.createElement("button");
      btn.textContent = "Sil";
      btn.onclick = async () => {
        if(!confirm("\"" + (b.title || b.name) + "\" silinsin mi?")) return;
        const fd = new FormData();
        fd.append("name", b.name);
        const r2 = await fetch("/delete", {method:"POST", body:fd});
        const j = await r2.json();
        if(j.ok) loadList(); else alert(j.error || "silinemedi");
      };
      li.append(t, s, btn);
      ul.append(li);
    }
  }catch(e){ $("#books").innerHTML = '<li class="s">liste al&#305;namad&#305;</li>'; }
}

function fmt(n){
  if(n > 1048576) return (n/1048576).toFixed(1) + " MB";
  if(n > 1024) return Math.round(n/1024) + " KB";
  return n + " B";
}

function upload(file){
  if(!file) return;
  if(!/\.epr$/i.test(file.name)){ msg("Sadece .epr dosyalar&#305; y&uuml;klenebilir", true); return; }
  const fd = new FormData();
  fd.append("book", file, file.name);
  const bar = $("#bar"); bar.style.display = "block";
  const fill = bar.firstElementChild;
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/upload");
  xhr.upload.onprogress = e => { if(e.lengthComputable) fill.style.width = (e.loaded/e.total*100) + "%"; };
  xhr.onload = () => {
    bar.style.display = "none"; fill.style.width = "0";
    let j = {}; try{ j = JSON.parse(xhr.responseText); }catch(e){}
    if(xhr.status === 200 && j.ok){ msg("Y&uuml;klendi: " + j.name); loadList(); }
    else msg("Hata: " + (j.error || xhr.status), true);
  };
  xhr.onerror = () => { bar.style.display = "none"; msg("Ba&#287;lant&#305; hatas&#305;", true); };
  xhr.send(fd);
}

const drop = $("#drop"), input = $("#file");
drop.onclick = () => input.click();
input.onchange = () => upload(input.files[0]);
["dragenter","dragover"].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.add("over");
}));
["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.remove("over");
}));
drop.addEventListener("drop", e => upload(e.dataTransfer.files[0]));

async function saveWifi(){
  const fd = new FormData();
  fd.append("ssid", $("#ssid").value);
  fd.append("pass", $("#pass").value);
  const r = await fetch("/wifi", {method:"POST", body:fd});
  const j = await r.json();
  msg(j.ok ? "WiFi kaydedildi" : ("Hata: " + (j.error || "")), !j.ok);
}

async function status(){
  try{
    const r = await fetch("/status");
    const j = await r.json();
    $("#stat").innerHTML =
      "S&uuml;r&uuml;m: " + j.version + "\n" +
      "Pil: " + j.battery_mv + " mV (" + j.battery_pct + "%)\n" +
      "Bo&#351; RAM: " + Math.round(j.free_heap/1024) + " KB\n" +
      "Bo&#351; alan: " + fmt(j.free_flash) + "\n" +
      "&Ccedil;al&#305;&#351;ma: " + j.uptime + " s";
  }catch(e){ $("#stat").textContent = "-"; }
}

loadList(); status();
setInterval(status, 10000);
</script>
</body></html>)HTMLPAGE";

/* --------------------------------------------------------------------------
 *  Tiny hand-rolled JSON helpers (no ArduinoJson)
 * ------------------------------------------------------------------------ */

static void jsonEscape(const char* in, String& out) {
    if (!in) return;
    for (const char* p = in; *p; p++) {
        const char c = *p;
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if ((uint8_t)c < 0x20) {
                    char tmp[8];
                    snprintf(tmp, sizeof(tmp), "\\u%04x", (unsigned)(uint8_t)c);
                    out += tmp;
                } else {
                    out += c;      /* UTF-8 passes through untouched */
                }
        }
    }
}

/* Extract a string value for `key` from a tiny flat JSON object. Returns false
 * if the key is absent. */
static bool jsonGetString(const String& body, const char* key, String& out) {
    const String pat = String("\"") + key + "\"";
    int i = body.indexOf(pat);
    if (i < 0) return false;
    i = body.indexOf(':', i + pat.length());
    if (i < 0) return false;
    i++;
    while (i < (int)body.length() && (body[i] == ' ' || body[i] == '\t')) i++;
    if (i >= (int)body.length() || body[i] != '"') return false;
    i++;

    out = "";
    while (i < (int)body.length()) {
        const char c = body[i++];
        if (c == '\\' && i < (int)body.length()) {
            const char e = body[i++];
            switch (e) {
                case 'n': out += '\n'; break;
                case 't': out += '\t'; break;
                case 'r': out += '\r'; break;
                case '"': out += '"';  break;
                case '\\': out += '\\'; break;
                default: out += e;
            }
            continue;
        }
        if (c == '"') return true;
        out += c;
    }
    return false;
}

/* Look a value up in the JSON body first, then in the form/query arguments. */
static bool requestValue(const char* key, String& out) {
    const String body = s_server.arg("plain");
    if (body.length() && jsonGetString(body, key, out)) return true;
    if (s_server.hasArg(key)) { out = s_server.arg(key); return true; }
    return false;
}

static void sendJson(int code, const String& body) {
    s_server.sendHeader("Cache-Control", "no-store");
    s_server.send(code, "application/json; charset=utf-8", body);
}

/* Keep uploaded names harmless: basename only, printable, no traversal. */
static String sanitizeName(const String& raw) {
    String base = raw;
    const int slash = base.lastIndexOf('/');
    if (slash >= 0) base = base.substring(slash + 1);
    const int bslash = base.lastIndexOf('\\');
    if (bslash >= 0) base = base.substring(bslash + 1);

    String out;
    for (size_t i = 0; i < base.length() && out.length() < 60; i++) {
        const char c = base[i];
        if (isalnum((unsigned char)c) || c == '-' || c == '_' || c == '.' || c == ' ') out += c;
        else out += '_';
    }
    if (out.length() == 0) out = "kitap.epr";
    if (!out.endsWith(".epr")) out += ".epr";
    return out;
}

/* --------------------------------------------------------------------------
 *  Upload handling
 * ------------------------------------------------------------------------ */

static void uploadReset() {
    if (s_up_file) s_up_file.close();
    s_up_file = File();
    s_up_final = "";
    s_up_size = 0;
    s_up_magic = 0;
    s_up_magic_len = 0;
    s_up_has_file = false;
    s_up_ok = false;
    s_up_name[0] = 0;
    s_up_error = "";
}

static void handleUploadData() {
    HTTPUpload& up = s_server.upload();

    switch (up.status) {
        case UPLOAD_FILE_START: {
            uploadReset();
            /* A multipart part with no filename is a plain form field. */
            if (up.filename.length() == 0) return;

            String name = sanitizeName(up.filename);
            strncpy(s_up_name, name.c_str(), sizeof(s_up_name) - 1);
            s_up_final = String(BOOKS_DIR) + "/" + name;

            if (LittleFS.exists(UPLOAD_TMP)) LittleFS.remove(UPLOAD_TMP);
            s_up_file = LittleFS.open(UPLOAD_TMP, "w");
            if (!s_up_file) {
                s_up_error = "dosya acilamadi";
                Serial.println("[wifi] cannot open the upload temp file");
                return;
            }
            s_up_has_file = true;
            Serial.printf("[wifi] upload start: %s\n", s_up_name);
            break;
        }

        case UPLOAD_FILE_WRITE: {
            if (!s_up_has_file) return;
            for (size_t i = 0; i < up.currentSize && s_up_magic_len < 4; i++) {
                s_up_magic = (s_up_magic << 8) | up.buf[i];
                s_up_magic_len++;
            }
            if (s_up_file) s_up_file.write(up.buf, up.currentSize);
            s_up_size += up.currentSize;
            break;
        }

        case UPLOAD_FILE_END: {
            if (!s_up_has_file) return;
            if (s_up_file) s_up_file.close();

            const bool magic_ok = (s_up_magic == 0x45505231u);   /* "EPR1" */
            if (!magic_ok) {
                s_up_error = "not an EPR1 file";
                Serial.printf("[wifi] rejected %s: bad magic 0x%08X\n",
                              s_up_name, (unsigned)s_up_magic);
                LittleFS.remove(UPLOAD_TMP);
            } else if (LittleFS.exists(s_up_final.c_str())) {
                LittleFS.remove(s_up_final.c_str());
                s_up_ok = LittleFS.rename(UPLOAD_TMP, s_up_final.c_str());
                s_up_error = s_up_ok ? "" : "kaydedilemedi";
            } else {
                s_up_ok = LittleFS.rename(UPLOAD_TMP, s_up_final.c_str());
                s_up_error = s_up_ok ? "" : "kaydedilemedi";
            }

            if (s_up_ok) {
                s_book_ops++;
                Serial.printf("[wifi] stored %s (%u bytes)\n",
                              s_up_final.c_str(), (unsigned)s_up_size);
            }
            s_up_has_file = false;
            break;
        }

        case UPLOAD_FILE_ABORTED: {
            Serial.println("[wifi] upload aborted");
            uploadReset();
            LittleFS.remove(UPLOAD_TMP);
            break;
        }

        default:
            break;
        }
}

/* Raw body path: the client sent the file directly with an X-Filename header
 * (a JSON client or curl -T). Streams to flash in chunks; limited by the
 * WebServer's body buffer, so multipart is the preferred path. */
static bool handleRawUpload();

static void handleUploadDone() {
    /* A multipart POST whose part had no filename never produced a file: give
     * the raw-body path (X-Filename) a chance before failing. */
    if (!s_up_name[0]) {
        if (handleRawUpload()) return;
        sendJson(400, "{\"ok\":false,\"error\":\"dosya yok\"}");
        return;
    }

    String j = "{\"ok\":";
    if (s_up_ok) {
        j += "true,\"name\":\"";
        jsonEscape(s_up_name, j);
        j += "\",\"size\":";
        j += String(s_up_size);
        j += "}";
        sendJson(200, j);
    } else {
        j += "false,\"error\":\"";
        jsonEscape(s_up_error.length() ? s_up_error.c_str() : "yukleme basarisiz", j);
        j += "\"}";
        sendJson(400, j);
    }
    s_up_ok = false;
}

static bool handleRawUpload() {
    const String body = s_server.arg("plain");
    const String header_name = s_server.header("X-Filename");
    if (!header_name.length()) return false;

    if (!body.length()) {
        sendJson(400, "{\"ok\":false,\"error\":\"bos govde\"}");
        return true;
    }
    if (body.length() > MAX_RAW_UPLOAD) {
        sendJson(413, "{\"ok\":false,\"error\":\"cok buyuk, multipart kullanin\"}");
        return true;
    }
    if (body.length() < 4 || memcmp(body.c_str(), EPR_MAGIC, 4) != 0) {
        sendJson(400, "{\"ok\":false,\"error\":\"not an EPR1 file\"}");
        return true;
    }

    const String name = sanitizeName(header_name);
    const String dest = String(BOOKS_DIR) + "/" + name;
    File f = LittleFS.open(dest, "w");
    if (!f) {
        sendJson(500, "{\"ok\":false,\"error\":\"yazilamadi\"}");
        return true;
    }
    const size_t written = f.write((const uint8_t*)body.c_str(), body.length());
    f.close();

    if (written != body.length()) {
        LittleFS.remove(dest.c_str());
        sendJson(500, "{\"ok\":false,\"error\":\"eksik yazildi\"}");
        return true;
    }

    s_book_ops++;
    Serial.printf("[wifi] stored (raw) %s (%u bytes)\n", dest.c_str(), (unsigned)written);
    sendJson(200, "{\"ok\":true,\"name\":\"" + name + "\",\"size\":" + String((unsigned)written) + "}");
    return true;
}

/* --------------------------------------------------------------------------
 *  Handlers
 * ------------------------------------------------------------------------ */

static void handleRoot() {
    s_server.sendHeader("Cache-Control", "no-store");
    s_server.send_P(200, "text/html; charset=utf-8", kPageHtml);
}

static void handleList() {
    std::vector<BookEntry> books = storageListBooks();
    String j = "[";
    for (size_t i = 0; i < books.size(); i++) {
        if (i) j += ",";
        j += "{\"name\":\"";
        jsonEscape(books[i].name.c_str(), j);
        j += "\",\"title\":\"";
        jsonEscape(books[i].title.c_str(), j);
        j += "\",\"author\":\"";
        jsonEscape(books[i].author.c_str(), j);
        j += "\",\"size\":";
        j += String((unsigned)books[i].size);
        j += "}";
    }
    j += "]";
    sendJson(200, j);
}

static void handleDelete() {
    String name;
    if (!requestValue("name", name)) {
        sendJson(400, "{\"ok\":false,\"error\":\"name yok\"}");
        return;
    }
    const String path = String(BOOKS_DIR) + "/" + sanitizeName(name);
    if (storageDeleteBook(path.c_str())) {
        s_book_ops++;
        sendJson(200, "{\"ok\":true}");
    } else {
        sendJson(404, "{\"ok\":false,\"error\":\"silinemedi\"}");
    }
}

static void handleWifi() {
    String ssid, pass;
    if (!requestValue("ssid", ssid) || !ssid.length()) {
        sendJson(400, "{\"ok\":false,\"error\":\"ssid yok\"}");
        return;
    }
    requestValue("pass", pass);
    storageSetWifi(ssid.c_str(), pass.c_str());
    sendJson(200, "{\"ok\":true}");
}

static void handleStatus() {
    uint32_t total = 0, used = 0;
    storageSpace(&total, &used);

    String j = "{";
    j += "\"version\":\"" POCKET_READER_VERSION "\",";
    j += "\"free_heap\":" + String((unsigned)ESP.getFreeHeap()) + ",";
    j += "\"free_flash\":" + String((unsigned)(total > used ? total - used : 0)) + ",";
    j += "\"battery_mv\":" + String((unsigned)batteryMilliVolts()) + ",";
    j += "\"battery_pct\":" + String((unsigned)batteryPercent()) + ",";
    j += "\"uptime\":" + String((unsigned)powerUptimeSeconds()) + ",";
    j += "\"mode\":\"";
    j += (s_state == WIFI_XFER_AP) ? "ap" : "sta";
    j += "\",\"books\":" + String((unsigned)storageListBooks().size());
    j += "}";
    sendJson(200, j);
}

/* Captive-portal catch-all: Android/iOS/Windows probes all land here and get
 * bounced to the upload page. */
static void handleNotFound() {
    String host = s_server.hostHeader();
    if (!host.length()) host = (s_state == WIFI_XFER_AP) ? WiFi.softAPIP().toString()
                                                         : WiFi.localIP().toString();
    s_server.sendHeader("Location", String("http://") + host + "/", true);
    s_server.send(302, "text/plain", "");
}

/* --------------------------------------------------------------------------
 *  Mode management
 * ------------------------------------------------------------------------ */

static void buildApSsid() {
    uint8_t mac[6] = {0};
    WiFi.macAddress(mac);
    snprintf(s_ap_ssid, sizeof(s_ap_ssid), "PocketReader-%02X%02X",
             (unsigned)mac[4], (unsigned)mac[5]);
}

static void startServer() {
    if (s_server_up) return;

    s_server.on("/", HTTP_GET, handleRoot);
    s_server.on("/list", HTTP_GET, handleList);
    s_server.on("/status", HTTP_GET, handleStatus);
    s_server.on("/wifi", HTTP_POST, handleWifi);
    s_server.on("/delete", HTTP_POST, handleDelete);
    /* Raw-body uploads (X-Filename) are served from the same /upload handler. */
    s_server.on("/upload", HTTP_POST, handleUploadDone, handleUploadData);
    s_server.onNotFound(handleNotFound);

    s_server.begin();
    s_server_up = true;
    Serial.println("[wifi] HTTP server on port 80");
}

static void goApMode() {
    buildApSsid();
    WiFi.mode(WIFI_AP);
    WiFi.softAP(s_ap_ssid, AP_PASS);

    /* Captive portal: answer every DNS name with our own address. */
    s_dns.start(53, "*", WiFi.softAPIP());

    const String ip = WiFi.softAPIP().toString();
    strncpy(s_address, ip.c_str(), sizeof(s_address) - 1);

    s_state = WIFI_XFER_AP;
    s_state_since = millis();
    startServer();

    Serial.printf("[wifi] AP \"%s\" up at %s\n", s_ap_ssid, s_address);
}

void wifiXferBegin() {
    if (s_state != WIFI_XFER_OFF) return;

    Settings st;
    storageLoadSettings(&st);

    uploadReset();
    s_book_ops = 0;

    if (st.wifi_ssid.length()) {
        Serial.printf("[wifi] trying saved network \"%s\"\n", st.wifi_ssid.c_str());
        WiFi.mode(WIFI_STA);
        WiFi.setSleep(false);           /* keep the server responsive */
        WiFi.begin(st.wifi_ssid.c_str(), st.wifi_pass.c_str());
        s_state = WIFI_XFER_CONNECTING;
        s_state_since = millis();
        strncpy(s_address, st.wifi_ssid.c_str(), sizeof(s_address) - 1);
    } else {
        goApMode();
    }
}

void wifiXferLoop() {
    if (s_state == WIFI_XFER_OFF) return;

    if (s_state == WIFI_XFER_CONNECTING) {
        if (WiFi.status() == WL_CONNECTED) {
            const String ip = WiFi.localIP().toString();
            strncpy(s_address, ip.c_str(), sizeof(s_address) - 1);
            s_state = WIFI_XFER_STA;
            s_state_since = millis();
            startServer();
            Serial.printf("[wifi] joined, http://%s/\n", s_address);
        } else if (millis() - s_state_since > STA_TIMEOUT_MS) {
            Serial.println("[wifi] STA timeout, falling back to AP");
            WiFi.disconnect(true);
            goApMode();
        }
    }

    if (!s_server_up) return;

    if (s_state == WIFI_XFER_AP) s_dns.processNextRequest();
    s_server.handleClient();
}

void wifiXferStop() {
    if (s_state == WIFI_XFER_OFF && !s_server_up) return;

    Serial.println("[wifi] shutting the radio down");
    s_server.stop();
    s_server_up = false;
    s_dns.stop();

    WiFi.softAPdisconnect(true);
    WiFi.disconnect(true);
    /* WIFI_OFF is what actually gets standby down to ~5 uA: an idle but
     * associated station keeps the modem and the beacon timer alive. */
    WiFi.mode(WIFI_OFF);
    delay(50);

    s_state = WIFI_XFER_OFF;
    s_address[0] = 0;
    uploadReset();
}

bool wifiXferActive() {
    return s_state != WIFI_XFER_OFF;
}

WifiXferState wifiXferState() { return s_state; }

const char* wifiXferStateText() {
    switch (s_state) {
        case WIFI_XFER_CONNECTING: return "baglaniyor";
        case WIFI_XFER_AP:         return "erisim noktasi";
        case WIFI_XFER_STA:        return "ag bagli";
        case WIFI_XFER_ERROR:      return "hata";
        default:                   return "kapali";
    }
}

const char* wifiXferSsid() {
    return (s_state == WIFI_XFER_AP) ? s_ap_ssid : s_address;
}

const char* wifiXferPass() {
    return (s_state == WIFI_XFER_AP) ? AP_PASS : "";
}

const char* wifiXferAddress() { return s_address; }

uint32_t wifiXferBookCount() { return s_book_ops; }

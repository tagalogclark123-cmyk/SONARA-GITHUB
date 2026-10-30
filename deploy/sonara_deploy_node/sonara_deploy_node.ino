/*
 * SONARA DEPLOYMENT NODE (farm data collection, Nov 2026)
 *
 * Records 5-s clips back to back and sends every clip to the bridge, as fast as the link allows.
 * Up to 5 nodes can share one bridge: before sending, a node asks the bridge for a turn
 * (REQUEST -> GRANT or WAIT), so only one node sends at a time and the USB link to the Pi
 * is never overloaded. With one node: about one clip every 9-10 s (about 6 clips per minute).
 *
 * Cycle:  RECORD 5 s  ->  ask for a turn  ->  SEND 667 packets (with retries)  ->  END packet with stats
 *
 * >>> BEFORE FLASHING EACH NODE: set NODE_ID (1, 2, 3, 4, 5 - every node different!) <<<
 * BRIDGE_MAC must be your bridge ESP32's MAC (unchanged from before).
 *
 * Blue LED (GPIO2):  ON = sending a clip | slow blink = waiting for a turn |
 *                    OFF = recording | 3 fast blinks at start-up | fast blink forever = bridge not found for 60 s
 * Wiring = the normal node (INMP441: WS 25, SCK 27, SD 32). Board: "ESP32 Dev Module".
 */
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_idf_version.h>
#include <driver/i2s.h>

// ===================== SET THESE =====================
#define NODE_ID           1                    // 1..5, DIFFERENT for every node
uint8_t BRIDGE_MAC[6] = {0xD4, 0xE9, 0xF4, 0xB2, 0xBF, 0x28};
#define HAS_BATT_DIVIDER  0                    // 1 only if the 100k/100k divider to GPIO34 is built
#define MIN_CYCLE_MS      0                    // 0 = as fast as possible; e.g. 30000 = one clip per 30 s
// =====================================================

#define WIFI_CHANNEL      1
#define SEND_RETRIES      4
#define INTER_PACKET_DELAY_MS 2
#define MAX_CONSEC_FAIL   20
#define TURN_GIVEUP_MS    60000                // no turn for 60 s -> drop this clip, record a new one
#define LED_PIN           2
#define BATT_PIN          34

#define I2S_WS   25
#define I2S_SCK  27
#define I2S_SD   32
#define I2S_PORT I2S_NUM_0
#define SAMPLE_RATE  16000
#define CLIP_SAMPLES 80000
#define CLIP_BYTES   160000
#define PIECES       10
#define PIECE_BYTES  16000
#define DATA_MAX     240

#define MSG_AUDIO 0x53
#define MSG_REQ   0x60
#define MSG_GRANT 0x61
#define MSG_WAIT  0x62
#define MSG_END   0x63

typedef struct __attribute__((packed)) {
  uint8_t magic, type, node_id; uint16_t clip_id, chunk_idx, total_chunks; uint8_t data_len; uint8_t data[DATA_MAX];
} AudioPacket;                                   // 250 bytes, same layout as sonara_node.ino
typedef struct __attribute__((packed)) {
  uint8_t magic, node_id; uint16_t clip_id;
} CtrlPacket;                                    // REQ / GRANT / WAIT, 4 bytes
typedef struct __attribute__((packed)) {
  uint8_t magic, node_id; uint16_t clip_id;
  uint32_t uptime_s, min_heap; uint8_t reset_reason, i2s_ok;
  uint16_t rec_peak, rec_rms, pkts, failed, retries, send_ms, wait_ms, batt_mv;
  uint32_t rec_age_ms;                           // ms from start of recording to this END packet
  uint16_t dropped_clips, sent_clips;            // since boot
} EndPacket;                                     // 38 bytes

uint8_t *piece[PIECES];
static int32_t raw[256];
volatile bool cbDone = false, cbOk = false;
volatile uint8_t ctrlReply = 0; volatile uint16_t ctrlClip = 0;
uint16_t clipId = 0, droppedClips = 0, sentClips = 0;
bool i2sOk = false;

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
void onSent(const wifi_tx_info_t *info, esp_now_send_status_t s) {
#else
void onSent(const uint8_t *mac, esp_now_send_status_t s) {
#endif
  cbOk = (s == ESP_NOW_SEND_SUCCESS); cbDone = true;
}

#if ESP_IDF_VERSION_MAJOR >= 5
void onRecv(const esp_now_recv_info_t *info, const uint8_t *d, int len) {
#else
void onRecv(const uint8_t *mac, const uint8_t *d, int len) {
#endif
  if (len >= 4 && (d[0] == MSG_GRANT || d[0] == MSG_WAIT) && d[1] == NODE_ID) {
    ctrlClip = d[2] | (d[3] << 8);
    ctrlReply = d[0];
  }
}

bool sendOnce(const uint8_t *d, size_t n) {
  cbDone = false; cbOk = false;
  if (esp_now_send(BRIDGE_MAC, d, n) != ESP_OK) { delay(5); return false; }
  unsigned long t0 = millis();
  while (!cbDone && millis() - t0 < 60) delay(1);
  return cbDone && cbOk;
}

void copyClip(uint32_t off, uint32_t len, uint8_t *dst) {      // clip bytes live in 10 pieces
  while (len) {
    uint32_t p = off / PIECE_BYTES, o = off % PIECE_BYTES, n = min(len, (uint32_t)(PIECE_BYTES - o));
    memcpy(dst, piece[p] + o, n); dst += n; off += n; len -= n;
  }
}

// Ask the bridge for a turn. Returns true when granted.
bool waitForTurn(unsigned long &waitMs) {
  CtrlPacket rq = {MSG_REQ, NODE_ID, clipId};
  unsigned long t0 = millis();
  while (millis() - t0 < TURN_GIVEUP_MS) {
    digitalWrite(LED_PIN, ((millis() / 500) % 2) ? HIGH : LOW);
    ctrlReply = 0;
    sendOnce((uint8_t *)&rq, sizeof(rq));
    unsigned long t1 = millis();
    while (ctrlReply == 0 && millis() - t1 < 150) delay(1);
    if (ctrlReply == MSG_GRANT && ctrlClip == clipId) { waitMs = millis() - t0; return true; }
    if (ctrlReply == MSG_WAIT) delay(300 + esp_random() % 600);     // another node is sending
    else delay(400 + esp_random() % 300);                           // no answer: bridge busy or away
  }
  waitMs = millis() - t0;
  return false;
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  for (int i = 0; i < 3; i++) { digitalWrite(LED_PIN, HIGH); delay(120); digitalWrite(LED_PIN, LOW); delay(120); }
  for (int i = 0; i < PIECES; i++) {
    piece[i] = (uint8_t *)malloc(PIECE_BYTES);
    if (!piece[i]) { Serial.printf("FAIL: memory piece %d\n", i); while (true) delay(1000); }
  }
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8; cfg.dma_buf_len = 256; cfg.use_apll = false;
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE; pins.bck_io_num = I2S_SCK; pins.ws_io_num = I2S_WS;
  pins.data_out_num = I2S_PIN_NO_CHANGE; pins.data_in_num = I2S_SD;
  i2sOk = (i2s_driver_install(I2S_PORT, &cfg, 0, NULL) == ESP_OK) && (i2s_set_pin(I2S_PORT, &pins) == ESP_OK);

  WiFi.mode(WIFI_STA); WiFi.disconnect();
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) { Serial.println("FAIL: ESP-NOW init"); while (true) delay(1000); }
  esp_now_register_send_cb(onSent);
  esp_now_register_recv_cb(onRecv);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BRIDGE_MAC, 6); peer.channel = WIFI_CHANNEL; peer.encrypt = false;
  esp_now_add_peer(&peer);
  Serial.printf("SONARA deployment node %d started, free heap %u, mic %s\n",
                NODE_ID, (unsigned)ESP.getFreeHeap(), i2sOk ? "OK" : "FAILED");
}

void loop() {
  unsigned long recStart = millis();

  // 1. RECORD 5 s (LED off)
  digitalWrite(LED_PIN, LOW);
  uint32_t peak = 0; double sumSq = 0; size_t br = 0;
  if (i2sOk) {
    for (int k = 0; k < 4; k++) i2s_read(I2S_PORT, raw, sizeof(raw), &br, portMAX_DELAY);   // flush old samples
    recStart = millis();
    uint32_t n = 0;
    while (n < CLIP_SAMPLES) {
      i2s_read(I2S_PORT, raw, sizeof(raw), &br, portMAX_DELAY);
      int words = br / 4;
      for (int i = 0; i < words && n < CLIP_SAMPLES; i++, n++) {
        int16_t s = (int16_t)(raw[i] >> 16);
        uint32_t off = n * 2;
        piece[off / PIECE_BYTES][off % PIECE_BYTES] = s & 0xFF;
        piece[(off + 1) / PIECE_BYTES][(off + 1) % PIECE_BYTES] = (s >> 8) & 0xFF;
        uint32_t a = s < 0 ? -(int32_t)s : s; if (a > peak) peak = a; sumSq += (double)s * s;
      }
    }
  } else {
    delay(5000);                                   // mic failed: still report so the Pi sees it
  }

  // 2. ASK FOR A TURN
  unsigned long waitMs = 0;
  if (!waitForTurn(waitMs)) {
    droppedClips++;
    Serial.printf("clip %u dropped: no turn from the bridge for %lu ms\n", clipId, waitMs);
    for (int i = 0; i < 40; i++) { digitalWrite(LED_PIN, i % 2); delay(50); }    // fast blink = bridge not found
    clipId++;
    return;
  }

  // 3. SEND the clip (LED on)
  digitalWrite(LED_PIN, HIGH);
  AudioPacket ap; ap.magic = MSG_AUDIO; ap.type = 1; ap.node_id = NODE_ID; ap.clip_id = clipId;
  uint16_t total = (CLIP_BYTES + DATA_MAX - 1) / DATA_MAX;
  ap.total_chunks = total;
  uint16_t sentOk = 0, failed = 0, retries = 0; int consec = 0;
  unsigned long t0 = millis();
  for (uint16_t i = 0; i < total; i++) {
    uint32_t off = (uint32_t)i * DATA_MAX, len = min((uint32_t)DATA_MAX, (uint32_t)(CLIP_BYTES - off));
    ap.chunk_idx = i; ap.data_len = len; copyClip(off, len, ap.data);
    bool ok = false;
    for (int a = 0; a <= SEND_RETRIES && !ok; a++) { if (a) retries++; ok = sendOnce((uint8_t *)&ap, sizeof(ap)); }
    if (ok) { sentOk++; consec = 0; } else { failed++; consec++; }
    if (consec >= MAX_CONSEC_FAIL) { failed += total - 1 - i; break; }   // bridge gone: give up this clip
    delay(INTER_PACKET_DELAY_MS);
  }
  unsigned long sendMs = millis() - t0;
  sentClips++;

  // 4. END packet with this clip's numbers (also tells the bridge the turn is over)
  EndPacket e = {};
  e.magic = MSG_END; e.node_id = NODE_ID; e.clip_id = clipId;
  e.uptime_s = millis() / 1000; e.min_heap = ESP.getMinFreeHeap(); e.reset_reason = (uint8_t)esp_reset_reason();
  e.i2s_ok = i2sOk; e.rec_peak = peak > 65535 ? 65535 : peak; e.rec_rms = (uint16_t)sqrt(sumSq / CLIP_SAMPLES);
  e.pkts = total; e.failed = failed; e.retries = retries;
  e.send_ms = sendMs > 65535 ? 65535 : sendMs; e.wait_ms = waitMs > 65535 ? 65535 : waitMs;
#if HAS_BATT_DIVIDER
  e.batt_mv = (uint16_t)(analogReadMilliVolts(BATT_PIN) * 2);
#else
  e.batt_mv = 0;
#endif
  e.rec_age_ms = millis() - recStart; e.dropped_clips = droppedClips; e.sent_clips = sentClips;
  for (int a = 0; a <= SEND_RETRIES; a++) if (sendOnce((uint8_t *)&e, sizeof(e))) break;
  digitalWrite(LED_PIN, LOW);

  Serial.printf("clip %u: sent %u/%u (failed %u, retries %u) in %lu ms, waited %lu ms, peak %u\n",
                clipId, sentOk, total, failed, retries, sendMs, waitMs, (unsigned)peak);
  clipId++;
  while ((long)(recStart + MIN_CYCLE_MS - millis()) > 0) delay(10);
}

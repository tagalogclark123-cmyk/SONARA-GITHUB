/*
 * SONARA DEPLOYMENT BRIDGE (ESP32 plugged into the Raspberry Pi by USB)
 *
 * - Gives nodes their turn: a node sends REQUEST, the bridge answers GRANT (send now) or WAIT
 *   (another node is sending). One node sends at a time, so the USB link is never overloaded.
 * - Forwards audio packets (0x53) to the Pi, exactly like sonara_bridge.ino.
 * - Forwards each node's END packet (0x63) with the bridge's own numbers added:
 *   audio packets received for that clip, their signal strength, and how many packets the
 *   bridge had to drop (queue full) since start-up.
 * - Every 5 s sends a heartbeat (0x64) so the Pi knows the bridge is alive.
 * Serial: 921600 baud, frames 0xAA 0x55 <len> <payload> <sum8>.
 * No settings to change. Board: "ESP32 Dev Module".
 */
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_idf_version.h>

#define WIFI_CHANNEL   1
#define QLEN           300
#define MAX_NODES      8
#define TURN_START_MS  2000     // granted node must start sending within this time
#define TURN_IDLE_MS   1500     // turn ends if no packet from the node for this long

#define MSG_AUDIO 0x53
#define MSG_REQ   0x60
#define MSG_GRANT 0x61
#define MSG_WAIT  0x62
#define MSG_END   0x63
#define MSG_BEAT  0x64

typedef struct { uint8_t len; int8_t rssi; uint8_t mac[6]; uint8_t data[250]; } Item;
QueueHandle_t q;
volatile uint32_t qDrops = 0;
uint8_t BCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

#if ESP_IDF_VERSION_MAJOR >= 5
void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  int8_t rssi = info->rx_ctrl ? info->rx_ctrl->rssi : 0;
  const uint8_t *mac = info->src_addr;
#else
void onRecv(const uint8_t *mac, const uint8_t *data, int len) {
  int8_t rssi = 0;
#endif
  if (len <= 0 || len > 250) return;
  Item it; it.len = len; it.rssi = rssi; memcpy(it.mac, mac, 6); memcpy(it.data, data, len);
  if (xQueueSend(q, &it, 0) != pdTRUE) qDrops++;
}

void sendFrame(const uint8_t *p, uint8_t n) {
  uint8_t sum = 0; for (int i = 0; i < n; i++) sum += p[i];
  uint8_t h[3] = {0xAA, 0x55, n};
  Serial.write(h, 3); Serial.write(p, n); Serial.write(&sum, 1);
}

void reply(uint8_t type, uint8_t node, uint16_t clip) {
  uint8_t m[4] = {type, node, (uint8_t)(clip & 0xFF), (uint8_t)(clip >> 8)};
  esp_now_send(BCAST, m, 4);                      // broadcast: every node hears it, only `node` reacts
}

// turn state
int owner = -1; uint16_t ownerClip = 0; unsigned long ownerLast = 0; bool ownerStarted = false;
// per-node counters for the clip being sent
uint16_t aClip[MAX_NODES + 1]; uint16_t aRx[MAX_NODES + 1]; long aSum[MAX_NODES + 1]; int8_t aMin[MAX_NODES + 1];
uint32_t framesOut = 0, grants = 0, waits = 0; uint8_t seenMask = 0;
unsigned long lastBeat = 0;

void setup() {
  Serial.setTxBufferSize(16384);
  Serial.begin(921600);
  q = xQueueCreate(QLEN, sizeof(Item));
  WiFi.mode(WIFI_STA); WiFi.disconnect();
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_now_init();
  esp_now_register_recv_cb(onRecv);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BCAST, 6); peer.channel = WIFI_CHANNEL; peer.encrypt = false;
  esp_now_add_peer(&peer);
  for (int i = 0; i <= MAX_NODES; i++) { aClip[i] = 0xFFFF; aRx[i] = 0; aSum[i] = 0; aMin[i] = 0; }
}

void loop() {
  Item it;
  while (xQueueReceive(q, &it, 5 / portTICK_PERIOD_MS) == pdTRUE) {
    uint8_t m = it.data[0];
    if (m == MSG_AUDIO && it.len >= 10) {
      uint8_t node = it.data[2]; uint16_t clip = it.data[3] | (it.data[4] << 8);
      if (node <= MAX_NODES) {
        if (clip != aClip[node]) { aClip[node] = clip; aRx[node] = 0; aSum[node] = 0; aMin[node] = 0; }
        aRx[node]++; aSum[node] += it.rssi; if (aRx[node] == 1 || it.rssi < aMin[node]) aMin[node] = it.rssi;
      }
      if (node == owner) { ownerLast = millis(); ownerStarted = true; }
      sendFrame(it.data, it.len); framesOut++;
    } else if (m == MSG_REQ && it.len >= 4) {
      uint8_t node = it.data[1]; uint16_t clip = it.data[2] | (it.data[3] << 8);
      if (node >= 1 && node <= MAX_NODES) seenMask |= (1 << (node - 1));
      if (owner < 0 || owner == node) {
        owner = node; ownerClip = clip; ownerLast = millis(); ownerStarted = false;
        reply(MSG_GRANT, node, clip); grants++;
      } else {
        reply(MSG_WAIT, node, clip); waits++;
      }
    } else if (m == MSG_END && it.len == 38) {
      uint8_t node = it.data[1]; uint16_t clip = it.data[2] | (it.data[3] << 8);
      uint8_t out[48]; memcpy(out, it.data, 38);
      bool ok = node <= MAX_NODES && aClip[node] == clip;
      uint16_t rx = ok ? aRx[node] : 0;
      int8_t avg = (ok && rx) ? aSum[node] / rx : 0, mn = ok ? aMin[node] : 0;
      uint32_t d = qDrops;
      out[38] = rx & 0xFF; out[39] = rx >> 8; out[40] = (uint8_t)avg; out[41] = (uint8_t)mn; out[42] = (uint8_t)it.rssi;
      memcpy(out + 43, &d, 4); out[47] = (owner == node) ? 1 : 0;
      sendFrame(out, 48); framesOut++;
      if (owner == node) owner = -1;              // turn over
    }
  }
  // turn timeout: node granted but never started, or stopped sending
  if (owner >= 0) {
    unsigned long lim = ownerStarted ? TURN_IDLE_MS : TURN_START_MS;
    if (millis() - ownerLast > lim) owner = -1;
  }
  if (millis() - lastBeat >= 5000) {
    lastBeat = millis();
    uint8_t b[20]; uint32_t up = millis() / 1000, d = qDrops;
    b[0] = MSG_BEAT; memcpy(b + 1, &up, 4); memcpy(b + 5, &d, 4); memcpy(b + 9, &framesOut, 4);
    memcpy(b + 13, &grants, 4); b[17] = (uint8_t)(owner < 0 ? 0 : owner); b[18] = seenMask; b[19] = 0;
    sendFrame(b, 20);
  }
}

// Semaforo Inteligente - receptor Serial para ESP32
//
// O Python envia linhas como:
//   LIGHT RED
//   LIGHT YELLOW
//   LIGHT GREEN
//   HEADLIGHT ON
//   HEADLIGHT OFF
//
// Ajuste os pinos conforme a ligação da sua maquete.

const int LED_RED = 25;
const int LED_YELLOW = 26;
const int LED_GREEN = 27;
const int HEADLIGHT = 33;

void setLight(const String &color) {
  digitalWrite(LED_RED, color == "RED" ? HIGH : LOW);
  digitalWrite(LED_YELLOW, color == "YELLOW" ? HIGH : LOW);
  digitalWrite(LED_GREEN, color == "GREEN" ? HIGH : LOW);
}

void setup() {
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(HEADLIGHT, OUTPUT);
  setLight("RED");
  digitalWrite(HEADLIGHT, LOW);
  Serial.begin(115200);
}

void loop() {
  if (!Serial.available()) return;

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "LIGHT RED") setLight("RED");
  else if (command == "LIGHT YELLOW") setLight("YELLOW");
  else if (command == "LIGHT GREEN") setLight("GREEN");
  else if (command == "HEADLIGHT ON") digitalWrite(HEADLIGHT, HIGH);
  else if (command == "HEADLIGHT OFF") digitalWrite(HEADLIGHT, LOW);

  Serial.println("OK " + command);
}

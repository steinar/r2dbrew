#include <OneWire.h>

const int buffer_size = 128;
char buffer[128];
unsigned int read_pos = 0;
unsigned int write_pos = 0;

unsigned int temp = 99;

int greenLed = 10;
int redLed   = 11;
int leds[2] = {greenLed, redLed};

int heater_pins[2] = {12,13};
int heater_led_pins[2] = {10,11};

#pragma pack(push, 1)
struct Header {
  unsigned short msg_size;
  char           msg_type;
};

struct HeaterCommand {
  char heater_idx;
  bool heater_status;
};

struct LedCommand {
  char led_idx;
  bool led_status;
};

struct TempUpdate {
  char temp;
};
#pragma pack(pop)

OneWire ds(7);
byte tempAddr[8];

void setup() {
  Serial.begin(9600);
  pinMode(greenLed, OUTPUT);
  pinMode(redLed,   OUTPUT);
  read_pos = 0;
  write_pos = 0;
  tempAddr[0] = 0;
}

int readTemperature()
{
  byte data[12];
  
  if (tempAddr[0] == 0)
  {
    if ( !ds.search(tempAddr)) { 
      // Found no address
      tempAddr[0] = 0;
      ds.reset_search();
      return 0;
    }
    
    if (OneWire::crc8(tempAddr, 7) != tempAddr[7]) {
      tempAddr[0] = 0;
      return 0;
    }
  }
  
  ds.reset();
  ds.select(tempAddr);
  ds.write(0x44, 1);        // start conversion, with parasite power on at the end
  
  delay(1000);      // maybe 750ms is enough, maybe not
  // we might do a ds.depower() here, but the reset will take care of it.
  
  ds.reset();
  ds.select(tempAddr);    
  ds.write(0xBE);         // Read Scratchpad
  
  for ( int i = 0; i < 9; i++) {           // we need 9 bytes
    data[i] = ds.read();
  }
  
  int16_t raw = (data[1] << 8) | data[0];
  byte cfg = (data[4] & 0x60);
  // at lower res, the low bits are undefined, so let's zero them
  if (cfg == 0x00) raw = raw & ~7;  // 9 bit resolution, 93.75 ms
  else if (cfg == 0x20) raw = raw & ~3; // 10 bit res, 187.5 ms
  else if (cfg == 0x40) raw = raw & ~1; // 11 bit res, 375 ms
  //// default is 12 bit resolution, 750 ms conversion time
  return (float)raw / 16.0;
}

void loop() {  
  temp = readTemperature();
  
  while (Serial.available() > 0 && write_pos < buffer_size - 1) {
    buffer[write_pos++] = Serial.read();
  }

  while (write_pos - read_pos >= sizeof(struct Header)) {
    struct Header * hdr = (struct Header *)(buffer + read_pos);
    
    if (sizeof(struct Header) + hdr->msg_size > write_pos - read_pos)
      break;
      
    switch (hdr->msg_type)
    {
    case 'H': // HEATER
      {
      struct HeaterCommand * cmd = (struct HeaterCommand *)(buffer + read_pos + sizeof(struct Header));
      //digitalWrite(heater_pins[cmd->heater_idx], cmd->heater_status ? HIGH : LOW);
      digitalWrite(heater_led_pins[cmd->heater_idx], cmd->heater_status ? HIGH : LOW);
      }
      break;
    case 'B': // BEEP
      // TODO beep
      break;
    case 'L': // LED COMMAND
      {
      struct LedCommand * cmd = (struct LedCommand *)(buffer + read_pos + sizeof(struct Header));
      digitalWrite(leds[cmd->led_idx], cmd->led_status ? HIGH : LOW);
      }
      break;
    case 'D': // DISPLAY LCD
      // TODO display message
      break;
    }
    
    read_pos += sizeof(struct Header) + hdr->msg_size;
  }
  
  if (read_pos > 0)
  {
    unsigned int remaining = write_pos - read_pos;
    for (int i = 0; i < remaining; i++)
      buffer[i] = buffer[read_pos+i]; 
    read_pos = 0;
    write_pos = remaining;
  }

  char out_buffer[128];
  struct Header * hdr = (struct Header *)out_buffer;
  hdr->msg_type = 't';
  hdr->msg_size = 1;
  struct TempUpdate * upd = (struct TempUpdate *)(out_buffer + sizeof(struct Header));
  upd->temp = temp;
  
  for (int i = 0; i < sizeof(struct Header) + sizeof(struct TempUpdate); i++)
    Serial.write(out_buffer[i]);
    
  //delay(500);
}

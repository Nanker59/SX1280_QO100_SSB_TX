#include <string.h>

#include "bsp/board_api.h"
#include "tusb.h"
#include "usb_descriptors.h"

#if CFG_AUDIO_DEBUG
#include "common_types.h"
#endif

/* PID bitmap */
#define PID_MAP(itf, n)  ((CFG_TUD_##itf) ? (1 << (n)) : 0)
#define USB_PID (0x4000 | PID_MAP(CDC, 0) | PID_MAP(MSC, 1) | PID_MAP(HID, 2) | \
                          PID_MAP(MIDI, 3) | PID_MAP(AUDIO, 4) | PID_MAP(VENDOR, 5))

//--------------------------------------------------------------------+
// Device Descriptor
//--------------------------------------------------------------------+
static tusb_desc_device_t const desc_device =
{
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = 0x0200,

    // IAD dla kompozytu
    .bDeviceClass       = TUSB_CLASS_MISC,
    .bDeviceSubClass    = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol    = MISC_PROTOCOL_IAD,

    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor           = 0xCafe,
    .idProduct          = USB_PID,
    .bcdDevice          = 0x0100,

    .iManufacturer      = 0x01,
    .iProduct           = 0x02,
    .iSerialNumber      = 0x03,

    .bNumConfigurations = 0x01
};

uint8_t const * tud_descriptor_device_cb(void)
{
  return (uint8_t const *) &desc_device;
}

#if CFG_AUDIO_DEBUG
//--------------------------------------------------------------------+
// HID Report Descriptor (opcjonalnie)
//--------------------------------------------------------------------+
uint8_t const desc_hid_report[] = {
  HID_USAGE_PAGE_N ( HID_USAGE_PAGE_VENDOR, 2   ),
  HID_USAGE        ( 0x01                       ),
  HID_COLLECTION   ( HID_COLLECTION_APPLICATION ),
    HID_USAGE        ( 0x02 ),
    HID_LOGICAL_MIN  ( 0x00 ),
    HID_LOGICAL_MAX_N( 0xff, 2 ),
    HID_REPORT_SIZE  ( 8 ),
    HID_REPORT_COUNT ( sizeof(audio_debug_info_t) ),
    HID_INPUT        ( HID_DATA | HID_VARIABLE | HID_ABSOLUTE ),
  HID_COLLECTION_END
};

uint8_t const * tud_hid_descriptor_report_cb(uint8_t itf)
{
  (void) itf;
  return desc_hid_report;
}
#endif

//--------------------------------------------------------------------+
// Endpoint numbers
//--------------------------------------------------------------------+
//
// Audio: ISO OUT + FB IN (zwyczajowo ten sam numer EP, IN ma bit 0x80)
// CDC:   1x NOTIF IN, 1x BULK OUT, 1x BULK IN
// HID:   1x IN (opcjonalnie)

#if CFG_TUSB_MCU == OPT_MCU_LPC175X_6X || CFG_TUSB_MCU == OPT_MCU_LPC177X_8X || CFG_TUSB_MCU == OPT_MCU_LPC40XX
  #define EPNUM_AUDIO         0x03
  #define EPNUM_AUDIO_FB      0x03

  #define EPNUM_CDC_NOTIF     0x81
  #define EPNUM_CDC_OUT       0x02
  #define EPNUM_CDC_IN        0x82

  #define EPNUM_DEBUG         0x04

#elif TU_CHECK_MCU(OPT_MCU_NRF5X)
  #define EPNUM_AUDIO         0x08
  #define EPNUM_AUDIO_FB      0x08

  #define EPNUM_CDC_NOTIF     0x81
  #define EPNUM_CDC_OUT       0x02
  #define EPNUM_CDC_IN        0x82

  #define EPNUM_DEBUG         0x04

#elif defined(TUD_ENDPOINT_ONE_DIRECTION_ONLY)
  // konserwatywnie: unikamy współdzielenia numerów
  #define EPNUM_AUDIO         0x02
  #define EPNUM_AUDIO_FB      0x01

  #define EPNUM_CDC_NOTIF     0x83
  #define EPNUM_CDC_OUT       0x04
  #define EPNUM_CDC_IN        0x84

  #define EPNUM_DEBUG         0x05

#else
  // Typowe dla RP2040: weź audio na 0x01, CDC na 0x02/0x82/0x83, debug na 0x84
  #define EPNUM_AUDIO         0x01
  #define EPNUM_AUDIO_FB      0x01

  #define EPNUM_CDC_OUT       0x02
  #define EPNUM_CDC_IN        0x82
  #define EPNUM_CDC_NOTIF     0x83

  #define EPNUM_DEBUG         0x84
#endif

//--------------------------------------------------------------------+
// Configuration Descriptor (UAC1 + CDC (+ optional HID))
//--------------------------------------------------------------------+

#if CFG_AUDIO_DEBUG
  #define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_AUDIO10_SPEAKER_STEREO_FB_DESC_LEN(2) + TUD_CDC_DESC_LEN + TUD_HID_DESC_LEN)
#else
  #define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_AUDIO10_SPEAKER_STEREO_FB_DESC_LEN(2) + TUD_CDC_DESC_LEN)
#endif

uint8_t const desc_configuration[] =
{
  // Config: 1, interface count, string index, total length, attribute, power(mA)
  // Attribute: 0x80 = bus powered
  TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x80, 100),

  // ---- UAC1 Speaker stereo + feedback, sample rates 44.1k + 48k ----
  // (stridx=2 wg Twojej tablicy stringów: "TinyUSB Speaker (UAC1)" / lub "UAC1 Speaker")
  TUD_AUDIO10_SPEAKER_STEREO_FB_DESCRIPTOR(
    ITF_NUM_AUDIO_CONTROL,
    2,
      CFG_TUD_AUDIO_FUNC_1_N_BYTES_PER_SAMPLE_RX,
      CFG_TUD_AUDIO_FUNC_1_RESOLUTION_RX,
      EPNUM_AUDIO,
      CFG_TUD_AUDIO_FUNC_1_EP_OUT_SZ_FS,
      (uint8_t)(EPNUM_AUDIO_FB | 0x80),
      44100, 48000
  ),

  // ---- CDC ACM (Serial) ----
  // stridx = 4 (patrz stringi poniżej)
  TUD_CDC_DESCRIPTOR(
    ITF_NUM_CDC_COMM,
    4,
    EPNUM_CDC_NOTIF, 8,
    EPNUM_CDC_OUT,
    EPNUM_CDC_IN, 64
  ),

#if CFG_AUDIO_DEBUG
  // ---- Optional HID debug ----
  TUD_HID_DESCRIPTOR(ITF_NUM_DEBUG, 0, HID_ITF_PROTOCOL_NONE,
                     sizeof(desc_hid_report), (uint8_t)EPNUM_DEBUG,
                     CFG_TUD_HID_EP_BUFSIZE, 7)
#endif
};

TU_VERIFY_STATIC(sizeof(desc_configuration) == CONFIG_TOTAL_LEN, "Incorrect size");

uint8_t const * tud_descriptor_configuration_cb(uint8_t index)
{
  (void) index;
  return desc_configuration;
}

//--------------------------------------------------------------------+
// String Descriptors
//--------------------------------------------------------------------+

enum {
  STRID_LANGID = 0,
  STRID_MANUFACTURER,
  STRID_PRODUCT,
  STRID_SERIAL,
  STRID_CDC,       // 4
  STRID_UAC1,      // 5
};

static char const *string_desc_arr[] =
{
  (const char[]) { 0x09, 0x04 },        // 0: English (0x0409)
  "TinyUSB",                            // 1: Manufacturer
  "TinyUSB Speaker (UAC1) + CDC",       // 2: Product
  NULL,                                 // 3: Serial (generated)
  "CDC Console",                        // 4: CDC interface string
  "UAC1 Speaker",                       // 5: UAC1 (optional use)
};

static uint16_t _desc_str[32 + 1];

uint16_t const * tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
  (void) langid;
  size_t chr_count;

  switch ( index )
  {
    case STRID_LANGID:
      memcpy(&_desc_str[1], string_desc_arr[0], 2);
      chr_count = 1;
      break;

    case STRID_SERIAL:
      chr_count = board_usb_get_serial(_desc_str + 1, 32);
      break;

    default:
    {
      if ( !(index < sizeof(string_desc_arr) / sizeof(string_desc_arr[0])) ) return NULL;

      const char *str = string_desc_arr[index];
      if (!str) return NULL;

      chr_count = strlen(str);

      size_t const max_count = sizeof(_desc_str) / sizeof(_desc_str[0]) - 1;
      if ( chr_count > max_count ) chr_count = max_count;

      for ( size_t i = 0; i < chr_count; i++ ) _desc_str[1 + i] = str[i];
    }
    break;
  }

  _desc_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * chr_count + 2));
  return _desc_str;
}

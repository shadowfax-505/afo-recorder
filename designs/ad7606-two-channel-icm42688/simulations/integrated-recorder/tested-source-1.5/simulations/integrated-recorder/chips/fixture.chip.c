// Fixture selection only; these pins are not part of the recorder hardware.
#include "wokwi-api.h"
void chip_init(void) {
    unsigned selection=attr_read(attr_init("case",0));
    const char *pins[]={"CASE0","CASE1","CASE2","CASE3"};
    for(unsigned i=0;i<4;i++)pin_write(pin_init(pins[i],OUTPUT),!!(selection&(1u<<i)));
}

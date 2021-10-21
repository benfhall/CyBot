#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <timer.h>
#include <inc/tm4c123gh6pm.h>

// Initialize the ADC
void adc_init(void){
      SYSCTL_RCGCADC_R |= 0x0001;   // 1) activate ADC0
      SYSCTL_RCGCGPIO_R |= 0x10;    // 2) activate clock for Port E
      while((SYSCTL_PRGPIO_R&0x10) != 0x10){};  // 3 for stabilization
      GPIO_PORTE_DIR_R &= ~0x10;    // 4) make PE4 input
      GPIO_PORTE_AFSEL_R |= 0x10;   // 5) enable alternate function on PE4
      GPIO_PORTE_DEN_R &= ~0x10;    // 6) disable digital I/O on PE4
      GPIO_PORTE_AMSEL_R |= 0x10;   // 7) enable analog functionality on PE4
      ADC0_PC_R &= ~0xF;
      ADC0_PC_R |= 0x1;             // 8) configure for 125K samples/sec
      ADC0_SSPRI_R = 0x0123;        // 9) Sequencer 3 is highest priority
      ADC0_ACTSS_R &= ~0x0008;      // 10) disable sample sequencer 3
      ADC0_EMUX_R &= ~0xF000;       // 11) seq3 is software trigger
      ADC0_SSMUX3_R &= ~0x000F;
      ADC0_SSMUX3_R += 10;           // 12) set channel
      ADC0_SSCTL3_R = 0x0006;       // 13) no TS0 D0, yes IE0 END0
      ADC0_SAC_R = 0x6;
      ADC0_IM_R &= ~0x0008;         // 14) disable SS3 interrupts
      ADC0_ACTSS_R |= 0x0008;       // 15) enable sample sequencer 3
}

int adc_read(void) {
    ADC0_PSSI_R = 0x0008; //init ss3
    while ( (ADC0_RIS_R & 0x08 ) == 0 ) {} // wait for conversion to complete
    int result = ADC0_SSFIFO3_R & 0xFFF; // read data
    ADC0_ISC_R = 0x0008; // clear interrupt
    return result; //return data
}

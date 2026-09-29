# Gate15 v2 analysis (fixed mapping)

## Factorial (25 seeds; new CSA/C48/C88 + kept DRRA/Normal)

- CSA: val 0.6148±0.0704 test 0.8771
- DRRA: val 0.6190±0.0827 test 0.8440
- C48: val 0.6810±0.0570 test 0.9496
- C88: val 0.6128±0.0660 test 0.8505
- Normal: val 0.8389±0.0814 test 1.0804
- KV_main: -0.0320 [-0.0618,-0.0023] wilcoxon 0.00963503122329712 t 0.0361 sign 20/25
- routing_main: +0.0300 [+0.0010,+0.0589] wilcoxon 0.05875152349472046 t 0.0430 sign 16/25
- interaction: -0.0724 [-0.1289,-0.0158] wilcoxon 0.013554692268371582 t 0.0143 sign 17/25
- H1: +0.0620 [+0.0157,+0.1082] wilcoxon 0.007370948791503906 t 0.0107 sign 18/25
- DRRA_minus_CSA_val: +0.0042 [-0.0437,+0.0521] wilcoxon 0.615043044090271 t 0.8583 sign 9/25
- DRRA_minus_CSA_test: -0.0331 [-0.0699,+0.0036] wilcoxon 0.03180783987045288 t 0.0751 sign 17/25

best-of-four val: `{'DRRA': 7, 'C88': 8, 'C48': 2, 'CSA': 8}` test: `{'DRRA': 12, 'C88': 8, 'CSA': 5}`
beats-CSA val: `{'DRRA': 16, 'C48': 6, 'C88': 12}` test: `{'DRRA': 17, 'C48': 4, 'C88': 17}`
beats-Normal: `{'CSA': 24, 'DRRA': 24, 'C48': 22, 'C88': 25}`

## Suite Flat v2 (5 seeds)

- etth1: flat 0.5909 drra 0.5967 normal 0.8416 | flat-vs-normal p=0.0625
- etth2: flat 1.7817 drra 1.8080 normal 1.9187 | flat-vs-normal p=0.8125
- ettm1: flat 0.4121 drra 0.3832 normal 0.4285 | flat-vs-normal p=0.4375
- ettm2: flat 0.9326 drra 0.8053 normal 1.5618 | flat-vs-normal p=0.0625
- electricity: flat 0.3775 drra 0.3808 normal 0.4047 | flat-vs-normal p=0.125
- traffic: flat 0.5907 drra 0.5874 normal 0.5994 | flat-vs-normal p=0.0625
- weather: flat 0.4448 drra 0.4424 normal 0.4460 | flat-vs-normal p=0.8125
- exchange: flat 3.1364 drra 3.2350 normal 2.9800 | flat-vs-normal p=0.3125
- solar: flat 0.1693 drra 0.1722 normal 0.1899 | flat-vs-normal p=0.0625
- syn_sinusoids: flat 0.1276 drra 0.1264 normal 0.1227 | flat-vs-normal p=0.0625
- syn_changepoints: flat 5.9733 drra 6.0013 normal 5.9456 | flat-vs-normal p=0.625
- syn_delayedcopy: flat 0.2894 drra 0.2894 normal 0.2888 | flat-vs-normal p=0.0625
Flat best-mean count: 4/12

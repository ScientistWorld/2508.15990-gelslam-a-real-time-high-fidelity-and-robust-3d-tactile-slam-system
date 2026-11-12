| method | status | rank gain | E1 rot MAE | E1 trans MAE | E1 rot p95 | E1 false-loop excess | E2 rot MAE | E2 trans MAE | E2 rot p95 | E2 false-loop excess |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| session_chain_dense | scored | +0.557 | 1.4803 | 0.1422 | 4.3192 | 0.0000 | 1.4010 | 0.2961 | 4.1050 | 0.0000 |
| hybrid_local_loops | scored | +0.053 | 1.4195 | 0.1325 | 4.0092 | 0.0000 | 1.7825 | 0.4906 | 28.3392 | 0.0000 |
| exhaustive_two_stage | scored | +0.024 | 1.4233 | 0.1418 | 4.2883 | 0.0000 | 2.1158 | 0.3972 | 32.0507 | 0.0000 |
| loop_ccs_070 | scored | +0.006 | 1.4389 | 0.1420 | 4.2946 | 0.0000 | 2.1273 | 0.3993 | 32.0507 | 0.0000 |
| gelslam_online | scored | +0.000 | 1.4390 | 0.1423 | 4.2946 | 0.0000 | 2.1500 | 0.4011 | 32.0507 | 0.0000 |
| reference_seed1 | scored | +0.000 | 1.4390 | 0.1423 | 4.2946 | 0.0000 | 2.1500 | 0.4011 | 32.0507 | 0.0000 |
| session_chain | scored | -0.067 | 1.4708 | 0.1422 | 4.1066 | 0.0000 | 1.8354 | 0.5060 | 28.6231 | 0.0000 |
| nf_kf | scored | -3.882 | 2.0712 | 0.2620 | 6.4450 | 0.0000 | 19.4876 | 3.0670 | 90.0000 | 0.0000 |
| only_nf_exhaustive | scored | -4.484 | 2.1113 | 0.2346 | 4.0759 | 0.0169 | 19.4085 | 3.0273 | 90.0000 | 0.0000 |
| normalflow | scored | -7.161 | 3.1665 | 0.7007 | 14.6149 | 0.0000 | 11.4511 | 2.8060 | 62.4027 | 0.0000 |
| only_sift | failed (false-loop constraint failed: 619/807 unique loop co | -293.807 | 90.0000 | 30.0000 | 90.0000 | 0.9800 | 90.0000 | 30.0000 | 90.0000 | 0.9800 |

Paired per-episode differences vs reference (negative = better): mean ± SE, better/worse episodes
- session_chain_dense: long_-rot +0.0413±0.0601 (17/7); long_-tra -0.0001±0.0045 (16/8); reloc-rot -0.7490±1.0624 (10/6); reloc-tra -0.1050±0.1634 (9/7)
- hybrid_local_loops: long_-rot -0.0195±0.0414 (9/3); long_-tra -0.0098±0.0034 (9/3); reloc-rot -0.3675±0.7107 (6/4); reloc-tra +0.0895±0.0615 (6/4)
- exhaustive_two_stage: long_-rot -0.0157±0.0091 (9/1); long_-tra -0.0004±0.0007 (9/1); reloc-rot -0.0342±0.0243 (8/6); reloc-tra -0.0039±0.0016 (9/5)
- loop_ccs_070: long_-rot -0.0001±0.0001 (1/0); long_-tra -0.0003±0.0003 (1/0); reloc-rot -0.0228±0.0192 (2/0); reloc-tra -0.0018±0.0016 (2/0)
- reference_seed1: long_-rot +0.0000±0.0000 (0/0); long_-tra +0.0000±0.0000 (0/0); reloc-rot +0.0000±0.0000 (0/0); reloc-tra +0.0000±0.0000 (0/0)
- session_chain: long_-rot +0.0318±0.0318 (0/1); long_-tra -0.0001±0.0001 (1/0); reloc-rot -0.3146±0.6914 (1/1); reloc-tra +0.1049±0.0720 (0/2)
- nf_kf: long_-rot +0.6322±0.2235 (2/21); long_-tra +0.1197±0.0474 (0/23); reloc-rot +17.3376±1.9573 (1/15); reloc-tra +2.6659±0.2751 (1/15)
- only_nf_exhaustive: long_-rot +0.6723±0.7338 (17/5); long_-tra +0.0923±0.1031 (16/4); reloc-rot +17.2584±1.9675 (1/15); reloc-tra +2.6262±0.2807 (1/15)
- normalflow: long_-rot +1.7275±0.9096 (1/23); long_-tra +0.5584±0.1238 (1/23); reloc-rot +9.3011±1.8503 (1/15); reloc-tra +2.4049±0.3281 (1/15)
- only_sift: long_-rot +1.4353±0.2627 (1/22); long_-tra +0.1102±0.0193 (1/22); reloc-rot +2.1423±0.3587 (1/15); reloc-tra +0.1345±0.0252 (0/16)
